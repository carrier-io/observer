class CommandExecutionResult(object):

    def __init__(self, results_type=None, page_identificator=None, report=None, raw_results=None, computed_results=None,
                 err=None):
        self.results_type = results_type
        self.report = report
        self.raw_results = raw_results
        self.computed_results = computed_results
        self.ex = err
        self.page_identificator = page_identificator
