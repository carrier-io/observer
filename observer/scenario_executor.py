from selene.support.shared import browser, SharedConfig
from selenium.common.exceptions import WebDriverException
from time import time
from observer.actions import browser_actions
from observer.constants import check_ui_performance
from observer.driver_manager import get_driver

load_event_end = 0


def execute_scenario(scenario):
    urls = scenario['urls']
    config = SharedConfig()
    config.base_url = urls[0]
    browser._config = config
    for test in scenario['tests']:
        _execute_test(test)


def _execute_test(test):
    print(f"'\nExecuting test: {test['name']}")
    for command in test['commands']:
        print(command)
        performance_metrics = _execute_command(command)
        print(performance_metrics)


def _execute_command(command):
    global load_event_end
    results = None

    cmd = command['command']
    target = command['target']
    value = command['value']
    c = command_type[cmd]
    start_time = time()
    current_time = time() - start_time
    try:
        c(target, value)

        if is_navigation_happened():
            load_event_end = get_performance_timing()['loadEventEnd']
            results = get_performance_metrics()
            results['info']['testStart'] = int(current_time)
    except WebDriverException:
        return None

    return results


def is_navigation_happened():
    latest_load_event_end = get_performance_timing()['loadEventEnd']
    if latest_load_event_end != load_event_end:
        return True

    return False


def get_performance_timing():
    return get_driver().execute_script("return performance.timing")


def get_performance_metrics():
    return get_driver().execute_script(check_ui_performance)


command_type = {
    "open": browser_actions.open,
    "setWindowSize": browser_actions.setWindowSize,
    "click": browser_actions.click,
    "type": browser_actions.type,
    "sendKeys": browser_actions.type,
    "assertText": browser_actions.assert_text
}
