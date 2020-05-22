import os
from uuid import uuid4
from junit_xml import TestCase, TestSuite

from observer.exporter import JsonExporter
from observer.util import logger


class Threshold(object):

    def __init__(self, name, gate, actual):
        self.name = name
        self.gate = gate
        self.actual = actual
        self.expected = self.gate['metric']
        self.comparison = gate['comparison']

    def is_passed(self):
        if self.comparison == 'gte':
            return self.actual >= self.expected
        elif self.comparison == 'lte':
            return self.actual <= self.expected
        elif self.comparison == 'gt':
            return self.actual > self.expected
        elif self.comparison == 'lt':
            return self.actual < self.expected
        elif self.comparison == 'eq':
            return self.actual == self.expected
        return True

    def get_result(self, title):
        message = ""
        if not self.is_passed():
            logger.info(
                f"Threshold: [{self.name}] value {self.actual} violates {self.comparison} {self.expected}! [FAILED]")

            message = f"{self.name} exceeded threshold of {self.expected}ms by " \
                      f"{self.actual - self.expected} ms"

        return {"name": f"{self.name} {title}",
                "actual": self.actual, "expected": self.expected,
                "message": message}


def complete_report(execution_results, global_thresholds, args):
    results = []

    report_title = execution_results.report.title
    threshold_results = {"total": len(global_thresholds), "failed": 0}

    expected_time_to_first_paint = _find_threshold_for('time_to_first_paint', global_thresholds)
    expected_time_to_first_byte = _find_threshold_for('time_to_first_byte', global_thresholds)
    expected_speed_index = _find_threshold_for('speed_index', global_thresholds)
    expected_total = _find_threshold_for('total', global_thresholds)
    expected_dom_content_loading = _find_threshold_for('dom_content_loading', global_thresholds)
    expected_dom_processing = _find_threshold_for('dom_processing', global_thresholds)

    perf_results = JsonExporter(execution_results.computed_results).export()['fields']

    if 'html' in args.report:
        results.append({'html_report': execution_results.report.get_report(), 'title': report_title})
    if expected_time_to_first_paint:
        threshold_results['failed'] += 1
        results.append(
            Threshold('First paint', expected_time_to_first_paint, perf_results['time_to_first_paint']).get_result(
                report_title))
    if expected_speed_index:
        threshold_results['failed'] += 1
        results.append(
            Threshold('Speed index', expected_speed_index, perf_results['speed_index']).get_result(report_title))
    if expected_total:
        threshold_results['failed'] += 1
        results.append(
            Threshold('Total Load', expected_total, perf_results['total']).get_result(report_title))
    if expected_time_to_first_byte:
        threshold_results['failed'] += 1
        results.append(
            Threshold('First byte', expected_time_to_first_byte, perf_results['time_to_first_byte']).get_result(
                report_title))

    if expected_dom_content_loading:
        threshold_results['failed'] += 1
        results.append(
            Threshold('DOM loading', expected_dom_content_loading, perf_results['dom_content_loading']).get_result(
                report_title))

    if expected_dom_processing:
        threshold_results['failed'] += 1
        results.append(
            Threshold('DOM processing', expected_dom_processing, perf_results['dom_processing']).get_result(
                report_title))

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


def _find_threshold_for(name, arr):
    result = [x for x in arr if x['target'] == name]
    if result:
        return result[0]
