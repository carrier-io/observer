import os
from uuid import uuid4
from junit_xml import TestCase, TestSuite


class Threshold(object):

    def __init__(self, name, gate, actual):
        self.name = name
        self.gate = gate
        self.actual = actual
        self.expected = self.gate['metric']

    def is_violated(self):
        if self.gate['comparison'] == 'gte':
            return self.actual >= self.expected

        return True

    def get_result(self, title):
        message = ""
        if self.is_violated():
            message = f"{self.name} exceeded threshold of {self.expected}ms by " \
                      f"{self.actual - self.expected} ms"

        return {"name": f"{self.name} {title}",
                "actual": self.actual, "expected": self.expected,
                "message": message}


def complete_report(report, global_thresholds, args):
    results = []
    threshold_results = {"total": len(global_thresholds), "failed": 0}

    expected_time_to_first_paint = _find_threshold_for('time_to_first_paint', global_thresholds)
    expected_speed_index = _find_threshold_for('speed_index', global_thresholds)
    expected_total = _find_threshold_for('total', global_thresholds)

    if 'html' in args.report:
        results.append({'html_report': report.get_report(), 'title': report.title})
    if expected_time_to_first_paint:
        # message = ''
        results.append(
            Threshold('First paint', expected_time_to_first_paint, report.timing['firstPaint']).get_result(
                report.title))

        # if _is_threshold_violated(expected_time_to_first_paint, report.timing['firstPaint']):
        #     threshold_results["failed"] += 1
        #
        #     message = f"First paint exceeded threshold of {expected_time_to_first_paint}ms by " \
        #               f"{report.timing['firstPaint'] - expected_time_to_first_paint} ms"
        # results.append({"name": f"First Paint {report.title}",
        #                 "actual": report.timing['firstPaint'], "expected": expected_time_to_first_paint,
        #                 "message": message})
    if expected_speed_index:
        results.append(
            Threshold('Speed index', expected_speed_index, report.timing['speedIndex']).get_result(report.title))
        # message = ''
        # if _is_threshold_violated(expected_speed_index, report.timing['speedIndex']):
        #     threshold_results["failed"] += 1
        #
        #     message = f"Speed index exceeded threshold of {expected_speed_index}ms by " \
        #               f"{report.timing['speedIndex'] - expected_speed_index} ms"
        # results.append({"name": f"Speed Index {report.title}", "actual": report.timing['speedIndex'],
        #                 "expected": expected_speed_index, "message": message})
    if expected_total:
        total_load = report.performance_timing['loadEventEnd'] - report.performance_timing['navigationStart']
        results.append(
            Threshold('Total Load', expected_total, total_load).get_result(report.title))

        # message = ''
        # if _is_threshold_violated(expected_total, total_load):
        #     threshold_results["failed"] += 1
        #
        #     message = f"Total Load exceeded threshold of {expected_total}ms by " \
        #               f"{total_load - expected_total} ms"
        # results.append({"name": f"Total Load {report.title}", "actual": total_load,
        #                 "expected": expected_total, "message": message})
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
    return [x for x in arr if x['target'] == name][0]
