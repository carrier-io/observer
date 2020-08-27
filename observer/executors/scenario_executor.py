from observer.executors.command_executor import execute_command
from observer.processors.test_data_processor import get_test_data_processor
from observer.util import  logger


def execute_scenario(scenario, args):
    for test in scenario['tests']:
        logger.info(f"Executing test: {test['name']}")
        _execute_test(test, args)


def _execute_test(test, args):
    test_name = test['name']
    test_data_processor = get_test_data_processor(test_name, args.data)
    for current_command in test['commands']:
        execute_command(current_command, test_data_processor)

