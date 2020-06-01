import copy
import tempfile
from datetime import datetime
from os import path
from shutil import rmtree
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from deepdiff import DeepDiff
from junit_xml import TestSuite, TestCase
from requests import get
from selene.support.shared import browser, SharedConfig

from observer.actions import browser_actions
from observer.actions.browser_actions import get_performance_timing, get_performance_metrics, command_type, \
    get_performance_entities, take_full_screenshot, get_dom_size, close_driver, get_current_url
from observer.command_result import CommandExecutionResult
from observer.constants import LISTENER_ADDRESS, GALLOPER_PROJECT_ID, REPORTS_BUCKET, GALLOPER_URL, ENV, \
    get_headers, RESULTS_BUCKET, RESULTS_REPORT_NAME
from observer.exporter import export, GalloperExporter, JsonExporter
from observer.processors.results_processor import resultsProcessor
from observer.processors.test_data_processor import get_test_data_processor
from observer.reporter import complete_report
from observer.thresholds import AggregatedThreshold
from observer.util import _pairwise, logger, terminate_runner, get_thresholds, filter_thresholds_for

load_event_end = 0
perf_entities = []
dom = None
results = None


def execute_scenario(scenario, args):
    base_url = scenario['url']
    config = SharedConfig()
    config.base_url = base_url
    browser._config = config
    for test in scenario['tests']:
        _execute_test(base_url, config.browser_name, test, args)

    close_driver()
    if not args.video:
        terminate_runner()


def _execute_test(base_url, browser_name, test, args):
    global results
    report_id = None
    global_thresholds = []

    test_name = test['name']
    logger.info(f"Executing test: {test_name}")

    test_data_processor = get_test_data_processor(test_name, args.data)

    if args.galloper:
        global_thresholds = get_thresholds(test_name)
        report_id = notify_on_test_start(GALLOPER_PROJECT_ID, test_name, browser_name, ENV, base_url)

    locators = []
    exception = None
    visited_pages = 0
    total_thresholds = {
        "total": 0,
        "failed": 0,
        "details": []
    }
    execution_results = {}

    for current_command, next_command in _pairwise(test['commands']):
        logger.info(
            f"{current_command['comment']} [ {current_command['command']}({current_command['target']}) ] "
            f"{current_command['value']}".strip())

        locators.append(current_command)

        execution_result = _execute_command(current_command, next_command, test_data_processor,
                                            is_video_enabled(args))

        if execution_result.ex:
            exception = execution_result.ex
            break

        if not execution_result.report:
            continue

        if args.export:
            export(execution_result.computed_results, args)

        visited_pages += 1

        scoped_thresholds = filter_thresholds_for(execution_result.report.title, global_thresholds)

        report_uuid, threshold_results = complete_report(execution_result, scoped_thresholds, args)

        if args.galloper:
            notify_on_command_end(
                report_id,
                execution_result.computed_results,
                threshold_results, locators, report_uuid, execution_result.report.title)

        if execution_result.raw_results:
            results = execution_result.raw_results

        perf_results = JsonExporter(execution_result.computed_results).export()['fields']
        page_identificator = execution_result.page_identificator
        if page_identificator in execution_results.keys():
            execution_results[page_identificator].append(perf_results)
        else:
            execution_results[page_identificator] = [perf_results]

    if global_thresholds:
        threshold_results = assert_test_thresholds(test_name, global_thresholds, execution_results)
        total_thresholds["total"] += threshold_results["total"]
        total_thresholds["failed"] += threshold_results["failed"]
        total_thresholds['details'] = threshold_results["details"]

    junit_report_name = generate_junit_report(test_name, total_thresholds)

    if args.galloper:
        notify_on_test_end(report_id, visited_pages, total_thresholds, exception,
                           junit_report_name)


def assert_test_thresholds(test_name, all_scope_thresholds, execution_results):
    threshold_results = {"total": len(all_scope_thresholds), "failed": 0, "details": []}

    logger.info(f"=====> Assert aggregated thresholds for {test_name}")
    checking_result = []
    for gate in all_scope_thresholds:
        threshold = AggregatedThreshold(gate, execution_results)
        if not threshold.is_passed():
            threshold_results['failed'] += 1
        checking_result.append(threshold.get_result())

    threshold_results["details"] = checking_result
    logger.info("=====>")

    return threshold_results


