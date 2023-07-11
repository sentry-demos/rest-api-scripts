from request import request
from processor import normalize_issue
from logger import customLogger
from sentry import Sentry
from sentry import utils
import dryable
import members
import sys
import uuid
import json
import csv
import os, sys

class Main:

    def init(self):
        try:
            
            self.logger = customLogger.Logger()
            self.sentry = Sentry.Sentry()
            self.memberObj = members.Members()
            self.migration_id = uuid.uuid4()

            cli_args = utils.process_cli_args(sys.argv, self.logger)

            if cli_args == False:
                return

            self.dry_run = "--dry-run" in cli_args
            dryable.set(self.dry_run)

            if self.dry_run:
                self.logger.debug('Running in dry-mode')
            
            self.memberObj.populate_members(self.sentry.get_org_members())
            self.memberObj.populate_teams(self.sentry.get_org_teams())

            filters = utils.get_request_filters(sys.argv, self.logger)
            if filters is None:
                raise Exception("Invalid CLI arguments")

            issues = self.sentry.get_issues_to_migrate(filters)
            if issues is None or len(issues) == 0:
                raise Exception("Issues list is empty")
            
            self.logger.debug(f'Ready to migrate {len(issues)} issues from {self.sentry.get_on_prem_project_name()} to {self.sentry.get_sass_project_name()}')
            metadata = self.create_issues_on_sass(issues)
            if metadata is not None:
                if self.dry_run:
                    self.print_issue_data(metadata)
                else:
                    self.update_issues(metadata)
                
                    discover_query = self.sentry.build_discover_query(self.migration_id)
                    self.logger.debug(f'Issues migrated discover query {discover_query}')

        except Exception as e:
            self.logger.critical(str(e))

    def update_issues(self, metadata):
        event_ids = [data["event_id"] for data in metadata]
        response = self.sentry.get_issue_ids_from_events(event_ids)
        if len(response["failed_event_ids"]) > 0:
            self.logger.warn(f'Could not find events with IDs {str(response["failed_event_ids"])} in {self.sentry.get_sass_project_name()} SaaS')
        
        if len(response["issues"]) == 0:
            self.logger.warn(f'Could not find new IDs in {self.sentry.get_sass_project_name()} SaaS')
        else:
            self.get_issue_metadata(response["issues"], metadata)

        if len(response["failed_event_ids"]) > 0:
            self.logger.debug(f'Retrying failed events {str(response["failed_event_ids"])}')
            response = self.sentry.get_issue_ids_from_failed_events(response["failed_event_ids"])
            if len(response["issues"]) == 0:
                self.logger.warn(f'Could not find new IDs in {self.sentry.get_sass_project_name()} SaaS')
                return
            else:
                self.get_issue_metadata(response["issues"], metadata)
    
    def get_issue_metadata(self, issues, metadata):
        for issue in issues:
            issue_id = issue["issue_id"]
            event_id = issue["event_id"]
            issue_metadata = utils.get_issue_attr(event_id, metadata, "issue_metadata")
            integration_data = utils.get_issue_attr(event_id, metadata, "integration_data")

            if issue_metadata is None:
                self.logger.warn(f'Could not update SaaS issue with ID {issue_id} (Issue created but not updated) - Skipping...')
                continue

            self.update_issue_metadata(issue_id, issue_metadata, integration_data)
    
    def update_issue_metadata(self, issue_id, issue_metadata, integration_data):
        response = self.sentry.update_issue(issue_id, issue_metadata)
        if response is not None and "id" in response:
            self.logger.info(f'SaaS Issue with ID {issue_id} metadata updated succesfully!')
        else:
            self.logger.error(f'SaaS Issue with ID {issue_id} metadata could not be updated')

        if integration_data["external_issue"] is not None:
            saas_integration_id = self.sentry.get_saas_integration_id("JIRA", {"key": "domainName", "value" : integration_data["domain_name"]})
            external_issues_response = self.sentry.update_external_issues(issue_id, integration_data, saas_integration_id)
            if external_issues_response is not None and "id" in external_issues_response and external_issues_response["id"] is not None:
                self.logger.info(f'SaaS Issue with ID {issue_id} external issues updated succesfully!')
            else:
                self.logger.error(f'SaaS Issue with ID {issue_id} external issues could not be updated')
        else:
            self.logger.debug(f'No external issues linked to Issue with ID {issue_id}')

    def create_issues_on_sass(self, issues):
        f = open('./output.json', "w")
        test_data = []
        metadata = []
        
        for index, issue in enumerate(issues):
            try:
                if issue["id"] is not None:
                    if "type" in issue and issue["type"] == "transaction":
                            continue
                        
                    self.logger.debug(f'Fetching data from issue with ID {issue["id"]} ({index+1}/{len(issues)})')

                    release = {}
                    if "firstRelease" in issue:
                        release["first"] = issue["firstRelease"]["version"] if "version" in issue["firstRelease"] else None
                    else:
                        releasesResponse = self.sentry.get_issue_releases(issue["id"])
                        if releasesResponse is not None and len(releasesResponse) != 0:
                            release["first"] = releasesResponse["firstRelease"]["shortVersion"]

                    # 2) Get the latest event for each of the issues
                    latest_event = self.sentry.get_latest_event_from_issue(issue["id"])

                    if "level" in issue:
                        issueData = {
                            "level" : issue["level"] or "error",
                            "firstSeen" : issue["firstSeen"],
                            "lastSeen" : issue["lastSeen"],
                            "release" : release,
                            "id" : issue["id"],
                            "migration_id" : str(self.migration_id)
                        }
                    else:
                        self.logger.warn("No level attribute found in issue data object")

                    # 3) Normalize and construct payload to send to SAAS
                    payload = normalize_issue(latest_event, issueData)
                    if ("error" in payload) or ("exception" in payload and payload["exception"] is None):
                        self.logger.error(payload["error"] if "error" in payload else f'Could not normalize issue payload with ID {issue["id"]} - Skipping...')
                        continue
                    
                    self.logger.info(f'Data normalized correctly for Issue with ID {issue["id"]}')

                    existingEvent = self.sentry.get_issue_by_id(issue["id"])
                    existingIssueID = None
                    if len(existingEvent["data"]) > 0:
                        existingId = existingEvent["data"][0]["id"]
                        issue_response = self.sentry.get_issue_id_from_event_id(existingId)
                        if "groupID" in issue_response:
                            existingIssueID = issue_response["groupID"]

                    else:
                        eventResponse = self.sentry.store_event(payload)

                        if not self.dry_run and (eventResponse is None or "id" not in eventResponse or eventResponse["id"] is None):
                            self.logger.error(f'Could not store new event in SaaS instance - Skipping...')
                            continue

                    issue_metadata = {}
                    integration_data = {}

                    if "firstSeen" in issue and issue["firstSeen"] is not None:
                        issue_metadata["firstSeen"] = issue["firstSeen"]
                    else:
                        self.logger.warn(f'firstSeen property could not be added to SaaS issue with ID {issue["id"]}')
                    
                    if "lastSeen" in issue and issue["lastSeen"] is not None:
                        issue_metadata["lastSeen"] = issue["lastSeen"]
                    else:
                        self.logger.warn(f'lastSeen property could not be added to SaaS issue with ID {issue["id"]}')
                    
                    if "assignedTo" in issue and issue["assignedTo"] is not None:
                        if issue["assignedTo"]["type"] == "team":
                            team_name = issue["assignedTo"]["name"]
                            team_id = self.memberObj.getTeamID(team_name)
                            if team_id is not None:
                                issue_metadata["assignedBy"] = "assignee_selector"
                                issue_metadata["assignedTo"] = "team:" + team_id
                        elif issue["assignedTo"]["type"] == "user":
                            if "email" not in issue["assignedTo"] or issue["assignedTo"]["email"] is None:
                                self.logger.warn(f'Issue assignee\'s email from on-prem issue with ID {issue["id"]} was not found')
                            else:
                                userEmail = issue["assignedTo"]["email"]
                                userId = self.memberObj.getUserID(userEmail)
                                if userId is not None:
                                    issue_metadata["assignedBy"] = "assignee_selector"
                                    issue_metadata["assignedTo"] = "user:" + userId
                                else:
                                    self.logger.warn(f'Could not find the ID of user with email {userEmail} - Skipping issue assignee')
                    else:
                        self.logger.warn(f'On-prem issue with ID {issue["id"]} does not contain property "assignedTo" - Skipping issue assignee')

                    integration_data = self.sentry.get_integration_data("JIRA", issue["id"])
                    
                    obj = {
                        "issue" : issue,
                        "event" : latest_event,
                        "integration_data": integration_data["raw_data"]
                    }
                    test_data.append(obj)

                    integration_data = integration_data["keys"]

                    if existingIssueID is not None and not self.dry_run:
                        self.logger.debug(f'Issue already created in SaaS instance with ID {existingIssueID} - Only updating issue with metadata')
                        self.update_issue_metadata(existingIssueID, issue_metadata, integration_data)
                        continue

                    if self.dry_run:
                        obj = {
                            "issue_skeleton" : payload,
                            "issue_metadata" : issue_metadata,
                            "integration_data" : integration_data
                        }
                        metadata.append(obj)
                    else:
                        self.logger.info(f'Issue successfully created in SaaS instance with ID {eventResponse["id"]}')
                        obj = {
                            "event_id" : eventResponse["id"],
                            "issue_metadata" : issue_metadata,
                            "integration_data" : integration_data
                        }
                        metadata.append(obj)

                    f.close()
                    f = open('./output.json', "w")
                    f.write(json.dumps(test_data))
                    

                else:
                    raise Exception("Issue ID not found")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)

        #f.write(json.dumps(test_data))
        return metadata

    def print_issue_data(self, data):
        self.logger.debug(data, True)

if __name__ == "__main__":
    main = Main()
    main.init()