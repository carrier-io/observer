from os import environ

from selene.support.shared import browser
from selenium import webdriver

driver = None


def get_driver():
    global driver
    remote_driver_address = environ.get("remote", "127.0.0.1:4444")
    if not driver:
        # driver = webdriver.Chrome(chrome.ChromeDriverManager().install())
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--window-size=1360,1020')
        driver = webdriver.Remote(
            command_executor=f'http://{remote_driver_address}/wd/hub',
            desired_capabilities=chrome_options.to_capabilities())
    browser._config.driver = driver
    return browser
