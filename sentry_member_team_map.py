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
        return requests.patch(url, headers=headers, json=data)

    def get_teams(self):
        """Return a dictionary mapping team slugs to a set of project slugs"""

        results = self._get_api(f'/api/0/organizations/{self.org}/scim/v2/Groups')
        return results.get("Resources")

    def get_team_members(self, teamId):
        """Return a dictionary mapping team slugs to member ids"""

        team = self._get_api(f'/api/0/organizations/{self.org}/scim/v2/Groups/' + teamId)

        return team

    def get_org_members(self):
        """Get members from an organization"""

        members = self._get_api(f'/api/0/organizations/{self.org}/scim/v2/Users')
        return members.get("Resources")

    def create_team_member(self, data):
        """Create team member"""
        teammember = self._post_api(f'/api/0/organizations/{self.org}/scim/v2/Users', json.dumps(data))
        return teammember.__dict__

    def update_team(self, members, teamId):
        """Update team attributes"""
        return self._patch_api(f'/api/0/organizations/{self.org}/scim/v2/Groups/' + teamId, data=
        {   "schemas": [
                "urn:ietf:params:scim:api:messages:2.0:PatchOp"
                    ],
            "Operations": [
              {
                "op": "replace",
                "path": "members",
                "value": members
              }
            ]
        }
    )


if __name__ == '__main__':

    onpremise_SCIMToken = os.environ['SENTRY_ONPREMISE_SCIM_AUTH_TOKEN']
    cloud_SCIMToken = os.environ['SENTRY_CLOUD_SCIM_AUTH_TOKEN']

    # copy over onpremise url (e.g. http://sentry.yourcompany.com)
    onpremise_SCIM = Sentry('<ON_PREMISE_URL>',
                            '<ON_PREMISE_ORG_SLUG>',
                            onpremise_SCIMToken)

    cloud_SCIM = Sentry('https://sentry.io',
                        '<ORG_SLUG>',
                        cloud_SCIMToken)

    onpremise_teams = onpremise_SCIM.get_teams()
    cloud_teams = cloud_SCIM.get_teams()
    updated_ids_dict = {}

    #To be used for ID swap for easier lookup later
    onpremmembers = onpremise_SCIM.get_org_members()
    cloudmembers = cloud_SCIM.get_org_members()
    

    #get id of old account and store it along with email in a common dictionary

    for member in onpremmembers:
        found = 0
        for cloudmember in cloudmembers:
              if ((member.get('emails')[0].get('value')) == 
                (cloudmember.get('emails')[0].get('value'))):
                    member['id'] = cloudmember.get('id')
                    updated_ids_dict[member.get('emails')[0].get('value')] = cloudmember.get('id')
                    found=1
                    break

        #Make a new user if not found in new org, email must match what is on Okta
        if (found == 0):

            #Create new user
            data = {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                "userName": "",
                "name": {"givenName": "", "familyName": ""},
                "emails": [{"primary": True, "value": "", "type": "work"}],
                "active": True,
            }
            data["userName"] = member.get('emails')[0].get('value');
            data.get("emails")[0]["value"] = member.get('emails')[0].get('value');
            newuser = cloud_SCIM.create_team_member(data)
            
            #get id of new user
            newuser_id = newuser.get("id")

            #update id in onpremmembers array
            updated_ids_dict[member.get('emails')[0].get('value')] = newuser_id

    # By now, all onpremmembers should have updated ids for the new org,
    # this will enable easy dictionary lookup for ids

    # Teams exist in both spots, team names must exist in both spots but
    # ids will be different, as a result, team name must be used because
    # that's whats in common

    # if a team exists in old org but not in new org, nothing will happen
    for team in onpremise_teams:

        #update old team members with ids of new org member ids
        for member in team.get("members"):
            #update ids here
            member['value'] = updated_ids_dict.get(member.get('display'))

        #by now all onpremise team members have updated ids

        #matching onprem team with updated ids to cloud sentry
        for cloudTeam in cloud_teams:

            #there is a match on team name, onprem teams will have updated ids from
            #cloud account
            if (cloudTeam['displayName'] == team['displayName']):
                cloud_SCIM.update_team(team.get("members"), cloudTeam['id'])



