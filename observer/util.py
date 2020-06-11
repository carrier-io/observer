import argparse
import json
import logging
import math
import os
import zipfile
from time import sleep

import requests

from observer.constants import LISTENER_ADDRESS

logger = logging.getLogger('Observer')

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(name)s] - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def parse_json_file(path):
    if not os.path.exists(path):
        raise Exception(f"No such file {path}")
    with open(path) as data:
        return json.load(data)


def terminate_runner():
    return requests.get(f'http://{LISTENER_ADDRESS}/terminate').content


def wait_for_agent():
    sleep(5)
    for _ in range(120):
        sleep(1)
        try:
            if requests.get(f'http://{LISTENER_ADDRESS}', timeout=1).content == b'OK':
                break
        except:
            pass


def _pairwise(iterable):
    return zip(iterable, iterable[1:])


def str2json(v):
    try:
        return json.loads(v)
    except:
        raise argparse.ArgumentTypeError('Json is not properly formatted.')


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def unzip(path_to_zip_file, target_dir):
    logger.info(f"Unzip {path_to_zip_file} to {target_dir}")
    with zipfile.ZipFile(path_to_zip_file, 'r') as zip_ref:
        zip_ref.extractall(target_dir)


def filter_thresholds_for(name, arr):
    test_scope = [x for x in arr if x['scope'] == name]
    every_scope = [x for x in arr if x['scope'] == 'every']
    return list({x['target']: x for x in every_scope + test_scope}.values())


def percentile(data, percentile):
    size = len(data)
    return sorted(data)[int(math.ceil((size * percentile) / 100)) - 1]


def is_values_match(actual, comparison, expected):
    if comparison == 'gte':
        return actual >= expected
    elif comparison == 'lte':
        return actual <= expected
    elif comparison == 'gt':
        return actual > expected
    elif comparison == 'lt':
        return actual < expected
    elif comparison == 'eq':
        return actual == expected
    return False


def get_aggregated_value(aggregation, metrics):
    if aggregation == 'max':
        return max(metrics)
    elif aggregation == 'min':
        return min(metrics)
    elif aggregation == 'avg':
        return round(sum(metrics) / len(metrics), 2)
    elif aggregation == 'pct95':
        return percentile(metrics, 95)
    elif aggregation == 'pct50':
        return percentile(metrics, 50)
    else:
        raise Exception(f"No such aggregation {aggregation}")


def flatten_list(l):
    return [item for sublist in l for item in sublist]
