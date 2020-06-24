import json

from requests import post

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
        body = []

        fields_mapping = {
            "/fields/System.Title": "Test",
            "/fields/Microsoft.VSTS.Common.Priority": PRIORITY_MAPPING['High'],
            "/fields/System.Description": "description",
            "/fields/System.AreaPath": self.team,
            "/fields/System.IterationPath": self.team
        }

        for key, value in fields_mapping.items():
            if value:
                _piece = {"op": "add", "path": key, "value": value}
                body.append(_piece)

        return post(self.url, auth=self.auth, json=body,
                    headers={'content-type': 'application/json-patch+json'})
