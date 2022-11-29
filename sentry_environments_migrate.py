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

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api(f'/api/0/organizations/{self.org}/projects/')
        print("RESULTS ", results)
        return [project.get('slug', '') for project in results]

    def get_keys(self, project_slug):
        """return the public and secret DSN links for the given project slug"""

        results = self._get_api(f'/api/0/projects/{self.org}/{project_slug}/keys/')

        return (results[0]['dsn']['public'], results[0]['dsn']['secret'])

    def get_project_environments(self, project):
        """Get environments for a project"""

        return self._get_api(f'/api/0/projects/{self.org}/{project}/environments/')


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

    for project in onpremise_projects:

        # for each project grab environments
        environments = sentry_onpremise.get_project_environments(project)

        #grab project DSN
        keys = sentry_onpremise.get_keys(project)

        #grab the environments from the SaaS Sentry account
        cloud_environments = sentry_cloud.get_project_environments(project)

        common_environments = []
        if (cloud_environments != []):
            for environment in environments:
                #if environment already exists in cloud, skip
                for cenvironment in cloud_environments:
                    if (environment["name"] == cenvironment["name"]):
                        break
                    else:
                        common_environments.append(environment)
        else:
            common_environments = environments

        #update DSN with Sentry SaaS project DSN
        keys = sentry_cloud.get_keys(project)
        os.environ["SENTRY_DSN"]=keys[0]

        # iterate through environments from on-prem account
        for environment in common_environments:
            #update Sentry SaaS projects with environment only if the environment
            #is missing from the Sentry SaaS project
            os.system('sentry-cli send-event --env ' + environment['name'] + ' -m "setting up environment %s" -a ' + environment['name'])

