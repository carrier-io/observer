import os
from shutil import rmtree
from uuid import uuid4

from observer.command_result import CommandExecutionResult
from observer.processors.results_processor import resultsProcessor


def generate_html_report(execution_result: CommandExecutionResult, threshold_results):
    video_folder = execution_result.video_folder
    test_status = get_test_status(threshold_results)

    report = resultsProcessor(test_status, execution_result.video_path,
                              execution_result.computed_results,
                              video_folder,
                              execution_result.screenshot_path)

    if os.path.exists(video_folder):
        rmtree(video_folder)

    report_uuid = save_report(report)
    return report_uuid, threshold_results


def save_report(report):
    report_uuid = uuid4()
    os.makedirs('/tmp/reports', exist_ok=True)
    with open(f'/tmp/reports/{report.title}_{report_uuid}.html', 'w') as f:
        f.write(report.html)
    return report_uuid


def get_test_status(threshold_results):
    if threshold_results['failed'] > 0:
        return "failed"

    return "passed"
