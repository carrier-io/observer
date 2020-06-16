import argparse

from selene.support.shared import SharedConfig

from observer.assertions import assert_page_thresholds, assert_test_thresholds
from observer.collector import ResultsCollector
from observer.driver_manager import set_config
from observer.exporter import JsonExporter
from observer.integrations.galloper import download_file, notify_on_test_start, notify_on_test_end, \
    notify_on_command_end, get_thresholds
from observer.executors.scenario_executor import execute_scenario
from observer.reporters.html_reporter import generate_html_report
from observer.reporters.junit_reporter import generate_junit_report
from observer.thresholds import AggregatedThreshold, Threshold
from observer.util import parse_json_file, str2bool, logger, unzip, wait_for_agent, terminate_runner, flatten_list, \
    filter_thresholds_for


def create_parser():
    parser = argparse.ArgumentParser(description="UI performance benchmarking for CI")
    parser.add_argument("-f", "--file", type=str, default="")
    parser.add_argument("-sc", "--scenario", type=str, default="")
    parser.add_argument("-d", "--data", type=str, default="")
    parser.add_argument("-v", '--video', type=str2bool, default=True)
    parser.add_argument("-r", '--report', action="append", type=str, default=['html'])
    parser.add_argument("-e", '--export', action="append", type=str, default=[])
    parser.add_argument("-g", '--galloper', type=str2bool, default=True)
    parser.add_argument("-l", "--loop", type=int, default=1)
    parser.add_argument("-a", "--aggregation", type=str)
    return parser


def parse_args():
    args, _ = create_parser().parse_known_args()
    return args


def main():
    logger.info("Starting analysis...")
    args = parse_args()
    execute(args)


def execute(args):
    logger.info(f"Start with args {args}")
    if args.video:
        wait_for_agent()

    scenario = get_scenario(args)

    config = SharedConfig()
    config.base_url = scenario['url']
    set_config(config)

    scenario_name = scenario['name']

    notify_on_test_start(scenario_name, config.browser_name, config.base_url, args)

    scenario_results = []
    for i in range(0, args.loop):
        logger.info(f"Executing scenario {scenario_name} loop: {i + 1}")
        results = execute_scenario(scenario, args)
        scenario_results.append(results)
        # close_driver()

    scenario_results = flatten_list(scenario_results)
    thresholds = get_thresholds(scenario_name)
    process_results_for_pages(scenario_results, thresholds)
    process_results_for_test(scenario_name, scenario_results, thresholds)

    if args.video:
        terminate_runner()


def process_results_for_pages(scenario_results, thresholds):
    for execution_result in scenario_results:
        threshold_results = assert_page_thresholds(execution_result, thresholds)

        report_uuid, threshold_results = generate_html_report(execution_result, threshold_results)
        notify_on_command_end(report_uuid, execution_result, threshold_results)


def process_results_for_test(scenario_name, scenario_results, thresholds):
    result_collector = ResultsCollector()
    for r in scenario_results:
        result_collector.add(r.page_identifier, r.to_json())

    threshold_results = assert_test_thresholds(scenario_name, thresholds, result_collector.results)
    junit_report_name = generate_junit_report(scenario_name, threshold_results)
    notify_on_test_end(threshold_results, None, junit_report_name)


def get_scenario(args):
    if args.file:

        file_path = download_file(args.file)
        if file_path.endswith(".zip"):
            unzip(file_path, "/tmp/data")

    return parse_json_file(args.scenario)


if __name__ == "__main__":
    main()
