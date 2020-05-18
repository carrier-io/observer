import argparse
import os
from pathlib import Path

import requests
from junit_xml import TestSuite, TestCase

from observer.constants import GALLOPER_API_URL, GALLOPER_PROJECT_ID, BUCKET_NAME, get_headers
from observer.runner import wait_for_agent
from observer.scenario_executor import execute_scenario
from observer.util import parse_json_file, str2bool, logger


def create_parser():
    parser = argparse.ArgumentParser(description="UI performance benchmarking for CI")
    parser.add_argument("-fp", '--firstPaint', type=int, default=0)
    parser.add_argument("-si", '--speedIndex', type=int, default=0)
    parser.add_argument("-y", "--yaml", type=str, default="")
    parser.add_argument("-f", "--file", type=str, default="")
    parser.add_argument("-d", "--data", type=str, default="")
    parser.add_argument("-tl", '--totalLoad', type=int, default=0)
    parser.add_argument("-v", '--video', type=bool, default=True)
    parser.add_argument("-r", '--report', action="append", type=str, default=['xml'])
    parser.add_argument("-e", '--export', action="append", type=str, default=[])
    parser.add_argument("-g", '--galloper', type=str2bool, default=True)
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
    logger.info("Starting analysis...")
    args = parse_args()
    execute(args)


def execute(args):
    logger.info(f"Start with args {args}")
    scenario = None
    if not args.video:
        wait_for_agent()
    if args.file and os.path.exists(args.file):
        scenario = parse_json_file(args.file)
    elif args.file:
        logger.info(f"Downloading scenario {args.file}")
        file_name = Path(args.file).name
        file_path = download_scenario(file_name)
        scenario = parse_json_file(file_path)
    execute_scenario(scenario, args)


def download_scenario(file_name):
    res = requests.get(f"{GALLOPER_API_URL}/artifacts/{GALLOPER_PROJECT_ID}/{BUCKET_NAME}/{file_name}",
                       headers=get_headers())
    if res.status_code != 200:
        raise Exception(f"Unable to download file {file_name}. Reason {res.reason}")
    file_path = f"/tmp/data/{file_name}"
    open(file_path, 'wb').write(res.content)
    return file_path


if __name__ == "__main__":
    main()
