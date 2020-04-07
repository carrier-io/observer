from selene.support.shared import browser
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

driver = None

def get_driver():
    global driver
    if not driver:
        driver = webdriver.Chrome(ChromeDriverManager().install())
    browser.set_driver(driver)
    return browser
