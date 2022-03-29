#!/usr/bin/env python

import os
import sys
import json
import requests


class Sentry():
    def __init__(self, base_url, org, token):
        self.base_url = base_url
        self.org = org
        self.token = token

    def _get_api(self, endpoint):
        """HTTP GET the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json',}
        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, headers=headers)
        return response.json()

    def _get_api_pagination(self, endpoint):
        """HTTP GET the Sentry API, following pagination links"""

        headers = {'Authorization': f'Bearer {self.token}'}

        results = []
        url = f'{self.base_url}{endpoint}'
        next = True
        while next:
            response = requests.get(url, headers=headers)
            results.extend(response.json())

            url = response.links.get('next', {}).get('url')
            next = response.links.get('next', {}).get('results') == 'true'
            if url == None:
                next = False

        return results
    
    def _put_api(self, endpoint, data=None):
        """HTTP PUT the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'}
        url = f'{self.base_url}{endpoint}'
        return requests.put(url, headers=headers, data=data)

    def _post_api(self, endpoint, data=None):
        """HTTP POST the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json',}
        url = f'{self.base_url}{endpoint}'
        return requests.post(url, headers=headers, data=data)

    def _delete_api(self, endpoint):
        """HTTP DELETE the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'

        return requests.delete(url, headers=headers)

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api(f'/api/0/organizations/{self.org}/projects/')
        return [project.get('slug', '') for project in results]
    
    def create_project_issue_alert(self, project, data=None):
        """Create a issue alert for a Sentry project"""

        return self._post_api(f'/api/0/projects/{self.org}/{project}/rules/', data=data)

    def create_project_metric_alert(self, project, data=None):
        """Create a metric alert for a Sentry project"""

        return self._post_api(f'/api/0/projects/{self.org}/{project}/alert-rules/', data=data)
        

    def update_project_issue_alert(self, project, alertID, data=None):
        """Update the issue alert for a Sentry project"""

        return self._put_api(f'/api/0/projects/{self.org}/{project}/rules/{alertID}/', data=data)

    def update_project_metric_alert(self, project, alertID, data=None):
        """Update the metric alert for a Sentry project"""
        return self._put_api(f'/api/0/projects/{self.org}/{project}/alert-rules/{alertID}/', data=data)

    def get_project_alerts(self, project):
        """Return a list of alerts for Sentry project"""

        return self._get_api(f'/api/0/projects/{self.org}/{project}/combined-rules/')

    def delete_project_issue_alert(self, project, ruleId):
        """Delete an alert for a Sentry project"""

        return self._delete_api(f'/api/0/projects/{self.org}/{project}/rules/{ruleId}/')

    def delete_project_metric_alert(self, project, ruleId):
        """Delete an alert for a Sentry project"""

        return self._delete_api(f'/api/0/projects/{self.org}/{project}/alert-rules/{ruleId}/')

    def get_teams(self):
        """Return a dictionary mapping team slugs to a set of project slugs"""

        return self._get_api_pagination(f'/api/0/organizations/{self.org}/teams/')


