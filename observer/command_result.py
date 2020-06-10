class CommandExecutionResult(object):

    def __init__(self, results_type=None,
                 page_identificator=None,
                 report=None,
                 raw_results=None,
                 computed_results=None,
                 video_folder=None,
                 video_path=None,
                 screenshot_path=None,
                 generate_report=False,
                 err=None):

        self.results_type = results_type
        self.report = report
        self.raw_results = raw_results
        self.computed_results = computed_results
        self.video_folder = video_folder
        self.video_path = video_path
        self.screenshot_path = screenshot_path
        self.ex = err
        self.page_identificator = page_identificator
        self.generate_report = generate_report

    def is_ready_for_report(self):
        return self.generate_report and self.video_folder and self.computed_results
