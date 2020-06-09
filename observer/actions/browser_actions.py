from io import BytesIO
from time import sleep

from PIL import Image
from selene import have, by, be
from selenium.webdriver.common.keys import Keys

from observer.constants import check_ui_performance
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
    elif "xpath=" in locator:
        return by.xpath(locator.replace("xpath=", ""))
    else:
        raise NotImplementedError(f"Wrong locator format {locator}")


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


def get_dom():
    return get_driver().driver.page_source


def get_dom_size():
    return get_driver().driver.execute_script("return document.getElementsByTagName('*').length")


def get_current_url():
    return get_driver().driver.current_url


def take_full_screenshot(save_path):
    driver = get_driver()
    # initiate value
    save_path = save_path + '.png' if save_path[-4::] != '.png' else save_path
    img_li = []  # to store image fragment
    offset = 0  # where to start

    # js to get height
    height = driver.driver.execute_script('return Math.max('
                                          'document.documentElement.clientHeight, window.innerHeight);')

    # js to get the maximum scroll height
    # Ref--> https://stackoverflow.com/questions/17688595/finding-the-maximum-scroll-position-of-a-page
    max_window_height = driver.driver.execute_script('return Math.max('
                                                     'document.body.scrollHeight, '
                                                     'document.body.offsetHeight, '
                                                     'document.documentElement.clientHeight, '
                                                     'document.documentElement.scrollHeight, '
                                                     'document.documentElement.offsetHeight);')

    # looping from top to bottom, append to img list
    # Ref--> https://gist.github.com/fabtho/13e4a2e7cfbfde671b8fa81bbe9359fb
    while offset < max_window_height:
        # Scroll to height
        driver.driver.execute_script(f'window.scrollTo(0, {offset});')
        img = Image.open(BytesIO((driver.driver.get_screenshot_as_png())))
        img_li.append(img)
        offset += height

    # Stitch image into one
    # Set up the full screen frame
    img_frame_height = sum([img_frag.size[1] for img_frag in img_li])
    img_frame = Image.new('RGB', (img_li[0].size[0], img_frame_height))
    offset = 0
    for img_frag in img_li:
        img_frame.paste(img_frag, (0, offset))
        offset += img_frag.size[1]
    img_frame.save(save_path)
    return save_path


command_type = {
    "open": command(open_url),
    "setWindowSize": command(setWindowSize, actionable=False),
    "click": command(click),
    "type": command(type),
    "sendKeys": command(sendKeys),
    "assertText": command(assert_text)
}
