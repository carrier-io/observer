from selene.support.shared import SharedBrowser
from selenium import webdriver

from observer.constants import REMOTE_DRIVER_ADDRESS, RESULTS_REPORT_NAME, RESULTS_BUCKET

browser = None
cfg = None


def get_driver():
    global browser
    if browser is None:
        options = get_browser_options(cfg.browser_name)

        driver = webdriver.Remote(
            command_executor=f'http://{REMOTE_DRIVER_ADDRESS}/wd/hub',
            options=options)

        cfg.driver = driver
        driver.set_window_position(0, 0)
        browser = SharedBrowser(cfg)
    return browser


def get_browser_options(browser_name):
    if "chrome" == browser_name:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.set_capability("version", "83.0")
        chrome_options.set_capability("junit_report", RESULTS_REPORT_NAME)
        chrome_options.set_capability("junit_report_bucket", RESULTS_BUCKET)
        return chrome_options

    if "firefox" == browser_name:
        ff_options = webdriver.FirefoxOptions()
        ff_options.set_capability("version", "63.0")
        return ff_options

    raise Exception(f"Unsupported browser {browser_name}")


def close_driver():
    global browser
    if browser:
        browser.quit()
        browser = None


def set_config(config):
    global cfg
    cfg = config
