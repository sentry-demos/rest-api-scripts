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

    def _put_api(self, endpoint, data=None):
        """HTTP PUT the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'
        return requests.put(url, headers=headers, data=data)

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api(f'/api/0/organizations/{self.org}/projects/')
        return [project.get('slug', '') for project in results]

    def get_keys(self, project_slug):
        """return the public and secret DSN links for the given project slug"""

        results = self._get_api(f'/api/0/projects/{self.org}/{project_slug}/keys/')

        return (results[0]['dsn']['public'], results[0]['dsn']['secret'])

    def get_teams(self):
        """Return slug names for given teams"""

        results = self._get_api(f'/api/0/organizations/{self.org}/teams/')

        return {team['slug']: team for team in results if 'slug' in team}

    def create_team(self, name, slug):
        """Create a new team in this Sentry org with the given name and slug"""

        return self._post_api(f'/api/0/organizations/{self.org}/teams/', data={'name': name, 'slug': slug})

    def give_team_access_to_project(self, team, project):
        """Give a team access to a project"""

        return self._post_api(f'/api/0/projects/{self.org}/{project}/teams/{team}/')

    def get_project_settings(self, project):
        """Get project settings"""

        return self._get_api(f'/api/0/projects/{self.org}/{project}/')

    def set_project_platform(self, project, filtervalue):
        """Update project with platform value"""

        return self._put_api(f'/api/0/projects/{self.org}/{project}/', data={"platform": filtervalue})

def get_team_projects(teams):
    mapping = {}
    for slug, team in teams.items():
        mapping[slug] = {project['slug'] for project in team.get('projects', []) if 'slug' in project}

    return mapping


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

        # for each project grab platform type
        filters = sentry_onpremise.get_project_settings(project)

        #update Sentry SaaS platform type
        sentry_cloud.set_project_platform(project, filters.get('platform'))