def generate_junit_report(test_name, total_thresholds):
    test_cases = []
    file_name = f"junit_report_{RESULTS_REPORT_NAME}.xml"
    logger.info(f"Generate report {file_name}")

    for item in total_thresholds["details"]:
        message = item['message']
        test_case = TestCase(item['name'], classname=f"{item['scope']}",
                             status="PASSED",
                             stdout=f"{item['scope']} {item['name'].lower()} {item['aggregation']} {item['actual']} "
                                    f"{item['rule']} {item['expected']}")
        if message:
            test_case.status = "FAILED"
            test_case.add_failure_info(message)
        test_cases.append(test_case)

    ts = TestSuite(test_name, test_cases)

    with open(f"/tmp/reports/{file_name}", 'w') as f:
        TestSuite.to_file(f, [ts], prettyprint=True)

    return file_name


def notify_on_test_start(project_id: int, test_name, browser_name, environment, base_url):
    data = {
        "test_name": test_name,
        "base_url": base_url,
        "browser_name": browser_name,
        "env": environment,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    res = requests.post(f"{GALLOPER_URL}/api/v1/observer/{project_id}", json=data,
                        headers=get_headers())
    return res.json()['id']


def notify_on_test_end(report_id: int, visited_pages, total_thresholds, exception, junit_report_name):
    logger.info(f"About to notify on test end for report {report_id}")

    data = {
        "report_id": report_id,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "visited_pages": visited_pages,
        "thresholds_total": total_thresholds["total"],
        "thresholds_failed": total_thresholds["failed"]
    }

    if exception:
        data["exception"] = str(exception)

    res = requests.put(f"{GALLOPER_URL}/api/v1/observer/{GALLOPER_PROJECT_ID}", json=data,
                       headers=get_headers())

    upload_artifacts(RESULTS_BUCKET, f"/tmp/reports/{junit_report_name}", junit_report_name)
    return res.json()


def send_report_locators(project_id: int, report_id: int, exception):
    requests.put(f"{GALLOPER_URL}/api/v1/observer/{project_id}/{report_id}",
                 json={"exception": exception, "status": ""},
                 headers=get_headers())


def notify_on_command_end(report_id: int, metrics, thresholds, locators, report_uuid,
                          name):
    logger.info(f"About to notify on command end for report {report_id}")
    result = GalloperExporter(metrics).export()

    file_name = f"{name}_{report_uuid}.html"
    report_path = f"/tmp/reports/{file_name}"

    data = {
        "name": name,
        "metrics": result,
        "bucket_name": REPORTS_BUCKET,
        "file_name": file_name,
        "resolution": metrics['info']['windowSize'],
        "browser_version": metrics['info']['browser'],
        "thresholds_total": thresholds["total"],
        "thresholds_failed": thresholds["failed"],
        "locators": locators
    }

    res = requests.post(f"{GALLOPER_URL}/api/v1/observer/{GALLOPER_PROJECT_ID}/{report_id}", json=data,
                        headers=get_headers())

    upload_artifacts(REPORTS_BUCKET, report_path, file_name)

    return res.json()["id"]


def upload_artifacts(bucket_name, artifact_path, file_name):
    file = {'file': open(artifact_path, 'rb')}

    res = requests.post(f"{GALLOPER_URL}/api/v1/artifacts/{GALLOPER_PROJECT_ID}/{bucket_name}/{file_name}", files=file,
                        headers=get_headers())
    return res.json()


def is_video_enabled(args):
    return "html" in args.report and args.video


def _execute_command(current_command, next_command, test_data_processor, enable_video=True):
    global load_event_end
    global perf_entities
    global dom
    global results

    report = None
    generate_report = False
    screenshot_path = None
    latest_results = None

    current_cmd = current_command['command']
    current_target = current_command['target']
    current_value = test_data_processor.process(current_command['value'])
    current_cmd, current_is_actionable = command_type[current_cmd]

    next_cmd = next_command['command']
    next_cmd, next_is_actionable = command_type[next_cmd]

    start_time = time()
    if enable_video and current_is_actionable:
        start_recording()
    current_time = time() - start_time
    try:

        current_cmd(current_target, current_value)

        is_navigation = is_navigation_happened()

        if is_navigation and next_is_actionable:
            browser_actions.wait_for_visibility(next_command['target'])

            load_event_end = get_performance_timing()['loadEventEnd']
            results = get_performance_metrics()
            results['info']['testStart'] = int(current_time)
            dom = get_dom_size()

            screenshot_path = take_full_screenshot(f"/tmp/{uuid4()}.png")
            generate_report = True
        elif not is_navigation:
            latest_pef_entries = get_performance_entities()

            is_entities_changed = is_performance_entities_changed(perf_entities, latest_pef_entries)

            if is_entities_changed and is_dom_changed(dom):
                dom = get_dom_size()
                perf_entities = latest_pef_entries
                latest_results = get_performance_metrics()
                latest_results['info']['testStart'] = int(current_time)
                results = compute_results_for_spa(results, latest_results, current_command)
                screenshot_path = take_full_screenshot(f"/tmp/{uuid4()}.png")
                generate_report = True

    except Exception as e:
        logger.error(e)
        return CommandExecutionResult(err=e)
    finally:
        if not next_is_actionable:
            return CommandExecutionResult()

        video_folder = None
        video_path = None
        if enable_video and next_is_actionable:
            video_folder, video_path = stop_recording()

    if generate_report and results and video_folder:
        report = resultsProcessor(video_path, results, video_folder, screenshot_path, True, True)

    if video_folder:
        rmtree(video_folder)

    page_identificator = None
    if report:
        # get url, action, locator here
        current_url = get_current_url()
        parsed_url = urlparse(current_url)
        title = report.title
        comment = current_command['comment']
        if comment:
            title = comment

        page_identificator = f"{title}:{parsed_url.path}@{current_command['command']}({current_target})"
    return CommandExecutionResult(page_identificator, report, latest_results, results, None)


def start_recording():
    get(f'http://{LISTENER_ADDRESS}/record/start')


def stop_recording():
    video_results = get(f'http://{LISTENER_ADDRESS}/record/stop').content
    video_folder = tempfile.mkdtemp()
    video_path = path.join(video_folder, "Video.mp4")
    with open(video_path, 'w+b') as f:
        f.write(video_results)

    return video_folder, video_path


def is_navigation_happened():
    latest_load_event_end = get_performance_timing()['loadEventEnd']
    if latest_load_event_end != load_event_end:
        return True

    return False


def is_performance_entities_changed(old_entities, latest_entries):
    ddiff = DeepDiff(old_entities, latest_entries, ignore_order=True)
    if not ddiff:
        return False

    if ddiff['iterable_item_added'] or ddiff['iterable_item_removed']:
        return True

    return False


def is_dom_changed(old_dom):
    new_dom = get_dom_size()
    return old_dom != new_dom


# total_load_time = perf_timing['loadEventEnd'] - perf_timing['navigationStart']
# time_to_first_byte = perf_timing['responseStart'] - perf_timing['navigationStart']
# time_to_first_paint = timing['firstPaint']
# dom_content_loading = perf_timing['domContentLoadedEventStart'] - perf_timing['domLoading']
# dom_processing = perf_timing['domComplete'] - perf_timing['domLoading']
def compute_results_for_spa(old, new, current_command):
    result = copy.deepcopy(new)

    timing = {
        'connectEnd': 0,
        'connectStart': 0,
        'domComplete': 0,
        'domContentLoadedEventEnd': 0,
        'domContentLoadedEventStart': 0,
        'domInteractive': 0,
        'domLoading': 0,
        'domainLookupEnd': 0,
        'domainLookupStart': 0,
        'fetchStart': 0,
        'loadEventEnd': 0,
        'loadEventStart': 0,
        'navigationStart': 0,
        'redirectEnd': 0,
        'redirectStart': 0,
        'requestStart': 0,
        'responseEnd': 0,
        'responseStart': 0,
        'secureConnectionStart': 0,
        'unloadEventEnd': 0,
        'unloadEventStart': 0
    }

    diff = DeepDiff(old["performanceResources"], new["performanceResources"], ignore_order=True)

    removed = {}
    added = diff['iterable_item_added']
    if 'iterable_item_removed' in diff.keys():
        removed = diff['iterable_item_removed']

    items_added = []
    for key, item in added.items():
        if key not in removed.keys():
            items_added.append(item)

    sorted_items = sorted(items_added, key=lambda k: k['startTime'])

    fields = [
        'connectEnd',
        'connectStart',
        'domainLookupEnd',
        'domainLookupStart',
        'fetchStart',
        'requestStart',
        'responseEnd',
        'responseStart',
        'secureConnectionStart',
        'startTime'
    ]

    first_result = sorted_items[0]
    first_point = first_result['startTime']
    for item in sorted_items:
        for field in fields:
            curr_value = item[field]
            if curr_value == 0:
                continue
            item[field] = curr_value - first_point

    sorted_items = sorted(items_added, key=lambda k: k['responseEnd'])
    latest_response = round(sorted_items[-1]['responseEnd'])

    result["performanceResources"] = sorted_items
    timing['requestStart'] = first_result['requestStart']
    timing['loadEventEnd'] = round(latest_response)
    result['performancetiming'] = timing
    result['timing']['firstPaint'] = new['timing']['firstPaint'] - old['timing']['firstPaint']

    if old['info']['title'] == new['info']['title']:
        title = new['info']['title']
        comment = current_command['comment']
        if comment:
            title = comment

        result['info']['title'] = title

    return result
