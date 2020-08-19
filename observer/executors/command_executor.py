from observer.actions.browser_actions import get_command
from observer.util import logger


def execute_command(current_command, test_data_processor):
    logger.info(
        f"{current_command['comment']} [ {current_command['command']}({current_command['target']}) ] "
        f"{current_command['value']}".strip())

    current_target = current_command['target']
    current_value = test_data_processor.process(current_command['value'])
    current_cmd, current_is_actionable = get_command(current_command['command'])

    current_cmd(current_target, current_value)
