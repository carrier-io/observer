import os

from observer.app import parse_tests

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_parse_json():
    data = parse_tests(f"{ROOT_DIR}/data/demo.side")
    assert data
