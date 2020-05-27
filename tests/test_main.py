import os

from observer.app import create_parser, execute

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_main_with_data_params():
    args = create_parser().parse_args(
        [
            "-f", f"data.zip",
            # "-d", f"{ROOT_DIR}/data/data.json",
            "-sc", "/tmp/data/webmail.side",
            "-fp", "100",
            "-si", "400",
            "-tl", "500",
            "-r", "html",
            # "-g", "False"
        ])
    execute(args)
