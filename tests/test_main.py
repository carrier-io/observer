import os

from observer.app import create_parser, execute

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_main():
    args = create_parser().parse_args(
        ["-f", f"{ROOT_DIR}/data/real-world.side", "-fp", "100", "-si", "400", "-tl", "500", "-r", "html"])
    execute(args)


def test_main_with_data_params():
    args = create_parser().parse_args(
        [
            "-f", f"{ROOT_DIR}/data/webmail.side",
            "-d", f"{ROOT_DIR}/data/data.json",
            # "-e", "influx",
            "-fp", "100",
            "-si", "400",
            "-tl", "500",
            "-r", "html",
            "-g", False
        ])
    execute(args)
