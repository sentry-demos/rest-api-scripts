#!/usr/bin/env python

import os
import sys
import requests
import json


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

    def _post_api(self, endpoint, data=None):
        """HTTP POST the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'

        return requests.post(url, headers=headers, data=data)

    def _patch_api(self, endpoint, data=None):
        """HTTP PATCH the Sentry API"""

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': f'application/json'
        }
        url = f'{self.base_url}{endpoint}'
        print("URL", url)
        print("data", data)
        print("headers", headers)
        return requests.patch(url, headers=headers, json=data)
        p

    def get_project_slugs(self):
        """Return a list of project slugs in this Sentry org"""

        results = self._get_api(f'/api/0/organizations/{self.org}/projects/')

        return [project.get('slug', '') for project in results]

    def get_keys(self, project_slug):
        """return the public and secret DSN links for the given project slug"""

        results = self._get_api(f'/api/0/projects/{self.org}/{project_slug}/keys/')

        return (results[0]['dsn']['public'], results[0]['dsn']['secret'])

    def get_teams(self):
        """Return a dictionary mapping team slugs to a set of project slugs"""

        results = self._get_api(f'/api/0/organizations/{self.org}/teams/')

        #return {team['id']: team for team in results if 'id' in team}
        return {(team['slug'], team['id']): team for team in results if ('id' in team, 'slug' in team)}

    def get_team_members(self, teamId):
        """Return a dictionary mapping team slugs to member ids"""

        team = self._get_api(f'/api/0/organizations/{self.org}/scim/v2/Groups/' + teamId)

        return team

    def create_team(self, name, slug):
        """Create a new team in this Sentry org with the given name and slug"""

        return self._post_api(f'/api/0/organizations/{self.org}/teams/', data={'name': name, 'slug': slug})

    def give_team_access_to_project(self, team, project):
        """Give a team access to a project"""

        return self._post_api(f'/api/0/projects/{self.org}/{project}/teams/{team}/')

    def update_team(self, members, teamId):
        """Update team attributes"""
        return self._patch_api(f'/api/0/organizations/{self.org}/scim/v2/Groups/' + teamId, data=
        {
            "schemas": [
            "urn:ietf:params:scim:api:messages:2.0:PatchOp"
            ],
            "Operations": [
            {
                "op": "replace",
                "path": "members",
                "value": [
                    {
                        "display": "email",
                        "value": somevalue
                    }
                ]
            }
            ]
        }
        )

def get_team_projects(teams):
    mapping = {}
    for slug, team in teams.items():
        mapping[slug] = {project['slug'] for project in team.get('projects', []) if 'slug' in project}

    return mapping


if __name__ == '__main__':
    onpremise_token = os.environ['SENTRY_ONPREMISE_AUTH_TOKEN']
    cloud_token = os.environ['SENTRY_CLOUD_AUTH_TOKEN']

    onpremise_SCIMToken = os.environ['SENTRY_ONPREMISE_SCIM_AUTH_TOKEN']
    cloud_SCIMToken = os.environ['SENTRY_CLOUD_SCIM_AUTH_TOKEN']

    # copy over onpremise url (e.g. http://sentry.yourcompany.com)
    sentry_onpremise = Sentry('https://sentry.io',
                              <ONPremiseOrg>,
                              onpremise_token)

    sentry_cloud = Sentry('https://sentry.io',
                          <SentryCloudOrg>,
                          cloud_token)

    onpremise_SCIM = Sentry('https://sentry.io',
                              <ONPremiseOrg>,
                               onpremise_SCIMToken)

    cloud_SCIM = Sentry('https://sentry.io',
                          <SentryCloudOrg>,
                          cloud_SCIMToken)

    onpremise_teams_ids = sentry_onpremise.get_teams()
    cloud_teams_ids = sentry_cloud.get_teams()

    # Teams exist in both spots, team names are assumed they exist in both spots but
    # ids will be different, as a result, team name must be used because
    # that's whats in common

    for team in onpremise_teams_ids.keys():
        members = onpremise_SCIM.get_team_members(team[1]).get("members")
        #replace the team in the new org with all team member info on old org

        #matching team in cloud sentry
        for cloudTeam in cloud_teams_ids:
            #there is a match on team name but ids will be different
            if (cloudTeam[0] == team[0]):
                print(cloud_SCIM.update_team(members, cloudTeam[1]))
                break