if __name__ == '__main__':
    onpremise_token = os.environ['SENTRY_ONPREMISE_AUTH_TOKEN']
    cloud_token = os.environ['SENTRY_CLOUD_AUTH_TOKEN']


    # copy over onpremise url (e.g. http://sentry.yourcompany.com)
    sentry_onpremise = Sentry('<ON_PREMISE_URL>',
                              '<ON_PREMISE_ORG_SLUG>',
                              onpremise_token)

    sentry_cloud = Sentry('https://sentry.io',
                          '<ORG_SLUG>',
                          cloud_token)

    onpremise_projects = sentry_onpremise.get_project_slugs()
    onpremise_teams = sentry_onpremise.get_teams()

    # Map team ids from on-prem to cloud so we can correctly create alerts for the 
    # right team in cloud
    onprem_id_slugname = {team['slug']: team['id'] for team in onpremise_teams}

    #grab team id and team slug name from cloud and add it to another dictionary
    cloud_teams = sentry_cloud.get_teams()
    cloud_id_slugname = {team['slug']: team['id'] for team in cloud_teams}

    #dictionary to hold updated team ids, it will essentially be a mapping of
    # onprem team ids to their equivalent cloud ids
    dictionary_with_updatedvalues = {}

    #create dictionary mapping described above bere
    for key in onprem_id_slugname:
        dictionary_with_updatedvalues.update({onprem_id_slugname[key]: cloud_id_slugname[key]})


    #begin iterating through on-prem projects to gather alerts to send to SaaS Sentry
    for project in onpremise_projects:

        # for each project grab alerts from on-premise and cloud Sentry
        alerts = sentry_onpremise.get_project_alerts(project)

        cloudalerts = sentry_cloud.get_project_alerts(project)

        # iterate through alerts from on-prem account per project
        # and make sure to remove the alert that exists in the SaaS
        # project and send the alert in there
        for alert in alerts:
            #update the team id on the alert
            
            # the below is to strip the teamid value that will be replaced with the 
            # teamid of the ids on SaaS Sentry
            teamid = alert["owner"][5:]
            teamid = dictionary_with_updatedvalues[teamid]
            alert["owner"] = "team:" + str(teamid)

            #to be used for modifying the alert 
            modify = 0
            cloud_alert_to_modify = alert
            alertID = alert["id"]

            #iterate through all SaaS Sentry alerts to see if the on-prem Sentry
            #alert already exists, if it does, modify it but don't create new alert
            for cloudalert in cloudalerts:
                if (cloudalert['name'] == alert['name']):
                    if "triggers" not in cloudalert:
                        modify = 1
                        #make sure alerts JSON has environment tag set and Slack workspace set
                        cloudalert["environment"] = alert["environment"]
                        #merge Sentry local actions with Sentry Cloud actions
                        if (alert["actions"]!=[]):
                            for index in range(len(alert["actions"])):
                                #check for Slack integration, only update Workspace id
                                if alert["actions"][index]["id"] == "sentry.integrations.slack.notify_action.SlackNotifyServiceAction":
                                    for cloudindex in range(len(cloudalert["actions"])):
                                        if cloudalert["actions"][cloudindex]["id"] == "sentry.integrations.slack.notify_action.SlackNotifyServiceAction":
                                            #replace workspace number and channel_id here
                                            cloudalert["actions"][cloudindex]["workspace"] = ""
                        cloud_alert_to_modify = cloudalert
                        alertID = cloud_alert_to_modify["id"]

                        #Can delete the alert with the two options below
                        #1.  sentry_cloud.delete_project_metric_alert(project, cloudalert["id"])
                        #2.  sentry_cloud.delete_project_issue_alert(project, cloudalert["id"])

            #format the alert, if this is not done, you will get a 500 error back from
            #Sentry
            if (modify != 1):
                temp_alert = alert
                temp_alert.pop('id', None)
                temp_alert.pop('dateCreated', None)
                temp_alert.pop('createdBy', None)
                temp_alert.pop('projects', None)
                temp_alert.pop('type', None)
                temp_alert.pop('dateModified', None)
                if "triggers" in temp_alert:
                    for value in temp_alert["triggers"]:
                        del value["dateCreated"]
                        del value["id"]
                        del value["alertRuleId"]
                        for index in range(len(value["actions"])):
                            del value["actions"][index]["id"]
                            del value["actions"][index]["alertRuleTriggerId"]
                            del value["actions"][index]["dateCreated"]
                            #update team ids for the actions
                            if value["actions"][index]["targetType"] == "team":
                                value["actions"][index]["targetIdentifier"]=dictionary_with_updatedvalues[value["actions"][index]["targetIdentifier"]]
                temp_alert = json.dumps(temp_alert).replace('None', 'null')
            else:
                temp_alert = cloud_alert_to_modify
                temp_alert.pop('type', None)
                temp_alert = json.dumps(temp_alert).replace('None', 'null')

            #check if the alert is a metric alert or issue alert and
            # create/update the proper alert, updating metric alerts not supported yet
            if "triggers" in temp_alert:
                if modify != 1:
                    sentry_cloud.create_project_metric_alert(project, temp_alert)

            else:
                if modify == 1:
                    sentry_cloud.update_project_issue_alert(project, alertID, temp_alert)
                else:
                    sentry_cloud.create_project_issue_alert(project, temp_alert)



