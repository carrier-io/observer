import argparse
from json import loads
from observer.runner import step, close_driver, terminate_runner
from junit_xml import TestSuite, TestCase


def str2json(v):
    try:
        return loads(v)
    except:
        raise argparse.ArgumentTypeError('Json is not properly formatted.')


def parse_args():
    parser = argparse.ArgumentParser(description="UI performance benchmarking for CI")
    parser.add_argument("-s", '--step', action="append", type=str2json)
    parser.add_argument("-fp", '--firstPaint', type=int, default=0)
    parser.add_argument("-si", '--speedIndex', type=int, default=0)
    parser.add_argument("-tl", '--totalLoad', type=int, default=0)
    parser.add_argument("-r", '--report', action="append", type=str, default=['xml'])
    args, _ = parser.parse_known_args()
    return args


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


def main():
    args = parse_args()
    results = []
    for st in args.step:
        if 'html' in args.report:
            st['html'] = True
        report = step(st)
        if st.get('html'):
            results.append({'html_report': report.get_report(), 'title': report.title})
        if args.firstPaint > 0:
            message = ''
            if args.firstPaint < report.timing['firstPaint']:
                message = f"First paint exceeded threshold of {args.firstPaint}ms by " \
                          f"{report.timing['firstPaint']-args.firstPaint} ms"
            results.append({"name": f"First Paint {report.title}",
                            "actual": report.timing['firstPaint'], "expected": args.firstPaint, "message": message})
        if args.speedIndex > 0:
            message = ''
            if args.speedIndex < report.timing['speedIndex']:
                message = f"Speed index exceeded threshold of {args.speedIndex}ms by " \
                          f"{report.timing['speedIndex']-args.speedIndex} ms"
            results.append({"name": f"Speed Index {report.title}",  "actual": report.timing['speedIndex'],
                            "expected": args.speedIndex, "message": message})
        if args.totalLoad > 0:
            totalLoad = report.performance_timing['loadEventEnd']-report.performance_timing['navigationStart']
            message = ''
            if args.totalLoad < totalLoad:
                message = f"Total Load exceeded threshold of {args.totalLoad}ms by " \
                          f"{totalLoad-args.speedIndex} ms"
            results.append({"name": f"Total Load {report.title}",  "actual": totalLoad,
                            "expected": args.totalLoad, "message": message})
    process_report(results, args.report)
    close_driver()
    terminate_runner()


if __name__ == "__main__":
    main()
