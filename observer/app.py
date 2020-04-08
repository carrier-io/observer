import os
from observer.parser import parse_tests
import argparse
from json import loads
from observer.runner import wait_for_agent
from junit_xml import TestSuite, TestCase

from observer.scenario_executor import execute_scenario


def str2json(v):
    try:
        return loads(v)
    except:
        raise argparse.ArgumentTypeError('Json is not properly formatted.')


def create_parser():
    parser = argparse.ArgumentParser(description="UI performance benchmarking for CI")
    parser.add_argument("-s", '--step', action="append", type=str2json)
    parser.add_argument("-fp", '--firstPaint', type=int, default=0)
    parser.add_argument("-si", '--speedIndex', type=int, default=0)
    parser.add_argument("-y", "--yaml", type=str, default="")
    parser.add_argument("-f", "--file", type=str, default="")
    parser.add_argument("-tl", '--totalLoad', type=int, default=0)
    parser.add_argument("-v", '--video', type=bool, default=True)
    parser.add_argument("-r", '--report', action="append", type=str, default=['xml'])
    return parser


def parse_args():
    args, _ = create_parser().parse_known_args()
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
    execute(args)


def execute(args):
    if not args.video:
        wait_for_agent()
    if args.file and os.path.exists(args.file):
        scenario = parse_tests(args.file)
        execute_scenario(scenario, args)


if __name__ == "__main__":
    print("Starting analysis...")
    main()
