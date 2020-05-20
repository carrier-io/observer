import argparse
import json
import logging
import os
import zipfile
from pathlib import Path

import requests

from observer.constants import GALLOPER_URL, GALLOPER_PROJECT_ID, TESTS_BUCKET, get_headers

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


def download_file(file_path):
    logger.info(f"Downloading data {file_path} from {TESTS_BUCKET} bucket")

    file_name = Path(file_path).name
    res = requests.get(f"{GALLOPER_URL}/artifacts/{GALLOPER_PROJECT_ID}/{TESTS_BUCKET}/{file_name}",
                       headers=get_headers())
    if res.status_code != 200:
        raise Exception(f"Unable to download file {file_name}. Reason {res.reason}")
    file_path = f"/tmp/data/{file_name}"
    os.makedirs("/tmp/data", exist_ok=True)
    open(file_path, 'wb').write(res.content)
    return file_path


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
