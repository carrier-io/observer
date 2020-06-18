import argparse

from selene.support.shared import SharedConfig

from observer.driver_manager import set_config
from observer.executors.scenario_executor import execute_scenario
from observer.integrations.galloper import download_file, notify_on_test_start, get_thresholds
from observer.processors.results_processor import process_results_for_pages, process_results_for_test
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
    parser.add_argument("-a", "--aggregation", type=str, default="max")
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

    logger.info("=====> Reports generation")
    scenario_results = flatten_list(scenario_results)
    thresholds = get_thresholds(scenario_name)
    process_results_for_pages(scenario_results, thresholds)
    process_results_for_test(scenario_name, scenario_results, thresholds)

    if args.video:
        terminate_runner()


def get_scenario(args):
    if args.file:

        file_path = download_file(args.file)
        if file_path.endswith(".zip"):
            unzip(file_path, "/tmp/data")

    return parse_json_file(args.scenario)


if __name__ == "__main__":
    main()
