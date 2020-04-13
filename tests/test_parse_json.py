import os

from observer.app import parse_json_file

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_parse_json():
    data = parse_json_file(f"{ROOT_DIR}/data/demo.side")
    assert data
