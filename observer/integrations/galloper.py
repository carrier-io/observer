import os
from pathlib import Path

import requests
from datetime import datetime
from observer.constants import GALLOPER_URL, GALLOPER_PROJECT_ID, TESTS_BUCKET, TOKEN, ENV, RESULTS_BUCKET, \
    REPORTS_BUCKET
from observer.exporter import GalloperExporter
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
                       headers=get_headers())
    if res.status_code != 200:
        raise Exception(f"Unable to download file {file_name}. Reason {res.reason}")
    file_path = f"/tmp/data/{file_name}"
    os.makedirs("/tmp/data", exist_ok=True)
    open(file_path, 'wb').write(res.content)
    return file_path


def get_thresholds(test_name):
    logger.info(f"Get thresholds for: {test_name} {ENV}")
    res = requests.get(
        f"{GALLOPER_URL}/api/v1/thresholds/{GALLOPER_PROJECT_ID}/ui?name={test_name}&environment={ENV}&order=asc",
        headers=get_headers())

    if res.status_code != 200:
        raise Exception(f"Can not get thresholds, Reasons {res.reason}")

    return res.json()


def notify_on_test_start(test_name, browser_name, base_url):
    data = {
        "test_name": test_name,
        "base_url": base_url,
        "browser_name": browser_name,
        "env": ENV,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    res = requests.post(f"{GALLOPER_URL}/api/v1/observer/{GALLOPER_PROJECT_ID}", json=data,
                        headers=get_headers())
    return res.json()['id']


def notify_on_test_end(report_id: int, visited_pages, total_thresholds, exception, junit_report_name):
    logger.info(f"About to notify on test end for report {report_id}")

    data = {
        "report_id": report_id,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "visited_pages": visited_pages,
        "thresholds_total": total_thresholds["total"],
        "thresholds_failed": total_thresholds["failed"]
    }

    if exception:
        data["exception"] = str(exception)

    res = requests.put(f"{GALLOPER_URL}/api/v1/observer/{GALLOPER_PROJECT_ID}", json=data,
                       headers=get_headers())

    upload_artifacts(RESULTS_BUCKET, f"/tmp/reports/{junit_report_name}", junit_report_name)
    return res.json()


def send_report_locators(project_id: int, report_id: int, exception):
    requests.put(f"{GALLOPER_URL}/api/v1/observer/{project_id}/{report_id}",
                 json={"exception": exception, "status": ""},
                 headers=get_headers())


def notify_on_command_end(report_id: int, results_type, metrics, thresholds, locators, report_uuid,
                          name):
    logger.info(f"About to notify on command end for report {report_id}")
    result = GalloperExporter(metrics).export()

    file_name = f"{name}_{report_uuid}.html"
    report_path = f"/tmp/reports/{file_name}"

    data = {
        "name": name,
        "type": results_type,
        "metrics": result,
        "bucket_name": REPORTS_BUCKET,
        "file_name": file_name,
        "resolution": metrics['info']['windowSize'],
        "browser_version": metrics['info']['browser'],
        "thresholds_total": thresholds["total"],
        "thresholds_failed": thresholds["failed"],
        "locators": locators
    }

    res = requests.post(f"{GALLOPER_URL}/api/v1/observer/{GALLOPER_PROJECT_ID}/{report_id}", json=data,
                        headers=get_headers())

    upload_artifacts(REPORTS_BUCKET, report_path, file_name)

    return res.json()["id"]


def upload_artifacts(bucket_name, artifact_path, file_name):
    file = {'file': open(artifact_path, 'rb')}

    res = requests.post(f"{GALLOPER_URL}/api/v1/artifacts/{GALLOPER_PROJECT_ID}/{bucket_name}/{file_name}", files=file,
                        headers=get_headers())
    return res.json()
