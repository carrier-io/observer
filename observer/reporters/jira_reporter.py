from jira import JIRA

from observer.constants import JIRA_URL, JIRA_USER, JIRA_PASSWORD, JIRA_PROJECT
from observer.util import logger


class JiraClient(object):

    def __init__(self, url, user, password, project):
        self.url = url
        self.password = password
        self.user = user
        self.project = project.upper()
        self.client = self.__connect()

    def __connect(self):
        try:
            jira = JIRA(self.url, basic_auth=(self.user, self.password))
        except Exception as e:
            logger.error(f"Failed to connect to Jira {self.url} {e}")
            raise e

        projects = [project.key for project in jira.projects()]
        if self.project not in projects:
            raise Exception(f"No such project {self.project}")

        return jira

    def create_issue(self, title, priority, description):
        issue_data = {
            'project': {'key': self.project},
            'issuetype': 'Bug',
            'summary': title,
            'description': description,
            'priority': {'name': priority},
            'labels': ['observer', 'ui_performance']
        }

        issue = self.client.create_issue(fields=issue_data)
        logger.info(f'  \u2713 was created: {issue.key}')

    def create_issues(self, scenario, data):
        field_list = []
        for d in data:
            steps = []
            for i, locator in enumerate(d['raw_result'].locators, 1):
                command = locator['command']
                text = f"{command} {locator['target']}"
                if command == "open":
                    text = f"{command} {scenario['url']}{locator['target']}"

                steps.append(f"{i}. {text}")

            steps = "\n".join(steps)

            description = f"""{d['message']}
                          
                          Steps:\n {steps}"""

            field_list.append({
                'project': {'key': self.project},
                'issuetype': 'Bug',
                'summary': d['message'],
                'description': description,
                'priority': {'name': "High"},
                'labels': ['observer', 'ui_performance', scenario['name']]
            })

        self.client.create_issues(field_list)


def notify_jira(scenario, threshold_results):
    jira = JiraClient(JIRA_URL, JIRA_USER, JIRA_PASSWORD, JIRA_PROJECT)
    jira.create_issues(scenario, threshold_results["details"])
