import argparse
import json
import logging
import os
import zipfile

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


def get_browser_version(info: str):
    return info.lower().split("_")
