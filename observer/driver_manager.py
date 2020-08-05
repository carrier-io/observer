from selene.support.shared import SharedBrowser
from selenium import webdriver

from observer.constants import REMOTE_DRIVER_ADDRESS

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
        browser = SharedBrowser(cfg)
    return browser


def get_browser_options(browser_name):
    if "chrome" == browser_name:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--window-size=1920,1080')
        return chrome_options

    if "firefox" == browser_name:
        ff_options = webdriver.FirefoxOptions()
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
