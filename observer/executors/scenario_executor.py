from observer.executors.command_executor import execute_command
from observer.processors.test_data_processor import get_test_data_processor
from observer.thresholds import AggregatedThreshold
from observer.util import _pairwise, logger, flatten_list


def execute_scenario(scenario, args):
    test_results = []
    for test in scenario['tests']:
        logger.info(f"Executing test: {test['name']}")
        results = _execute_test(test, args)
        test_results.append(results)
    return flatten_list(test_results)


def _execute_test(test, args):
    is_video = is_video_enabled(args)
    test_name = test['name']
    locators = []

    test_data_processor = get_test_data_processor(test_name, args.data)

    results = []
    for current_command, next_command in _pairwise(test['commands']):
        execution_result = execute_command(current_command, next_command, test_data_processor, is_video)
        locators.append(current_command)
        if execution_result.ex:
            break

        if not execution_result.is_ready_for_report():
            continue

        execution_result.locators = locators.copy()
        # exporter.export(execution_result.computed_results)

        # report_uuid, threshold_results = generate_html_report(execution_result, [], args)
        # notify_on_command_end(execution_result, threshold_results, locators, report_uuid)

        # perf_results = exporter.to_json(execution_result.computed_results)
        # results_collector.add(execution_result.page_identifier, execution_result)
        results.append(execution_result)

    return results
    # threshold_results = assert_test_thresholds(test_name, global_thresholds, results_collector.results)
    # junit_report_name = generate_junit_report(test_name, threshold_results)


def is_video_enabled(args):
    return "html" in args.report and args.video
