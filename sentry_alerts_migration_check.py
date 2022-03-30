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

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api(f'/api/0/organizations/{self.org}/projects/')
        return [project.get('slug', '') for project in results]
    

    def get_project_alerts(self, project):
        """Return a list of alerts for Sentry project"""

        return self._get_api(f'/api/0/projects/{self.org}/{project}/combined-rules/')

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

    #grab teams on Sentry SaaS
    cloud_teams = sentry_cloud.get_teams()

    #count of metric alerts in on-prem
    countofmetricalerts = 0

    #count of metric alerts in cloud
    countofmetricalertscloud = 0


    #begin iterating through on-prem projects to gather alerts to send to SaaS Sentry
    for project in onpremise_projects:

        # for each project grab alerts from on-premise and cloud Sentry
        alerts = sentry_onpremise.get_project_alerts(project)

        cloudalerts = sentry_cloud.get_project_alerts(project)

        # iterate through alerts from on-prem account per project
        # and make sure to count it
        for alert in alerts:
            if ("triggers" in alert):
                countofmetricalerts += 1

            #iterate through all SaaS Sentry alerts to see if the on-prem Sentry
            #alert already exists, if it does, count it
            for cloudalert in cloudalerts:
                if (cloudalert['name'] == alert['name'] and "triggers" in cloudalert):
                    countofmetricalertscloud += 1
                    

    #compare on-prem alerts with cloud alerts
    if (countofmetricalerts == countofmetricalertscloud):
        print("Successful migration")
    else:
        print("Migration was not successful") 
            



