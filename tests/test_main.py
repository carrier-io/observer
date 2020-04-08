import os

from observer.app import main, create_parser

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_main():
    os.environ.setdefault("ffmpg_path", "ffmpeg")  # for local debug only

    args = create_parser().parse_args(["--file", f"{ROOT_DIR}/data/real-world.side", "-r", "html"])
    main(args)
