from observer.models.exporters import JsonExporter


class CommandExecutionResult(object):

    def __init__(self, results_type=None,
                 page_identifier=None,
                 computed_results=None,
                 video_folder=None,
                 video_path=None,
                 screenshot_path=None,
                 generate_report=False,
                 err=None):
        self.results_type = results_type
        self.computed_results = computed_results
        self.video_folder = video_folder
        self.video_path = video_path
        self.screenshot_path = screenshot_path
        self.ex = err
        self.page_identifier = page_identifier
        self.generate_report = generate_report
        self.locators = None

    def is_ready_for_report(self):
        return self.generate_report and self.computed_results

    def to_json(self):
        return JsonExporter(self.computed_results).export()['fields']
