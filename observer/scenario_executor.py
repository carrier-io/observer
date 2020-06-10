import copy
import tempfile
from os import path
from shutil import rmtree
from time import time
from urllib.parse import urlparse
from uuid import uuid4

from deepdiff import DeepDiff
from requests import get

from observer.actions import browser_actions
from observer.actions.browser_actions import get_performance_timing, get_performance_metrics, command_type, \
    get_performance_entities, take_full_screenshot, get_dom_size, get_current_url
from observer.command_result import CommandExecutionResult
from observer.constants import LISTENER_ADDRESS, GALLOPER_PROJECT_ID, ENV
from observer.exporter import export, JsonExporter
from observer.integrations.galloper import get_thresholds, notify_on_test_start, notify_on_command_end, \
    notify_on_test_end
from observer.processors.results_processor import resultsProcessor
from observer.processors.test_data_processor import get_test_data_processor
from observer.reporters.html_reporter import complete_report
from observer.reporters.junit_reporter import generate_junit_report
from observer.thresholds import AggregatedThreshold
from observer.util import _pairwise, logger, filter_thresholds_for

load_event_end = 0
perf_entities = []
dom = None
results = None


def execute_scenario(scenario, config, args):
    for test in scenario['tests']:
        logger.info(f"Executing test: {test['name']}")
        _execute_test(config.base_url, config.browser_name, test, args)


def _execute_test(base_url, browser_name, test, args):
    global results
    report_id = None
    global_thresholds = []
    locators = []
    exception = None
    visited_pages = 0
    total_thresholds = {
        "total": 0,
        "failed": 0,
        "details": []
    }
    execution_results = {}

    test_name = test['name']
    test_data_processor = get_test_data_processor(test_name, args.data)

    if args.galloper:
        global_thresholds = get_thresholds(test_name)
        report_id = notify_on_test_start(test_name, browser_name, base_url)

    for current_command, next_command in _pairwise(test['commands']):
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
                execution_result.results_type,
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


def is_video_enabled(args):
    return "html" in args.report and args.video


def _execute_command(current_command, next_command, test_data_processor, enable_video=True):
    logger.info(
        f"{current_command['comment']} [ {current_command['command']}({current_command['target']}) ] "
        f"{current_command['value']}".strip())

    global load_event_end
    global perf_entities
    global dom
    global results

    report = None
    generate_report = False
    screenshot_path = None
    latest_results = None
    results_type = "page"

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
            results = compute_results_for_simple_page()
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
                results_type = "action"

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
    return CommandExecutionResult(results_type, page_identificator, report, latest_results, results, None)


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
    timing['requestStart'] = round(first_result['requestStart'])
    timing['responseStart'] = round(first_result['responseStart'])
    timing['loadEventEnd'] = round(latest_response)

    content_loading_time = 0
    for item in sorted_items:
        if item['decodedBodySize'] > 0:
            content_loading_time += round(item["responseEnd"] - item["responseStart"])

    timing['domContentLoadedEventStart'] = 1
    timing['domContentLoadedEventEnd'] = timing['domContentLoadedEventStart']

    result['performancetiming'] = timing
    result['timing']['firstPaint'] = new['timing']['firstPaint'] - old['timing']['firstPaint']

    if old['info']['title'] == new['info']['title']:
        title = new['info']['title']
        comment = current_command['comment']
        if comment:
            title = comment

        result['info']['title'] = title

    return result


def compute_results_for_simple_page():
    metrics = get_performance_metrics()
    resources = copy.deepcopy(metrics['performanceResources'])

    sorted_items = sorted(resources, key=lambda k: k['startTime'])
    current_total = metrics['performancetiming']['loadEventEnd'] - metrics['performancetiming']['navigationStart']
    fixed_end = sorted_items[-1]['responseEnd']
    diff = fixed_end - current_total
    metrics['performancetiming']['loadEventEnd'] += round(diff)
    return metrics
