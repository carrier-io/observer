import argparse

from selene.support.shared import SharedConfig

from observer.driver_manager import close_driver, set_config
from observer.integrations.galloper import download_file
from observer.scenario_executor import execute_scenario
from observer.util import parse_json_file, str2bool, logger, unzip, wait_for_agent


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

    if args.file:

        file_path = download_file(args.file)
        if file_path.endswith(".zip"):
            unzip(file_path, "/tmp/data")

    scenario = parse_json_file(args.scenario)

    config = SharedConfig()
    config.base_url = scenario['url']
    set_config(config)

    for i in range(0, args.loop):
        logger.info(f"Executing scenario loop: {i + 1}")

        execute_scenario(scenario, config, args)

        close_driver()

    # if args.video:
    #     terminate_runner()


if __name__ == "__main__":
    main()
