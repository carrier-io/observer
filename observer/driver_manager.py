from selene.support.shared import browser
from selenium import webdriver

from observer.constants import REMOTE_DRIVER_ADDRESS

driver = None


def get_driver():
    global driver
    if not driver:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--window-size=1360,1020')
        driver = webdriver.Remote(
            command_executor=f'http://{REMOTE_DRIVER_ADDRESS}/wd/hub',
            desired_capabilities=chrome_options.to_capabilities())
    browser._config.driver = driver
    return browser
