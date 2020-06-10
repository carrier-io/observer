import os
from shutil import rmtree
from uuid import uuid4

from observer.command_result import CommandExecutionResult
from observer.exporter import JsonExporter
from observer.processors.results_processor import resultsProcessor
from observer.thresholds import Threshold
from observer.util import logger, filter_thresholds_for


def generate_html_report(execution_result: CommandExecutionResult, thresholds, args):
    video_folder = execution_result.video_folder

    report = resultsProcessor(execution_result.video_path,
                              execution_result.computed_results,
                              video_folder,
                              execution_result.screenshot_path, True, True)

    if os.path.exists(video_folder):
        rmtree(video_folder)

    return complete_report(report, execution_result, thresholds, args)


def complete_report(report, execution_result, thresholds, args):
    results = []
    report_title = report.title
    scoped_thresholds = filter_thresholds_for(report_title, thresholds)

    threshold_results = {"total": len(scoped_thresholds), "failed": 0}
    perf_results = JsonExporter(execution_result.computed_results).export()['fields']

    if 'html' in args.report:
        results.append({'html_report': report.report, 'title': report_title})

    logger.info(f"=====> Assert thresholds for {report_title}")
    for gate in scoped_thresholds:
        target_metric_name = gate["target"]
        threshold = Threshold(gate, perf_results[target_metric_name])
        if not threshold.is_passed():
            threshold_results['failed'] += 1

        results.append(threshold.get_result())
    logger.info("=====>")

    uuid = __process_report(results, args.report)

    return uuid, threshold_results


def __process_report(results, config):
    report_uuid = uuid4()
    os.makedirs('/tmp/reports', exist_ok=True)

    for record in results:
        if 'html' in config and 'html_report' in record.keys():
            with open(f'/tmp/reports/{record["title"]}_{report_uuid}.html', 'w') as f:
                f.write(record['html_report'])

    return report_uuid
