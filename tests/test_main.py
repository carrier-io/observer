import os

from observer.app import create_parser, execute
from observer.reporters.azure_devops import AdoClient
from observer.reporters.jira_reporter import JiraClient

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_main_with_data_params():
    args = create_parser().parse_args(
        [
            # "-f", f"data.zip",
            # "-d", f"{ROOT_DIR}/data/data.json",
            "-sc", "/tmp/data/webmail.side",
            "-g", "False",
            "-v", "False",
            # "-r", "ado",
            "-l", "1",
            "-b", "chrome",
            "-a", "max"
        ])
    execute(args)


def test_jira_reporter():
    jira = JiraClient("http://192.168.0.107:8088", "SergeyPirogov", "123456", "DEMO")
    # jira.create_issue("Threshold: all [Total] min value 200 violates rule lte 50", "High", "")
    # issues = jira.get_issues()
    issues = jira.get_issues("75f58c287ddcc1b1eef9ebc85906216c2b6a25b3b9310cfb632de0571ce98c32")
    print(issues)


def test_ado():
    personal_access_token = 'q3se3d23xq6tiaisrz3lp76edvegbmvysvaopyqvhtsaqb7dweza'
    ado = AdoClient('SerhiiPirohov', 'DEMO', personal_access_token, issue_type="issue")
    res = ado.create_issues({}, [])
    print(res)


def test_ff():
    from selenium import webdriver
    ff_options = webdriver.FirefoxOptions()
    driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=ff_options)

    driver.get("http://automation-remarks.com")
    driver.close()
