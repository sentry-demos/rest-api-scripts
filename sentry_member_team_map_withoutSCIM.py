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

    def _post_api(self, endpoint, data=None):
        """HTTP POST the Sentry API"""

        headers = {'Authorization': f'Bearer {self.token}'}
        url = f'{self.base_url}{endpoint}'
        return requests.post(url, headers=headers, data=data)

    def get_teams(self):
        """Return a dictionary mapping team slugs to a set of project slugs"""

        results = self._get_api_pagination(f'/api/0/organizations/{self.org}/teams/')
        return {team['slug']: team for team in results if 'slug' in team}

    def get_teams_members_reg(self, teamname):
        """Return a dictionary mapping team slugs to a set of project slugs"""

        results = self._get_api_pagination(f'/api/0/teams/{self.org}/{teamname}/members/')
        return results

    def get_org_members(self):
        """Get members from an organization"""

        members = self._get_api_pagination(f'/api/0/organizations/{self.org}/members/')
        return members

    def create_team_member(self, data=None):
        """Create team member"""

        teammember = self._post_api(f'/api/0/organizations/{self.org}/members/', data)
        return teammember.json()

    def update_team_reg(self, memberid, teamname):
        """Update team attributes"""

        result = self._post_api(f'/api/0/organizations/{self.org}/members/{memberid}/teams/{teamname}/')
        return result



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

    updated_ids_dict = {}

    #To be used for ID swap for easier lookup later
    onprem_members = sentry_onpremise.get_org_members()
    cloud_members = sentry_cloud.get_org_members()

    #get id of old account and store it along with email in a common dictionary, i.e. updated_ids_dict

    for member in onprem_members:
        found = 0
        for cloudmember in cloud_members:
              if (member.get('email') ==
                (cloudmember.get('email'))):
                    member['id'] = cloudmember.get('id')
                    #update id in common dictionary
                    updated_ids_dict[member.get('email')] = cloudmember.get('id')
                    found = 1
                    break

        #Make a new user if not found in new org, email must match what is on Okta
        if (found == 0):

            #Create new user
            data = {
                "email": "",
                "role": "member"
            }
            data["userName"] = member.get('email');
            data['email'] = member.get('email');
            newuser = sentry_cloud.create_team_member(data)
            
            #get id of new user
            newuser_id = newuser.get("id")
            
            #update id in common dictionary
            updated_ids_dict[member['email']] = newuser_id

    # By now, all onprem_members should have updated ids for the new org,
    # this should be stored in the new dictionary
    # this will enable easy dictionary lookup for ids

    # Teams exist in both spots, team names must exist in both spots but
    # ids will be different, as a result, team name must be used because
    # that's whats in common

    for team in onpremise_teams:
        #update old team members with ids of new org member ids
        for member in sentry_onpremise.get_teams_members_reg(team):
            #update member id here
            member['id'] = updated_ids_dict.get(member.get("email"))

            #onpremise team member for selected team has updated id


            #update cloud team with member from on_prem team
            sentry_cloud.update_team_reg(member['id'], team)



