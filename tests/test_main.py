import os

from observer.app import create_parser, execute

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_main_with_data_params():
    args = create_parser().parse_args(
        [
            # "-f", f"data.zip",
            # "-d", f"{ROOT_DIR}/data/data.json",
            "-sc", "webmail.side",
            # "-r", "ado",
            "-l", "1",
            "-b", "chrome_84.0",
            "-a", "max"
        ])

    execute(args)
