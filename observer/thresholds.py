from observer.util import logger, get_actual_aggregated_value


class Threshold(object):

    def __init__(self, gate, actual):
        self.name = gate['target'].replace("_", " ").capitalize()
        self.gate = gate
        self.actual = actual
        self.expected = gate['metric']
        self.comparison = gate['comparison']

    def is_passed(self):
        if self.comparison == 'gte':
            return self.actual >= self.expected
        elif self.comparison == 'lte':
            return self.actual <= self.expected
        elif self.comparison == 'gt':
            return self.actual > self.expected
        elif self.comparison == 'lt':
            return self.actual < self.expected
        elif self.comparison == 'eq':
            return self.actual == self.expected
        return False

    def get_result(self, title):
        message = ""
        if not self.is_passed():
            logger.info(
                f"Threshold: [{self.name}] value {self.actual} violates rule {self.comparison} {self.expected}! [FAILED]")

            message = f"{self.name} violated threshold of {self.expected}ms by " \
                      f"{self.actual - self.expected} ms"
        else:
            logger.info(
                f"Threshold: [{self.name}] value {self.actual} comply with rule {self.comparison} {self.expected}! [PASSED]")

        return {"name": f"{self.name}",
                "actual": self.actual, "expected": self.expected,
                "message": message}


class AggregatedThreshold(Threshold):

    def __init__(self, gate, values):
        target_metric_name = gate['target']
        self.aggregation = gate['aggregation']
        actual = get_actual_aggregated_value(target_metric_name, values, self.aggregation)
        super().__init__(gate, actual)

    def get_result(self, title):
        message = ""
        if not self.is_passed():
            logger.info(
                f"Threshold: [{self.name}] {self.aggregation} value {self.actual} violates rule {self.comparison} {self.expected}! [FAILED]")
            message = f"{self.name} violated threshold of {self.aggregation} {self.expected}ms by " \
                      f"{self.actual - self.expected} ms"
        else:
            logger.info(
                f"Threshold: [{self.name}] {self.aggregation} value {self.actual} comply with rule {self.comparison} {self.expected}! [PASSED]")

        return {"name": f"{self.name}",
                "actual": self.actual, "expected": self.expected,
                "message": message}
