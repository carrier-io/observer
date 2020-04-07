from selene.support.shared import browser, SharedConfig

from observer.actions import browser_actions


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
        _execute_command(command)


def _execute_command(command):
    cmd = command['command']
    target = command['target']
    value = command['value']
    c = command_type[cmd]
    c(target, value)


command_type = {
    "open": browser_actions.open,
    "setWindowSize": browser_actions.setWindowSize,
    "click": browser_actions.click,
    "type": browser_actions.type,
    "sendKeys": browser_actions.type,
    "assertText": browser_actions.assert_text
}
