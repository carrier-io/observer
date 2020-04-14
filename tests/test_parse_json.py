import os

from observer.app import parse_json_file
from observer.exporter import export_to_telegraph_json

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_parse_json():
    data = parse_json_file(f"{ROOT_DIR}/data/demo.side")
    assert data


def test_export_to_telegraph_json():
    json_data = export_to_telegraph_json([])
    assert json_data
