from observer.assertions import assert_test_thresholds, assert_page_thresholds
from observer.models.collector import ResultsCollector
from observer.integrations.galloper import notify_on_test_end, notify_on_command_end
from observer.reporters.html_reporter import generate_html_report
from observer.reporters.junit_reporter import generate_junit_report


def process_results_for_pages(scenario_results, thresholds):
    for execution_result in scenario_results:
        threshold_results = assert_page_thresholds(execution_result, thresholds)

        report_uuid, threshold_results = generate_html_report(execution_result, threshold_results)
        notify_on_command_end(report_uuid, execution_result, threshold_results)


def process_results_for_test(scenario_name, scenario_results, thresholds):
    result_collector = ResultsCollector()
    for r in scenario_results:
        result_collector.add(r.page_identifier, r.to_json())

    threshold_results = assert_test_thresholds(scenario_name, thresholds, result_collector.results)
    junit_report_name = generate_junit_report(scenario_name, threshold_results)
    notify_on_test_end(threshold_results, None, junit_report_name)
