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

        return results

    def _post_api(self, endpoint, data=None):
        """HTTP POST the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'

        return requests.post(url, headers=headers, data=data)

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api_pagination(f'/api/0/organizations/{self.org}/projects/')

        return [project.get('slug', '') for project in results]

    def get_keys(self, project_slug):
        """return the public and secret DSN links for the given project slug"""

        results = self._get_api_pagination(f'/api/0/projects/{self.org}/{project_slug}/keys/')

        return (results[0]['dsn']['public'], results[0]['dsn']['secret'])

    def get_teams(self):
        """Return team slug names"""

        results = self._get_api_pagination(f'/api/0/organizations/{self.org}/teams/')

        return {team['slug']: team for team in results if 'slug' in team}

    def create_team(self, name, slug):
        """Create a new team in this Sentry org with the given name and slug"""

        return self._post_api(f'/api/0/organizations/{self.org}/teams/', data={'name': name, 'slug': slug})

    def give_team_access_to_project(self, team, project):
        """Give a team access to a project"""

        return self._post_api(f'/api/0/projects/{self.org}/{project}/teams/{team}/')


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

    onpremise_teams = sentry_onpremise.get_teams()
    cloud_teams = sentry_cloud.get_teams()

    onpremise_projects = get_team_projects(onpremise_teams)
    cloud_projects = get_team_projects(cloud_teams)

    # If a team is in onpremise, but not cloud, it should be added to cloud
    missing_teams = onpremise_teams.keys() - cloud_teams.keys()
    for team in missing_teams:
        print(f'Creating mising team {team}: ')
        sentry_cloud.create_team(onpremise_teams[team]['name'], onpremise_teams[team]['slug'])
        cloud_projects[team] = set()

    # If a team exists in both, grant any missing project access in cloud
    common_teams = onpremise_projects.keys() & cloud_projects.keys()
    for team in common_teams:
        missing_projects = onpremise_projects[team] - cloud_projects[team]
        for project in missing_projects:
            print(f'Granting team {team} missing access to project {project}: ')
            sentry_cloud.give_team_access_to_project(team, project)
