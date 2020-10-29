import argparse
import os

from selene.support.shared import SharedConfig

from observer.constants import TZ, ARTIFACT
from observer.driver_manager import set_config, close_driver, set_args
from observer.executors.scenario_executor import execute_scenario
from observer.integrations.galloper import download_file
from observer.util import parse_json_file, logger, unzip


def create_parser():
    parser = argparse.ArgumentParser(description="UI performance benchmarking for CI")
    parser.add_argument("-f", "--file", type=str, default="")
    parser.add_argument("-sc", "--scenario", type=str, default="")
    parser.add_argument("-d", "--data", type=str, default="")
    parser.add_argument("-r", '--report', action="append", type=str, default=[])
    parser.add_argument("-e", '--export', action="append", type=str, default=[])
    parser.add_argument("-l", "--loop", type=int, default=1)
    parser.add_argument("-a", "--aggregation", type=str, default="max")
    parser.add_argument("-b", "--browser", type=str, default="chrome")
    parser.add_argument("-tid", '--test_id', type=str, default="")
    return parser


def parse_args():
    args, _ = create_parser().parse_known_args()
    return args


def main():
    logger.info("Starting analysis...")
    logger.info(f"Time zone {TZ}")
    args = parse_args()
    execute(args)


def execute(args):
    logger.info(f"Start with args {args}")
    scenario = get_scenario(args)

    config = SharedConfig()
    config.base_url = scenario['url']
    set_config(config)
    set_args(args)

    scenario_name = scenario['name']

    for i in range(0, args.loop):
        logger.info(f"Executing scenario {scenario_name} loop: {i + 1}")
        execute_scenario(scenario, args)

    close_driver()


def get_scenario(args):
    file_name = ARTIFACT
    if not file_name:
        file_name = args.file

    file_path = download_file(file_name)
    target_folder = "/tmp/data"
    if file_path.endswith(".zip"):
        unzip(file_path, target_folder)

    return parse_json_file(os.path.join(target_folder, args.scenario))


if __name__ == "__main__":
    main()
