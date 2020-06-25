import hashlib

from requests import post

from observer.constants import ADO_ORGANIZATION, ADO_PROJECT, ADO_TOKEN, ADO_TEAM
from observer.util import logger

PRIORITY_MAPPING = {"Critical": 1, "High": 1, "Medium": 2, "Low": 3, "Info": 4}


class AdoClient(object):

    def __init__(self, organization, project, personal_access_token,
                 team=None, issue_type="issue", rules="false", notify="false"):
        self.auth = ('', personal_access_token)
        self.team = f"{project}"
        if team:
            self.team = f"{project}\\{team}"

        self.url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/' \
                   f'${issue_type}?bypassRules={rules}&suppressNotifications={notify}&api-version=5.1'

        self.query_url = f'https://dev.azure.com/{organization}/{project}/_apis/wit/wiql?api-version=5.1'

    def get_issues(self, issue_hash=None):
        q = f"SELECT [System.Id] From WorkItems Where [System.Description] Contains \"{issue_hash}\""
        data = post(self.query_url, auth=self.auth, json={"query": q},
                    headers={'content-type': 'application/json'}).json()
        return data["workItems"]

    def create_issues(self, scenario, data):

        for d in data:
            if d['status'] == 'passed':
                continue

            issue_hash = hashlib.sha256(
                f"{d['scope']} {d['name']} {d['aggregation']} {d['raw_result'].page_identifier}".encode(
                    'utf-8')).hexdigest()

            if len(self.get_issues(issue_hash)) > 0:
                continue

            logger.info(f"=====> About to crate Azure DevOps issues")

            steps = []
            for i, locator in enumerate(d['raw_result'].locators, 1):
                command = locator['command']
                value = locator["value"]
                action = "to" if value != "" else "on"
                text = f"*{command}* {value} {action}  *{locator['target']}*"
                if command == "open":
                    text = f"*{command}* {action} {scenario['url']}{locator['target']}"

                steps.append(f"{i}. {text}")

            steps = "\n".join(steps)

            summary = f"{d['scope'].capitalize()} [{d['name']}] {d['aggregation']} value violates threshold rule for {scenario['name']}"

            description = f"""Value {d['actual']} violates threshold rule: {d['scope']} [{d['name']}] {d['aggregation']}
            {d['rule']} {d['expected']} for {scenario['name']}"

                                      Steps:\n {steps}

                                      *Issue Hash:* {issue_hash}  
                        """

            fields_mapping = {
                "/fields/System.Title": summary,
                "/fields/Microsoft.VSTS.Common.Priority": PRIORITY_MAPPING['High'],
                "/fields/System.Description": description,
                "/fields/System.AreaPath": self.team,
                "/fields/System.IterationPath": self.team
            }

            body = []
            for key, value in fields_mapping.items():
                if value:
                    _piece = {"op": "add", "path": key, "value": value}
                    body.append(_piece)

            res = post(self.url, auth=self.auth, json=body,
                       headers={'content-type': 'application/json-patch+json'})

            logger.info(f"Azure DevOps issue {res.json()['id']} has been created")


def notify_azure_devops(scenario, threshold_results):
    client = AdoClient(ADO_ORGANIZATION, ADO_PROJECT, ADO_TOKEN, ADO_TEAM)
    client.create_issues(scenario, threshold_results["details"])
