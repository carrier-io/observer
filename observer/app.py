import argparse

from selene.support.shared import SharedConfig

from observer.collector import ResultsCollector
from observer.driver_manager import set_config
from observer.integrations.galloper import download_file, notify_on_test_start, notify_on_test_end, \
    notify_on_command_end, get_thresholds
from observer.executors.scenario_executor import execute_scenario
from observer.reporters.html_reporter import generate_html_report
from observer.thresholds import AggregatedThreshold
from observer.util import parse_json_file, str2bool, logger, unzip, wait_for_agent, terminate_runner, flatten_list


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

    notify_on_test_start(scenario_name, config.browser_name, config.base_url)

    scenario_results = []
    for i in range(0, args.loop):
        logger.info(f"Executing scenario {scenario_name} loop: {i + 1}")
        results = execute_scenario(scenario, args)
        scenario_results.append(results)
        # close_driver()

    result_collector = ResultsCollector()
    scenario_results = flatten_list(scenario_results)

    for execution_result in scenario_results:
        report_uuid, threshold_results = generate_html_report(execution_result, [], args)
        notify_on_command_end(report_uuid, execution_result, threshold_results)

    for r in scenario_results:
        result_collector.add(r.page_identifier, r.to_json())

    threshold_results = assert_test_thresholds(scenario_name, result_collector.results)

    notify_on_test_end(threshold_results, None, "")

    if args.video:
        terminate_runner()


def get_scenario(args):
    if args.file:

        file_path = download_file(args.file)
        if file_path.endswith(".zip"):
            unzip(file_path, "/tmp/data")

    return parse_json_file(args.scenario)


def assert_test_thresholds(test_name, execution_results):
    all_scope_thresholds = get_thresholds(test_name)

    threshold_results = {"total": len(all_scope_thresholds), "failed": 0, "details": []}

    if not all_scope_thresholds:
        return threshold_results

    logger.info(f"=====> Assert aggregated thresholds for {test_name}")
    checking_result = []
    for gate in all_scope_thresholds:
        threshold = AggregatedThreshold(gate, execution_results)
        if not threshold.is_passed():
            threshold_results['failed'] += 1
        checking_result.append(threshold.get_result())

    threshold_results["details"] = checking_result
    logger.info("=====>")

    return threshold_results


if __name__ == "__main__":
    main()
