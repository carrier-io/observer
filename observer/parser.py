import json


def parse_tests(data_path):
    with open(data_path) as data:
        return json.load(data)
