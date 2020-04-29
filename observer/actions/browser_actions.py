from time import sleep

from observer.constants import check_ui_performance
from selene import have, by, be
from selenium.webdriver.common.keys import Keys

from observer.driver_manager import get_driver


def command(func, actionable=True):
    return func, actionable


def get_locator_strategy(locator):
    if "css=" in locator:
        return locator.replace("css=", "")
    elif "id=" in locator:
        return locator.replace("id=", "#")
    elif "linkText=" in locator:
        return by.link_text(locator.replace("linkText=", ""))


def process_text(text):
    if "${KEY_ENTER}" == text:
        return Keys.ENTER
    return text


def open_url(url, value):
    driver = get_driver()
    driver.open(url)
    for _ in range(1200):
        if driver.execute_script('return document.readyState === "complete" && performance.timing.loadEventEnd > 0'):
            break
        sleep(0.1)


def setWindowSize(size, value):
    print(size)
    s = size.split("x")
    get_driver().driver.set_window_size(s[0], s[1])


def click(locator, value):
    css_or_xpath = get_locator_strategy(locator)
    get_driver().element(css_or_xpath).click()


def type(locator, text):
    css_or_xpath = get_locator_strategy(locator)
    get_driver().element(css_or_xpath).set_value(text)


def sendKeys(locator, text):
    css_or_xpath = get_locator_strategy(locator)
    get_driver().element(css_or_xpath).send_keys(process_text(text))


def assert_text(locator, text):
    css_or_xpath = get_locator_strategy(locator)
    get_driver().element(css_or_xpath).should_have(have.exact_text(text))


def wait_for_visibility(locator):
    get_driver().element(locator).wait_until(be.visible)


def get_performance_timing():
    return get_driver().execute_script("return performance.timing")


def get_performance_metrics():
    return get_driver().driver.execute_script(check_ui_performance)


def get_performance_entities():
    return get_driver().driver.execute_script("return performance.getEntriesByType('resource')")


command_type = {
    "open": command(open_url),
    "setWindowSize": command(setWindowSize, actionable=False),
    "click": command(click),
    "type": command(type),
    "sendKeys": command(sendKeys),
    "assertText": command(assert_text)
}
