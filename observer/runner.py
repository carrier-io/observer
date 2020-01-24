import tempfile
from os import environ, path
from time import sleep
from selenium import webdriver
from time import time
from selene.support.shared import browser
from selene import by
from requests import get
from observer.constants import check_ui_performance, listener_address
from shutil import rmtree
from observer.processors.results_processor import resultsProcessor

driver = None

def get_driver():
    remote_driver_address = environ.get("remote", "127.0.0.1:4444")
    global driver
    if not driver:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--window-size=1360,1020')
        driver = webdriver.Remote(
            command_executor=f'http://{remote_driver_address}/wd/hub',
            desired_capabilities=chrome_options.to_capabilities())
        browser.set_driver(driver)
    return driver


def execute_step(step_definition):
    get_driver()
    browser.open(step_definition['url'])
    if step_definition.get('el'):
        browser.element(by.xpath(step_definition['el'])).is_displayed()
    for _ in range(1200):
        if browser.execute_script('return document.readyState === "complete" && performance.timing.loadEventEnd > 0'):
            break
        sleep(0.1)


def close_driver():
    browser.quit()


def step(step_definition):
    get_driver()
    start_time = time()
    videofolder = None
    video_path = None
    if step_definition.get('html'):
        get(f'http://{listener_address}/record/start')
    current_time = time() - start_time
    execute_step(step_definition)
    results = driver.execute_script(check_ui_performance)
    results['info']['testStart'] = int(current_time)
    if step_definition.get('html'):
        video_results = get(f'http://{listener_address}/record/stop').content
        videofolder = tempfile.mkdtemp()
        video_path = path.join(videofolder, "Video.mp4")
        with open(video_path, 'w+b') as f:
            f.write(video_results)
    report = resultsProcessor(video_path, results, videofolder, True, step_definition.get('html'))
    if videofolder:
        rmtree(videofolder)
    return report


def terminate_runner():
    return get(f'http://{listener_address}/terminate').content


def wait_for_agent():
    for _ in range(120):
        try:
            if get(f'http://{listener_address}', timeout=1).content == b'OK':
                break
        except:
            pass
        sleep(1)
