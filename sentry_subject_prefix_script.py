#!/usr/bin/env python

import os
import sys
import requests


class Sentry():
    def __init__(self, base_url, org, token):
        self.base_url = base_url
        self.org = org
        self.token = token

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

    def _get_api(self, endpoint):
        """HTTP GET the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, headers=headers)
        return response.json()

    def _put_api(self, endpoint, data=None):
        """HTTP PUT the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'
        return requests.put(url, headers=headers, data=data)

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api_pagination(f'/api/0/organizations/{self.org}/projects/')
        return [project.get('slug', '') for project in results]

    def get_project_details(self, project_slug):
        """Get project details"""
        results = self._get_api(f'/api/0/projects/{self.org}/{project_slug}/')
        return results

    def update_project_details(self, project_slug, prefixdata):
        """Update project details"""
        return self._put_api(f'/api/0/projects/{self.org}/{project_slug}/', data={'subjectPrefix': prefixdata})

if __name__ == '__main__':
    onpremise_token = os.environ['SENTRY_ONPREMISE_AUTH_TOKEN']
    cloud_token = os.environ['SENTRY_CLOUD_AUTH_TOKEN']

    # copy over onpremise url (e.g. http://sentry.yourcompany.com)
    sentry_onpremise = Sentry('<ON_PREMISE_URL>',
                              '<ORG_SLUG>',
                              onpremise_token)
    sentry_cloud = Sentry('https://sentry.io',
                          '<ORG_SLUG>',
                          cloud_token)

    onpremise_projects = sentry_onpremise.get_project_slugs()
    for project in onpremise_projects:
        onpremise_project_details = sentry_onpremise.get_project_details(project)

        #get onpremise subjectPrefix
        subject_prefix = onpremise_project_details.get('subjectPrefix', '')

        #update new project with subjectPrefix if it was set in on-premise-project
        if subject_prefix:
            result = sentry_cloud.update_project_details(project, subject_prefix)


