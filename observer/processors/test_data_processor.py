import abc
import re

from observer.util import parse_json_file


class TestDataProcessor(object):

    def __init__(self, test_name, data_file_path):
        self.test_name = test_name
        self.data_file_path = data_file_path

    @abc.abstractmethod
    def process(self, value):
        pass

    @abc.abstractmethod
    def _read_test_data(self):
        pass

    def _process_test_data(self, current_value, test_data):
        if not current_value:
            return current_value

        if not re.match(r'^\${[a-zA-Z0-9_.-]+}$', current_value):
            return current_value

        value = current_value.replace("${", "").replace("}", "")

        if value not in test_data:
            return value
        return test_data[value]


class JsonFileDataProcessor(TestDataProcessor):

    # processor for json data format
    # {
    #   "testName": {
    #     "field": "value"
    #   }
    # }
    #
    # Example:
    #
    # {
    #   "IncorrectLogin": {
    #     "username": "admin",
    #     "password": "admin"
    #   }
    # }

    def __init__(self, name, args):
        super(JsonFileDataProcessor, self).__init__(name, args)

    def process(self, value):
        test_data = self._read_test_data()
        return self._process_test_data(value, test_data)

    def _read_test_data(self):
        if not self.data_file_path:
            return None

        data = parse_json_file(self.data_file_path)
        if self.test_name not in data:
            return None

        return data[self.test_name]


def get_test_data_processor(test_name, data_file_path):
    if not data_file_path:
        return TestDataProcessor(test_name, data_file_path)

    if data_file_path.endswith(".json"):
        return JsonFileDataProcessor(test_name, data_file_path)

    raise NotImplemented(f"There is no processor for data {data_file_path}")
