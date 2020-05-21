import os
from uuid import uuid4
from junit_xml import TestCase, TestSuite


def complete_report(report, global_thresholds, args):
    results = []
    threshold_results = {"total": len(global_thresholds), "failed": 0}

    expected_time_to_first_paint = _find_threshold_for('time_to_first_paint', global_thresholds)
    expected_speed_index = _find_threshold_for('speed_index', global_thresholds)
    expected_total = _find_threshold_for('total', global_thresholds)

    if 'html' in args.report:
        results.append({'html_report': report.get_report(), 'title': report.title})
    if expected_time_to_first_paint:
        message = ''
        if _is_threshold_violated(expected_time_to_first_paint, report.timing['firstPaint']):
            threshold_results["failed"] += 1

            message = f"First paint exceeded threshold of {expected_time_to_first_paint}ms by " \
                      f"{report.timing['firstPaint'] - expected_time_to_first_paint} ms"
        results.append({"name": f"First Paint {report.title}",
                        "actual": report.timing['firstPaint'], "expected": expected_time_to_first_paint, "message": message})
    if expected_speed_index:
        message = ''
        if _is_threshold_violated(expected_speed_index, report.timing['speedIndex']):
            threshold_results["failed"] += 1

            message = f"Speed index exceeded threshold of {expected_speed_index}ms by " \
                      f"{report.timing['speedIndex'] - expected_speed_index} ms"
        results.append({"name": f"Speed Index {report.title}", "actual": report.timing['speedIndex'],
                        "expected": expected_speed_index, "message": message})
    if expected_total:
        total_load = report.performance_timing['loadEventEnd'] - report.performance_timing['navigationStart']
        message = ''
        if _is_threshold_violated(expected_total, total_load):
            threshold_results["failed"] += 1

            message = f"Total Load exceeded threshold of {expected_total}ms by " \
                      f"{total_load - expected_total} ms"
        results.append({"name": f"Total Load {report.title}", "actual": total_load,
                        "expected": expected_total, "message": message})
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


def _is_threshold_violated(gate, value):
    expected = gate['metric']
    if gate['comparison'] == 'gte':
        return value >= expected

    return True


def _find_threshold_for(name, arr):
    return [x for x in arr if x['target'] == name][0]
