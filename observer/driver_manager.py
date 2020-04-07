from os import environ

from selene.support.shared import browser
from selenium import webdriver

driver = None


def get_driver():
    global driver
    remote_driver_address = environ.get("remote", "127.0.0.1:4444")
    if not driver:
        chrome_options = webdriver.ChromeOptions()
        driver = webdriver.Remote(
            command_executor=f'http://{remote_driver_address}/wd/hub',
            desired_capabilities=chrome_options.to_capabilities())
    browser.set_driver(driver)
    return browser
