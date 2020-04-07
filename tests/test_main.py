import os

from observer.app import main, create_parser

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def test_main():
    args = create_parser().parse_args(["--file", f"{ROOT_DIR}/data/demo.side", "--local",""])
    main(args)
