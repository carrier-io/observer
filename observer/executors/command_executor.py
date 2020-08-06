import copy
import os
import tempfile
from time import time
from urllib.parse import urlparse
from uuid import uuid4

from deepdiff import DeepDiff
from requests import get

from observer.actions import browser_actions
from observer.actions.browser_actions import get_performance_timing, get_dom_size, take_full_screenshot, \
    get_performance_entities, get_performance_metrics, get_current_url, get_command, get_current_session_id
from observer.constants import LISTENER_ADDRESS
from observer.db import save_to_storage, get_from_storage
from observer.models.command_result import CommandExecutionResult
from observer.util import logger


def execute_command(current_command, next_command, test_data_processor, enable_video=True):
    logger.info(
        f"{current_command['comment']} [ {current_command['command']}({current_command['target']}) ] "
        f"{current_command['value']}".strip())

    generate_report = False
    screenshot_path = None
    results = None
    results_type = "page"

    current_target = current_command['target']
    current_value = test_data_processor.process(current_command['value'])
    current_cmd, current_is_actionable = get_command(current_command['command'])

    _, next_is_actionable = get_command(next_command['command'])

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

            comment = current_command['comment']
            if comment:
                results['info']['title'] = comment

            dom = get_dom_size()

            save_to_storage("command_results", {
                "dom_size": dom,
                "results": results,
                "load_event_end": load_event_end,
                "perf_entities": []
            })

            screenshot_path = take_full_screenshot(f"/tmp/{uuid4()}.png")
            generate_report = True

        elif not is_navigation:
            previous_res = get_from_storage("command_results")
            perf_entities = previous_res['perf_entities']
            dom = previous_res['dom_size']
            previous_results = previous_res['results']

            load_event_end = get_performance_timing()['loadEventEnd']
            latest_pef_entries = get_performance_entities()

            is_entities_changed = is_performance_entities_changed(perf_entities, latest_pef_entries)

            if is_entities_changed and is_dom_changed(dom):
                dom = get_dom_size()
                latest_results = get_performance_metrics()
                latest_results['info']['testStart'] = int(current_time)
                results = compute_results_for_spa(previous_results, latest_results, current_command)

                save_to_storage("command_results", {
                    "dom_size": dom,
                    "results": latest_results,
                    "load_event_end": load_event_end,
                    "perf_entities": latest_pef_entries
                })

                screenshot_path = take_full_screenshot(f"/tmp/{uuid4()}.png")
                generate_report = True
                results_type = "action"

    except Exception as e:
        logger.error(f'======> Exception {e}')
        return CommandExecutionResult(err=e)
    finally:
        if not next_is_actionable:
            return CommandExecutionResult()

        video_folder = None
        video_path = None
        if enable_video and next_is_actionable:
            video_folder, video_path = stop_recording()

    if not results:
        return CommandExecutionResult()

    page_identifier = get_page_identifier(results['info']['title'], current_command)

    return CommandExecutionResult(results_type=results_type,
                                  page_identifier=page_identifier,
                                  computed_results=results,
                                  video_folder=video_folder,
                                  video_path=video_path,
                                  screenshot_path=screenshot_path,
                                  generate_report=generate_report)


def get_page_identifier(title, current_command):
    current_url = get_current_url()
    parsed_url = urlparse(current_url)
    comment = current_command['comment']
    if comment:
        title = comment

    return f"{title}:{parsed_url.path}@{current_command['command']}({current_command['target']})"


def start_recording():
    get(f'http://{LISTENER_ADDRESS}/record/start?sessionId={get_current_session_id()}')


def stop_recording():
    video_results = get(f'http://{LISTENER_ADDRESS}/record/stop?sessionId={get_current_session_id()}').content
    video_folder = tempfile.mkdtemp()
    video_path = os.path.join(video_folder, "video.mp4")
    with open(video_path, 'w+b') as f:
        f.write(video_results)

    return video_folder, video_path


def is_navigation_happened():
    results = get_from_storage("command_results")
    if results is None:
        load_event_end = 0
    else:
        load_event_end = results['load_event_end']

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

    comment = current_command['comment']
    if comment:
        result['info']['title'] = comment

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
