from selene.support.shared import SharedBrowser
from selenium import webdriver
from selenium.webdriver.webkitgtk.options import Options

from observer.constants import REMOTE_DRIVER_ADDRESS, RESULTS_REPORT_NAME, RESULTS_BUCKET, ENV, TZ, GALLOPER_PROJECT_ID

browser = None
cfg = None
exec_args = None


def get_driver():
    global browser
    if browser is None:
        options = get_browser_options(cfg.browser_name, exec_args)

        driver = webdriver.Remote(
            command_executor=f'http://{REMOTE_DRIVER_ADDRESS}/wd/hub',
            options=options)

        cfg.driver = driver
        driver.set_window_position(0, 0)
        browser = SharedBrowser(cfg)
    return browser


def get_browser_options(browser_name, args):
    options = Options()

    if "chrome" == browser_name:
        options = webdriver.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.set_capability("version", "83.0")

    if "firefox" == browser_name:
        options = webdriver.FirefoxOptions()
        options.set_capability("version", "63.0")

    if options.capabilities.get("browserName") == 'MiniBrowser':
        raise Exception(f"Unsupported browser {browser_name}")

    if 'junit' in args.report:
        options.set_capability("junit_report", RESULTS_REPORT_NAME)
        options.set_capability("junit_report_bucket", RESULTS_BUCKET)

    options.set_capability("env", ENV)
    options.set_capability('tz', TZ)
    options.set_capability('galloper_project_id', GALLOPER_PROJECT_ID)

    return options


def close_driver():
    global browser
    if browser:
        browser.quit()
        browser = None


def set_config(config):
    global cfg
    cfg = config


def set_args(args):
    global exec_args
    exec_args = args
