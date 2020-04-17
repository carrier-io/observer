import os
import tempfile
from datetime import datetime
from os import path
from shutil import rmtree
from time import time

import requests
from requests import get
from selene.support.shared import browser, SharedConfig
from selenium.common.exceptions import WebDriverException

from observer.actions import browser_actions
from observer.actions.browser_actions import get_performance_timing, get_performance_metrics, command_type
from observer.constants import listener_address
from observer.exporter import export, GalloperExporter
from observer.processors.results_processor import resultsProcessor
from observer.processors.test_data_processor import get_test_data_processor
from observer.reporter import complete_report
from observer.runner import close_driver, terminate_runner
from observer.util import _pairwise

load_event_end = 0
galloper_api_url = os.getenv("GALLOPER_API_URL", "http://localhost:80/api/v1")
galloper_project_id = int(os.getenv("GALLOPER_PROJECT_ID", "1"))
env = os.getenv("ENV", "")
minio_bucket_name = os.getenv("MINIO_BUCKET_NAME", "reports")


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
    test_name = test['name']
    print(f"\nExecuting test: {test_name}")

    test_data_processor = get_test_data_processor(test_name, args.data)

    report_id = notify_on_test_start(galloper_project_id, test_name, browser_name, env, base_url)

    locators = []
    previous_report_id = None
    visited_pages = 0
    total_thresholds = {
        "total": 0,
        "failed": 0
    }

    for current_command, next_command in _pairwise(test['commands']):
        print(current_command)

        locators.append(current_command)

        report, cmd_results = _execute_command(current_command, next_command, test_data_processor,
                                               is_video_enabled(args))

        if not report:
            continue

        if args.export:
            export(cmd_results, args)

        visited_pages += 1

        thresholds = complete_report(report, args)
        total_thresholds["total"] += thresholds["total"]
        total_thresholds["failed"] += thresholds["failed"]

        if previous_report_id:
            send_report_locators(galloper_project_id, previous_report_id, locators)

        file_name = f"{report.title}_0.html"
        report_path = f"/tmp/reports/{file_name}"
        previous_report_id = notify_on_command_end(galloper_project_id,
                                                   report_id,
                                                   minio_bucket_name,
                                                   cmd_results,
                                                   thresholds, locators, report_path, file_name)

    notify_on_test_end(galloper_project_id, report_id, visited_pages, total_thresholds)


def notify_on_test_start(project_id: int, test_name, browser_name, env, base_url):
    data = {
        "test_name": test_name,
        "base_url": base_url,
        "browser_name": browser_name,
        "env": env,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    res = requests.post(f"{galloper_api_url}/observer/{project_id}", json=data, auth=('user', 'user'))
    return res.json()['id']


def notify_on_test_end(project_id: int, report_id: int, visited_pages, total_thresholds):
    data = {
        "report_id": report_id,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "visited_pages": visited_pages,
        "thresholds_total": total_thresholds["total"],
        "thresholds_failed": total_thresholds["failed"]
    }

    res = requests.put(f"{galloper_api_url}/observer/{project_id}", json=data, auth=('user', 'user'))
    return res.json()


def send_report_locators(project_id: int, report_id: int, locators):
    requests.put(f"{galloper_api_url}/observer/{project_id}/{report_id}", json=locators, auth=('user', 'user'))


def notify_on_command_end(project_id: int, report_id: int, bucket_name, metrics, thresholds, locators, report_path,
                          file_name):
    result = GalloperExporter(metrics).export()

    data = {
        "metrics": result,
        "bucket_name": bucket_name,
        "file_name": file_name,
        "thresholds_total": thresholds["total"],
        "thresholds_failed": thresholds["failed"],
        "locators": locators
    }

    res = requests.post(f"{galloper_api_url}/observer/{project_id}/{report_id}", json=data, auth=('user', 'user'))

    file = {'file': open(report_path, 'rb')}

    requests.post(f"{galloper_api_url}/artifacts/{project_id}/{bucket_name}/{file_name}", files=file,
                  auth=('user', 'user'))

    return res.json()["id"]


def is_video_enabled(args):
    return "html" in args.report and args.video


def _execute_command(current_command, next_command, test_data_processor, enable_video=True):
    global load_event_end
    results = None

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

        if next_is_actionable:
            pass

        if is_navigation_happened() and next_is_actionable:
            browser_actions.wait_for_visibility(next_command['target'])

            load_event_end = get_performance_timing()['loadEventEnd']
            results = get_performance_metrics()
            results['info']['testStart'] = int(current_time)
    except WebDriverException as e:
        print(e)
        return None, None
    finally:
        if not next_is_actionable:
            return None, None

        video_folder = None
        video_path = None
        if enable_video and next_is_actionable:
            video_folder, video_path = stop_recording()

    report = None
    if results and video_folder:
        report = resultsProcessor(video_path, results, video_folder, True, True)

    if video_folder:
        rmtree(video_folder)

    return report, results


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
