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
                'Content-Type': 'application/json',}
        url = f'{self.base_url}{endpoint}'
        return requests.put(url, headers=headers, data=data)

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api(f'/api/0/organizations/{self.org}/projects/')
        return [project.get('slug', '') for project in results]
    

    def set_project_rate_limits(self, project, keyId, data=None):
        """Set a Sentry project limit"""

        return self._put_api(f'/api/0/projects/{self.org}/{project}/keys/{keyId}/', data=data)

    def get_keys(self, project_slug):
        """return all the keys for the given project slug"""

        results = self._get_api(f'/api/0/projects/{self.org}/{project_slug}/keys/')

        return results

    def get_teams(self):
        """Return a dictionary mapping team slugs to a set of project slugs"""

        return self._get_api_pagination(f'/api/0/organizations/{self.org}/teams/')


if __name__ == '__main__':
    cloud_token = os.environ['SENTRY_CLOUD_AUTH_TOKEN']


    # copy over cloud url (e.g. http://sentry.yourcompany.com)
    sentry_cloud = Sentry('https://sentry.io',
                              'adamtestorg',
                              cloud_token)

    #grab project slugs
    cloud_projects = sentry_cloud.get_project_slugs()


    #begin iterating through projects to set DSN limits for SaaS Sentry
    for project in cloud_projects:


         # iterate through keys
        keys = sentry_cloud.get_keys(project)
        for key in keys:
            #strip out the key
            key = key['dsn']['public']
            key = key[8:40]


            #Set the DSN rate limit
            data = {
                    "rateLimit": {"count": 100, "window": 60}
                    }

            #for each project, set the DSN rate limit on
            #a per project level
            sentry_cloud.set_project_rate_limits(project, key, json.dumps(data))



        
