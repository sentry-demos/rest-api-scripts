#!/usr/bin/env python

import os
import sys

import requests


class Sentry():
    def __init__(self, base_url, org, token):
        self.base_url = base_url
        self.org = org
        self.token = token

    def _get_api(self, endpoint):
        """HTTP GET the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, headers=headers)
        return response.json()

    def _post_api(self, endpoint, data=None):
        """HTTP POST the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
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
    
    def create_project_alert(self, project, data=None):
        """Create an alert for a Sentry project"""

        self._post_api(f'/api/0/projects/{self.org}/{project}/rules/', data=data)

    def get_project_alerts(self, project):
        """Return a list of alerts for Sentry project"""

        return self._get_api(f'/api/0/organizations/{self.org}/{project}/rules')

    def delete_project_alert(self, project, ruleId):
        """Delete an alert for a Sentry project"""

        return self._delete_api(f'/api/0/projects/{self.org}/{project}/rules/{ruleId}')


    def get_keys(self, project_slug):
        """return the public and secret DSN links for the given project slug"""

        results = self._get_api(f'/api/0/projects/{self.org}/{project_slug}/keys/')

        return (results[0]['dsn']['public'], results[0]['dsn']['secret'])


if __name__ == '__main__':
    onpremise_token = os.environ['SENTRY_ONPREMISE_AUTH_TOKEN']
    cloud_token = os.environ['SENTRY_CLOUD_AUTH_TOKEN']


    # copy over onpremise url (e.g. http://sentry.yourcompany.com)
    sentry_onpremise = Sentry('https://sentry.io',
                              '<ON_PREMISE_ORG_SLUG>',
                              onpremise_token)

    sentry_cloud = Sentry('https://sentry.io',
                          '<ORG_SLUG>',
                          cloud_token)

    onpremise_projects = sentry_onpremise.get_project_slugs()

    for project in onpremise_projects:

        # for each project grab alerts
        alerts = sentry_onpremise.get_project_alerts(project)



        # iterate through alerts from on-prem account per project
        # and make sure to remove the alert that exists in the SaaS
        # project and send the alert in there

        for alert in alerts:
            #delete the alert
            sentry_cloud.delete_project_alert(project, alert["id"])
            #create the alert
            sentry_cloud.create_project_alert(project, alert)


