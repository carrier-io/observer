from selene.support.shared import SharedBrowser, SharedConfig
from selenium import webdriver

from observer.constants import REMOTE_DRIVER_ADDRESS
from webdriver_manager.chrome import ChromeDriverManager

browser = None
cfg = None


def get_driver():
    global browser
    if browser is None:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--window-size=1360,1020')
        driver = webdriver.Remote(
            command_executor=f'http://{REMOTE_DRIVER_ADDRESS}/wd/hub',
            desired_capabilities=chrome_options.to_capabilities())

        cfg.driver = driver
        browser = SharedBrowser(cfg)
    return browser


def close_driver():
    global browser
    if browser:
        browser.quit()
        browser = None


def set_config(config):
    global cfg
    cfg = config
