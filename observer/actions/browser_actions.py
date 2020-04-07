from selene import have

from observer.driver_manager import get_driver


def get_locator_strategy(locator):
    if "css=" in locator:
        return locator.replace("css=", "")
    elif "id=" in locator:
        return locator.replace("id=", "#")


def open(url, value):
    get_driver().open_url(url)


def setWindowSize(size, value):
    print(size)
    s = size.split("x")
    get_driver().driver.set_window_size(s[0], s[1])


def click(locator, value):
    css_or_xpath = get_locator_strategy(locator)
    get_driver().s(css_or_xpath).click()


def type(locator, text):
    css_or_xpath = get_locator_strategy(locator)
    get_driver().s(css_or_xpath).set_value(text)


def assert_text(locator, text):
    css_or_xpath = get_locator_strategy(locator)
    get_driver().s(css_or_xpath).should_have(have.exact_text(text))
