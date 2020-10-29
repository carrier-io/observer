import os
from pathlib import Path

import requests

from observer.constants import GALLOPER_URL, GALLOPER_PROJECT_ID, TESTS_BUCKET, TOKEN
from observer.util import logger


def get_headers():
    if TOKEN:
        return {'Authorization': f"Bearer {TOKEN}"}
    logger.warning("Auth TOKEN is not set!")
    return None


def download_file(file_path):
    logger.info(f"Downloading data {file_path} from {TESTS_BUCKET} bucket")

    file_name = Path(file_path).name

    res = requests.get(f"{GALLOPER_URL}/api/v1/artifacts/{GALLOPER_PROJECT_ID}/{TESTS_BUCKET}/{file_name}",
                       headers=get_headers(), stream=True)
    if res.status_code != 200 or 'html' in res.text:
        raise Exception(f"Unable to download file {file_name}. Reason {res.reason}")
    file_path = f"/tmp/data/{file_name}"
    os.makedirs("/tmp/data", exist_ok=True)
    with open(file_path, 'wb') as fd:
        for chunk in res.iter_content(chunk_size=128):
            fd.write(chunk)
    return file_path
