from observer.executors.command_executor import execute_command
from observer.processors.test_data_processor import get_test_data_processor
from observer.util import _pairwise, logger, flatten_list


def execute_scenario(scenario, args):
    # test_results = []
    for test in scenario['tests']:
        logger.info(f"Executing test: {test['name']}")
        results = _execute_test(test, args)
        # test_results.append(results)
    # return flatten_list(test_results)


def _execute_test(test, args):
    test_name = test['name']
    # locators = []

    test_data_processor = get_test_data_processor(test_name, args.data)

    # results = []
    for current_command, next_command in _pairwise(test['commands']):
        execution_result = execute_command(current_command, next_command, test_data_processor, args.video)
        # locators.append(current_command)
        # if execution_result.ex:
        #     break
        #
        # if not execution_result.is_ready_for_report():
        #     continue
        #
        # execution_result.locators = locators.copy()
        # results.append(execution_result)

    # return results
