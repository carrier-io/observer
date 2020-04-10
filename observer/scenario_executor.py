import tempfile
from os import path
from shutil import rmtree
from time import time
from junit_xml import TestSuite, TestCase

from requests import get
from selene.support.shared import browser, SharedConfig
from selenium.common.exceptions import WebDriverException

from observer.actions import browser_actions
from observer.constants import check_ui_performance, listener_address
from observer.driver_manager import get_driver
from observer.processors.results_processor import resultsProcessor
from observer.runner import close_driver, terminate_runner

load_event_end = 0


def execute_scenario(scenario, args):
    url = scenario['url']
    config = SharedConfig()
    config.base_url = url
    browser._config = config
    for test in scenario['tests']:
        _execute_test(test, args)

    close_driver()
    if not args.video:
        terminate_runner()


def _pairwise(iterable):
    return zip(iterable, iterable[1:])


def _execute_test(test, args):
    print(f"'\nExecuting test: {test['name']}")
    for current_command, next_command in _pairwise(test['commands']):
        print(current_command)
        results = []

        report = _execute_command(current_command, next_command, is_video_enabled(args))

        if not report:
            continue

        if 'html' in args.report:
            results.append({'html_report': report.get_report(), 'title': report.title})
        if args.firstPaint > 0:
            message = ''
            if args.firstPaint < report.timing['firstPaint']:
                message = f"First paint exceeded threshold of {args.firstPaint}ms by " \
                          f"{report.timing['firstPaint'] - args.firstPaint} ms"
            results.append({"name": f"First Paint {report.title}",
                            "actual": report.timing['firstPaint'], "expected": args.firstPaint, "message": message})
        if args.speedIndex > 0:
            message = ''
            if args.speedIndex < report.timing['speedIndex']:
                message = f"Speed index exceeded threshold of {args.speedIndex}ms by " \
                          f"{report.timing['speedIndex'] - args.speedIndex} ms"
            results.append({"name": f"Speed Index {report.title}", "actual": report.timing['speedIndex'],
                            "expected": args.speedIndex, "message": message})
        if args.totalLoad > 0:
            totalLoad = report.performance_timing['loadEventEnd'] - report.performance_timing['navigationStart']
            message = ''
            if args.totalLoad < totalLoad:
                message = f"Total Load exceeded threshold of {args.totalLoad}ms by " \
                          f"{totalLoad - args.speedIndex} ms"
            results.append({"name": f"Total Load {report.title}", "actual": totalLoad,
                            "expected": args.totalLoad, "message": message})
        process_report(results, args.report)


def is_video_enabled(args):
    return "html" in args.report and args.video


def _execute_command(current_command, next_command, enable_video=True):
    global load_event_end
    results = None

    current_cmd = current_command['command']
    current_target = current_command['target']
    current_value = current_command['value']
    current_cmd, current_is_actionable = command_type[current_cmd]

    next_cmd = next_command['command']
    next_cmd, next_is_actionable = command_type[next_cmd]

    start_time = time()
    if enable_video and current_is_actionable:
        start_recording()
    current_time = time() - start_time
    try:
        current_cmd(current_target, current_value)

        if next_is_actionable:
            pass

        if is_navigation_happened() and next_is_actionable:
            browser_actions.wait_for_visibility(next_command['target'])

            load_event_end = get_performance_timing()['loadEventEnd']
            results = get_performance_metrics()
            results['info']['testStart'] = int(current_time)
    except WebDriverException as e:
        print(e)
        return None
    finally:
        if not next_is_actionable:
            return None

        video_folder = None
        video_path = None
        if enable_video and next_is_actionable:
            video_folder, video_path = stop_recording()

    report = None
    if results and video_folder:
        report = resultsProcessor(video_path, results, video_folder, True, True)

    if video_folder:
        rmtree(video_folder)

    return report


def start_recording():
    get(f'http://{listener_address}/record/start')


def stop_recording():
    video_results = get(f'http://{listener_address}/record/stop').content
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


def get_performance_timing():
    return get_driver().execute_script("return performance.timing")


def get_performance_metrics():
    return get_driver().execute_script(check_ui_performance)


def command(func, actionable=True):
    return func, actionable


command_type = {
    "open": command(browser_actions.open),
    "setWindowSize": command(browser_actions.setWindowSize, actionable=False),
    "click": command(browser_actions.click),
    "type": command(browser_actions.type),
    "sendKeys": command(browser_actions.sendKeys),
    "assertText": command(browser_actions.assert_text)
}


def process_report(report, config):
    test_cases = []
    html_report = 0
    for record in report:
        if 'xml' in config and 'html_report' not in record.keys():
            test_cases.append(TestCase(record['name'], record.get('class_name', 'observer'),
                                       record['actual'], '', ''))
            if record['message']:
                test_cases[-1].add_failure_info(record['message'])
        elif 'html' in config and 'html_report' in record.keys():
            with open(f'/tmp/reports/{record["title"]}_{html_report}.html', 'w') as f:
                f.write(record['html_report'])
            html_report += 1

    ts = TestSuite("Observer UI Benchmarking Test ", test_cases)
    with open("/tmp/reports/report.xml", 'w') as f:
        TestSuite.to_file(f, [ts], prettyprint=True)
