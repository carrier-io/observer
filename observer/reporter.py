import os
from uuid import uuid4
from junit_xml import TestCase, TestSuite

from observer.exporter import JsonExporter
from observer.thresholds import Threshold
from observer.util import logger


def complete_report(execution_results, thresholds, args):
    results = []
    report_title = execution_results.report.title
    threshold_results = {"total": len(thresholds), "failed": 0}
    perf_results = JsonExporter(execution_results.computed_results).export()['fields']

    if 'html' in args.report:
        results.append({'html_report': execution_results.report.get_report(), 'title': report_title})

    logger.info(f"=====> Assert thresholds for {report_title}")
    for gate in thresholds:
        target_metric_name = gate["target"]
        threshold = Threshold(gate, perf_results[target_metric_name])
        if not threshold.is_passed():
            threshold_results['failed'] += 1

        results.append(threshold.get_result())
    logger.info("=====>")

    uuid = __process_report(results, args.report)

    return uuid, threshold_results


def __process_report(results, config):
    test_cases = []
    report_uuid = uuid4()
    os.makedirs('/tmp/reports', exist_ok=True)

    for record in results:
        if 'xml' in config and 'html_report' not in record.keys():
            test_cases.append(TestCase(record['name'], record.get('class_name', 'observer'),
                                       record['actual'], '', ''))
            if record['message']:
                test_cases[-1].add_failure_info(record['message'])
        elif 'html' in config and 'html_report' in record.keys():
            with open(f'/tmp/reports/{record["title"]}_{report_uuid}.html', 'w') as f:
                f.write(record['html_report'])

    ts = TestSuite("Observer UI Benchmarking Test ", test_cases)
    with open(f"/tmp/reports/report_{report_uuid}.xml", 'w') as f:
        TestSuite.to_file(f, [ts], prettyprint=True)

    return report_uuid
