import copy
import tempfile
from datetime import datetime
from os import path
from shutil import rmtree
from time import time
from uuid import uuid4

import requests
from deepdiff import DeepDiff
from requests import get
from selene.support.shared import browser, SharedConfig

from observer.actions import browser_actions
from observer.actions.browser_actions import get_performance_timing, get_performance_metrics, command_type, \
    get_performance_entities, take_full_screenshot, get_dom_size
from observer.command_result import CommandExecutionResult
from observer.constants import LISTENER_ADDRESS, GALLOPER_PROJECT_ID, REPORTS_BUCKET, GALLOPER_URL, ENV, \
    TOKEN, get_headers
from observer.exporter import export, GalloperExporter
from observer.processors.results_processor import resultsProcessor
from observer.processors.test_data_processor import get_test_data_processor
from observer.reporter import complete_report
from observer.runner import close_driver, terminate_runner
from observer.util import _pairwise, logger

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

    test_name = test['name']
    logger.info(f"Executing test: {test_name}")

    test_data_processor = get_test_data_processor(test_name, args.data)

    if args.galloper:
        report_id = notify_on_test_start(GALLOPER_PROJECT_ID, test_name, browser_name, ENV, base_url)

    locators = []
    exception = None
    visited_pages = 0
    total_thresholds = {
        "total": 0,
        "failed": 0
    }

    for current_command, next_command in _pairwise(test['commands']):
        logger.info(current_command)

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

        report_uuid, thresholds = complete_report(execution_result.report, args)
        total_thresholds["total"] += thresholds["total"]
        total_thresholds["failed"] += thresholds["failed"]

        if args.galloper:
            notify_on_command_end(GALLOPER_PROJECT_ID,
                                  report_id,
                                  REPORTS_BUCKET,
                                  execution_result.computed_results,
                                  thresholds, locators, report_uuid, execution_result.report.title)

        if execution_result.raw_results:
            results = execution_result.raw_results

    if args.galloper:
        notify_on_test_end(GALLOPER_PROJECT_ID, report_id, visited_pages, total_thresholds, exception)


def notify_on_test_start(project_id: int, test_name, browser_name, environment, base_url):
    data = {
        "test_name": test_name,
        "base_url": base_url,
        "browser_name": browser_name,
        "env": environment,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    res = requests.post(f"{GALLOPER_URL}/observer/{project_id}", json=data,
                        headers=get_headers())
    return res.json()['id']


def notify_on_test_end(project_id: int, report_id: int, visited_pages, total_thresholds, exception):
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

    res = requests.put(f"{GALLOPER_URL}/observer/{project_id}", json=data,
                       headers=get_headers())
    return res.json()


def send_report_locators(project_id: int, report_id: int, exception):
    requests.put(f"{GALLOPER_URL}/observer/{project_id}/{report_id}", json={"exception": exception, "status": ""},
                 headers=get_headers())


def notify_on_command_end(project_id: int, report_id: int, bucket_name, metrics, thresholds, locators, report_uuid,
                          name):
    logger.info(f"About to notify on command end for report {report_id}")
    result = GalloperExporter(metrics).export()

    file_name = f"{name}_{report_uuid}.html"
    report_path = f"/tmp/reports/{file_name}"

    data = {
        "name": name,
        "metrics": result,
        "bucket_name": bucket_name,
        "file_name": file_name,
        "resolution": metrics['info']['windowSize'],
        "browser_version": metrics['info']['browser'],
        "thresholds_total": thresholds["total"],
        "thresholds_failed": thresholds["failed"],
        "locators": locators
    }

    res = requests.post(f"{GALLOPER_URL}/observer/{project_id}/{report_id}", json=data, headers=get_headers())

    file = {'file': open(report_path, 'rb')}

    requests.post(f"{GALLOPER_URL}/artifacts/{project_id}/{bucket_name}/{file_name}", files=file,
                  headers=get_headers())

    return res.json()["id"]


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

    return CommandExecutionResult(report, latest_results, results, None)


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


def compute_results_for_spa(old, new, current_command):
    result = copy.deepcopy(new)

    diff = DeepDiff(old["performanceResources"], new["performanceResources"], ignore_order=True)
    items_added = list(diff['iterable_item_added'].values())
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

    first_point = sorted_items[0]['startTime']
    for item in sorted_items:
        for field in fields:
            curr_value = item[field]
            if curr_value == 0:
                continue
            item[field] = curr_value - first_point

    sorted_items = sorted(items_added, key=lambda k: k['responseEnd'])

    total_diff = round(
        new['performancetiming']['loadEventEnd'] - new['performancetiming']['navigationStart'] - sorted_items[-1][
            'responseEnd'])

    result["performanceResources"] = items_added
    result['performancetiming']['responseStart'] = result['performancetiming']['navigationStart']
    result['performancetiming']['loadEventEnd'] = result['performancetiming']['loadEventEnd'] - total_diff
    result['performancetiming']['domComplete'] = result['performancetiming']['domComplete'] - total_diff

    result['timing']['firstPaint'] = new['timing']['firstPaint'] - old['timing']['firstPaint']

    if old['info']['title'] == new['info']['title']:
        title = new['info']['title']
        comment = current_command['comment']
        if comment:
            title = comment

        result['info']['title'] = title

    return result
