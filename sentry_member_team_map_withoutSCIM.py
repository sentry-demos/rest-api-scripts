#!/usr/bin/env python

import os
import sys
import requests
import json
import logging

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

    def update_team_reg(self, memberid, teamname, member_email):
        """Update team attributes"""

        result = self._post_api(f'/api/0/organizations/{self.org}/members/{memberid}/teams/{teamname}/')
        if result.status_code in [201,204]:
            logger.info("Team '%s' has assigned cloud member '%s'" % (team,member_email))
            return result
        else:
            logger.warning(f'\n[WARN] Could not assign member {member_email} to team {teamname}. Status code {result.status_code}\n')

def prompt_user_to_confirm_dry_run_mode(is_dryrun_mode, action_to_take):
    print("\n")
    if is_dryrun_mode:
        print(f'Running in DRYRUN MODE. About to {action_to_take}.')
    else:
        print(f'Running for real (not dry run mode). About to {action_to_take}. This will cause database changes to be made to SaaS.')

    selection = input(f"Continue? y/n:\n")
    if selection != "y":
        print("'y' not selected. Exiting program.")
        sys.exit()
    else:
        print("\n")


if __name__ == '__main__':
    
    logging.basicConfig(filename=os.path.basename(__file__)+'.log', 
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
        datefmt='%Y-%m-%d:%H:%M:%S', level=logging.DEBUG, filemode='a')
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    logger.info(">>> Script started")
    onpremise_token = os.environ['SENTRY_ONPREMISE_AUTH_TOKEN']
    onpremise_url = os.environ['ON_PREMISE_URL']
    onpremise_slug = os.environ['ON_PREMISE_ORG_SLUG']
    cloud_token = os.environ['SENTRY_CLOUD_AUTH_TOKEN']
    cloud_slug = os.environ['ORG_SLUG']
    # dryrun_member_creation = True #change to false when ready to create members in SaaS for real
    dryrun_associate_members_teams = True #change to false when ready to associate members/teams in SaaS for real

    if dryrun_associate_members_teams:
        logger.info("=========================\nRunning in DRY RUN MODE\n=========================")
    else:
        logger.info("=========================\nRunning for real\n=========================")

    # prompt_user_to_confirm_dry_run_mode(dryrun_member_creation, "Recreate on-premise members in SaaS")

    onpremise_url = onpremise_url.strip("/"); #removes trailing slash '/' of the URL if needed

    # copy over onpremise url (e.g. http://sentry.yourcompany.com)
    sentry_onpremise = Sentry(onpremise_url,
                              onpremise_slug,
                              onpremise_token)

    sentry_cloud = Sentry('https://sentry.io',
                              cloud_slug,
                              cloud_token)

    onpremise_teams = sentry_onpremise.get_teams()
    cloud_teams = sentry_cloud.get_teams()
    logger.info("Get on-prem teams completed.")
    updated_ids_dict = {}

    #To be used for ID swap for easier lookup later
    onpremise_members = sentry_onpremise.get_org_members()
    logger.info("Get on-prem members completed.")
    cloud_members = sentry_cloud.get_org_members()
    logger.info("Get cloud members completed.")

    #get id of old account and store it along with email in a common dictionary, i.e. updated_ids_dict
    logger.info("\n================================================")
    logger.info("...Checking for duplicate users in cloud/on-prem. These users may need to be added via Sentry UI...\n")
    for member in onpremise_members:
        found = 0
        # Check if any onpremise members already exist as cloud members
        for cloudmember in cloud_members:
            if (member.get('email') == (cloudmember.get('email'))):
                member['id'] = cloudmember.get('id')
                #update id in common dictionary to use pre-existing cloud member's id
                updated_ids_dict[member.get('email')] = cloudmember.get('id')
                found = 1
                # logger.info("Member already exists in cloud: %s" % (member.get('email')))
                break

        # Make a new user if not found in cloud, email must match what is on Okta
        if (found == 0):
            role = member.get('role')
            #Create new user
            data = {
                "email": "",
                "role": role
            }
            data["userName"] = member.get('email')
            data['email'] = member.get('email')
            
            logger.info(f'[INFO] - onprem user "{data["userName"]}" ("{data["role"]}" role) does not exist in cloud')

            # Member creation via API is not permitted at this time; commenting out.
            # if dryrun_member_creation:
            #     logger.info(f'DRYRUN MODE - would have created onprem user "{data["userName"]}" ("{data["role"]}" role) in cloud')
            # else:
                # newuser = sentry_cloud.create_team_member(data)
                # if "userName" in newuser:
                #     logger.info("Created new user (userName, role) in cloud: %s, %s" % (data["userName"], data['role']))
                # else:
                #     # this may actually be expected since I no longer see a documented endpoint for
                #     # creating new Sentry members via API
                #     logger.info(f'\n[ERROR] Could not create user - {data["userName"]} - {newuser}\n')

                # #get id of new user
                # newuser_id = newuser.get("id")
                
                # #update id in common dictionary
                # updated_ids_dict[member['email']] = newuser_id

    prompt_user_to_confirm_dry_run_mode(dryrun_associate_members_teams, "assign users to teams.\nNote: Users would be assigned to the same team names as they had from onprem. The teams must already exist on the cloud Sentry.")

    # By now, all onpremise_members should have updated ids for the new org,
    # this should be stored in the new dictionary
    # this will enable easy dictionary lookup for ids

    # Teams exist in both spots, team names must exist in both spots but
    # ids will be different, as a result, team name must be used because
    # that's whats in common
    # userInput = input("\nWould you like to assign cloud users to teams?\nNote: Users would be assigned to the same team names as they had from onprem. The teams must already exist on the cloud Sentry.\n(y/n): ")
    
    logger.info("\n================================================")
    logger.info("\n...Preparing to assign cloud members to teams...")

    # if userInput.lower() == "y":
    for team in onpremise_teams:
        logger.info("\n")
        #update old team members with ids of new org member ids
        for onprem_member in sentry_onpremise.get_teams_members_reg(team):
            #onpremise team member for selected team has updated id
            onprem_member['id'] = updated_ids_dict.get(onprem_member.get("email"))
            #update cloud team with member from on_prem team
            if team in cloud_teams:
                onprem_member_exists_in_cloud = True in (cloud_member['email'] == onprem_member['email'] for cloud_member in cloud_members)
                if dryrun_associate_members_teams:
                    if onprem_member_exists_in_cloud:
                        logger.info("DRY RUN: Team '%s' would add cloud member '%s'" % (team,onprem_member.get("email")))
                    else:
                        logger.info(f'[WARN] DRY RUN: Onprem user "{onprem_member["email"]}" on team "{team}" does not exist in cloud! Cannot add to cloud team {team}')
                else:
                    if onprem_member_exists_in_cloud:
                        # logger.info("Adding to Team %s - cloud member %s" % (team,onprem_member.get("email")))
                        sentry_cloud.update_team_reg(onprem_member['id'], team, onprem_member['email'])
                    else:
                        logger.warning(f'[WARN] ==========> onprem user "{onprem_member["email"]}" does not exist in cloud; could not add to team "{team}"!')
            else:
                logger.warning("[WARN] Team %s does not exist in cloud! Could not add member %s\n" % (team, onprem_member.get("email")))
    # else:
    #     logger.info("Skipped assigning cloud users to corresponding onprem teams")

    logger.info("\n<<< Script completed")
    print("\nScript completed. Log available in ./%s" % (os.path.basename(__file__)+'.log'))
