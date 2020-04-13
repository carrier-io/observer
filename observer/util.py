import argparse
import json


def parse_json_file(path):
    with open(path) as data:
        return json.load(data)


def _pairwise(iterable):
    return zip(iterable, iterable[1:])


def str2json(v):
    try:
        return json.loads(v)
    except:
        raise argparse.ArgumentTypeError('Json is not properly formatted.')
