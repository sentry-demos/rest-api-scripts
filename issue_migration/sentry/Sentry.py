from dotenv import load_dotenv
from sentry import utils
from request import request
import dryable
import os
import time
from halo import Halo

class Sentry:

    def __init__(self):
        load_dotenv()
        self.request_timeout = 40
        attributes = utils.get_attributes_from_dsn(os.environ["SAAS_PROJECT_DSN"])
        self.saas_options = {
            "endpoint" : f'https://{attributes.group(2)}/api/',
            "url" : os.environ["SAAS_URL"],
            "auth_token" : os.environ["SAAS_AUTH_TOKEN"],
            "org_name" : os.environ["SAAS_ORG_NAME"],
            "project_name" : os.environ["SAAS_PROJECT_NAME"],
            "sentry_key" : attributes.group(1),
            "project_key" : attributes.group(3)
        }

        self.on_prem_options = {
            "auth_token" : os.environ["ON_PREM_AUTH_TOKEN"],
            "url" : os.environ["ON_PREM_URL"],
            "org_name" : os.environ["ON_PREM_ORG_NAME"],
            "project_name" : os.environ["ON_PREM_PROJECT_NAME"]
        }

    def get_sass_project_name(self):
        return self.saas_options["project_name"]

    def get_on_prem_project_name(self):
        return self.on_prem_options["project_name"]

    def get_org_members(self):
        url = f'{self.saas_options["url"]}organizations/{self.saas_options["org_name"]}/users/'
        response = request(url, method = "GET")
        members = []
        if response is not None and response.status_code == 200:
            members = members + response.json()
            next = response.links.get('next', {}).get('results') == 'true'
            while next:
                url = response.links.get('next', {}).get('url')
                response = self.make_issues_request(url)
                next = response.links.get('next', {}).get('results') == 'true'
                data = response.json()
                members = members + data

            return members
        
        print(response.json())

        raise Exception(f'Could not fetch {self.saas_options["org_name"]} members')

    def get_org_teams(self):
        url = f'{self.saas_options["url"]}organizations/{self.saas_options["org_name"]}/teams/'
        response = request(url, method = "GET")
        teams = []
        if response is not None and response.status_code == 200:
            teams = teams + response.json()
            next = response.links.get('next', {}).get('results') == 'true'
            while next:
                url = response.links.get('next', {}).get('url')
                response = self.make_issues_request(url)
                next = response.links.get('next', {}).get('results') == 'true'
                data = response.json()
                teams = teams + data

            return teams

        raise Exception(f'Could not fetch {self.saas_options["org_name"]} teams')

    def get_issues_to_migrate(self, filters):
       
        issues = []

        if "start" in filters:
            url = f'{self.on_prem_options["url"]}projects/{self.on_prem_options["org_name"]}/{self.on_prem_options["project_name"]}/issues/'
            response = self.make_issues_request(url)
            data = response.json()
            last_event_last_seen = utils.parse_string_date(data[-1]["lastSeen"])
            first_event_last_seen = utils.parse_string_date(data[0]["lastSeen"])
            not_in_range = filters["start"] < last_event_last_seen or filters["end"] > first_event_last_seen
            next = response.links.get('next', {}).get('results') == 'true'
            spinner = Halo(text="Loading", spinner="dots")

            if not_in_range == False or next == False:
                issues = data

            while not_in_range and next:
                spinner.start()
                next = response.links.get('next', {}).get('results') == 'true'
                if next:
                    url = response.links.get('next', {}).get('url')
                    response = self.make_issues_request(url)
                    data = response.json()
                    issues = issues + data
                    last_event_last_seen = utils.parse_string_date(data[-1]["lastSeen"])
                    first_event_last_seen = utils.parse_string_date(data[0]["lastSeen"])
                    not_in_range = filters["start"] < last_event_last_seen or filters["end"] > first_event_last_seen
            
            count = 0
            while filters["fetch_release"] and count < len(data):
                base_url = f'{self.on_prem_options["url"]}issues/{data[count]["id"]}/'
                response = self.make_issues_request(base_url)
                data[count] = response.json()
                count = count+1

            spinner.stop()

        elif "issues" in filters and filters["issues"] is not None:
            base_url = f'{self.on_prem_options["url"]}issues/'
            for id in filters["issues"]:
                url = base_url + f'{id}/'
                response = self.make_issues_request(url)
                data = response.json()
                issues.append(data)

        return utils.filter_issues(issues, filters)

    def make_issues_request(self, url):
        response = request(url, method = "GET")
        if response is not None and response.status_code == 200:
            return response

        print(response.json())
        raise Exception(f'Could not get issues from on-prem {self.on_prem_options["project_name"]}')
    
    def get_issue_by_id(self, issue_id):
        if id is not None:
            url = f'{self.saas_options["url"]}organizations/{self.saas_options["org_name"]}/events/?query=onprem_id:{issue_id}&field=id'
            response = request(url, method = "GET")
            if response is not None and response.status_code == 200:
                return response.json()

        raise Exception(f'Could not check if issue already exists with on prem id {issue_id}')

    def get_latest_event_from_issue(self, id):
        if id is not None:
            url = f'{self.on_prem_options["url"]}issues/{id}/events/latest/'
            response = request(url, method = "GET")
            if response is not None and response.status_code == 200:
                return response.json()
            else:
                print(response.json())

        raise Exception(f'Could not get latest event from on-prem {self.on_prem_options["org_name"]} with issue ID {id}')

    def get_issue_releases(self, id):
        if id is not None:
            url = f'{self.on_prem_options["url"]}issues/{id}/first-last-release/'
            response = request(url, method = "GET")
            if response is not None and response.status_code == 200:
                return response.json()
            elif response.status_code != 404:
                print(response.json())
        
        return None

    def get_issue_id_from_event_id(self, event_id):
        if id is not None:
            url = f'{self.saas_options["url"]}projects/{self.saas_options["org_name"]}/{self.saas_options["project_name"]}/events/{event_id}/'
            response = request(url, method = "GET")
            if response is not None and response.status_code == 200:
                return response.json()

        raise Exception(f'Could not get issue info from SaaS event with ID {event_id}')


    @dryable.Dryable()
    def store_event(self, event):
        store_url = f'{self.saas_options["endpoint"]}{self.saas_options["project_key"]}/store/?sentry_key={self.saas_options["sentry_key"]}'
        response = request(store_url, method = "POST", payload = event)
        if response is not None and response.status_code == 200:
            return response.json()
        else:
            print(response.json())

        return None

    def update_issue(self, issue_id, payload):
        url = f'{self.saas_options["url"]}issues/{issue_id}/'
        response = request(url = url, method = "PUT", payload = payload)
        if response is not None and response.status_code == 200:
            return response.json()
        else:
            print(response.json())
        
        return None
    
    def get_issue_ids_from_events(self, eventIDs):
        spinner = Halo(text="Loading", spinner="dots")
        spinner.start()
        time.sleep(10)
        failed_event_ids = []
        issues = []
        for eventID in eventIDs:
            url = f'{self.saas_options["url"]}projects/{self.saas_options["org_name"]}/{self.saas_options["project_name"]}/events/{eventID}/'
            response = request(url, method = "GET")
            start_time = time.time()
            if response is not None:
                data = response.json()
                while "id" not in data:
                    time_delta = time.time() - start_time
                    response = request(url, method = "GET")
                    data = response.json()

                    if time_delta > self.request_timeout:
                        print("Timeout reached")
                        failed_event_ids.append(eventID)
                        break

                if "groupID" in data:
                    issues.append({
                        "issue_id" : data["groupID"],
                        "event_id" : eventID
                    })
        spinner.stop()

        return {
            "issues" : issues,
            "failed_event_ids" : failed_event_ids
        }

    def get_issue_ids_from_failed_events(self, eventIDs):
        spinner = Halo(text="Loading", spinner="dots")
        spinner.start()
        url = f'{self.saas_options["url"]}projects/{self.saas_options["org_name"]}/{self.saas_options["project_name"]}/events/'
        response = request(url, method = "GET")
        events_metadata = []
        issues = []
        if response is not None:
            data = response.json()
            for event in data:
                obj = {
                    "event_id" : event["eventID"],
                    "issue_id" : event["groupID"]
                }
                events_metadata.append(obj)

        for eventID in eventIDs:
            issue_id = [obj['issue_id'] for obj in events_metadata if obj['event_id'] == eventID]
            next = response.links.get('next', {}).get('results') == 'true'
            while next and len(issue_id) == 0:
                url = response.links.get('next', {}).get('url')
                response = request(url, method = "GET")
                next = response.links.get('next', {}).get('results') == 'true'
                data = response.json()
                issue_id = [obj["groupID"] for obj in data if obj["eventID"] == eventID]

            if issue_id is not None:
                if len(issue_id) == 1:
                    issue_id = issue_id[0]
                obj = {
                    "issue_id" : issue_id,
                    "event_id" : eventID
                }
                issues.append(obj)

        return {
            "issues" : issues
        }

    def get_integration_data(self, integration_name, issue_id):
        url = f'{self.on_prem_options["url"]}groups/{issue_id}/integrations/'
        response = request(url, method = "GET")
        if response is not None and response.status_code == 200:
            return self.process_integrations_response(response.json(), integration_name)
        
        raise Exception(f'Could not fetch integrations for issue with ID {issue_id}')
    
    def process_integrations_response(self, integrations, integration_name):
        keys = {
            "domain_name" : None,
            "external_issue" : None
        }
        for integration in integrations:
            if "name" in integration and integration["name"].lower() == integration_name.lower():
                if len(integration["externalIssues"]) > 0:
                    keys["domain_name"] = integration["domainName"] or None
                    keys["external_issue"] = integration["externalIssues"][0]["key"] or None

        return { "keys": keys, "raw_data": integrations }

    def get_saas_integration_id(self, integration_name, identifer):
        url = f'{self.saas_options["url"]}organizations/{self.saas_options["org_name"]}/integrations/?includeConfig=0'
        response = request(url, method = "GET")
        if response is not None and response.status_code in [200,201]:
            data = response.json()
            for integration in data:
                if integration["name"].lower() == integration_name.lower() and integration[identifer["key"]] == identifer["value"]:
                    return integration["id"] or None

        raise Exception(f'Could not get integration id for {integration_name} in SaaS {self.saas_options["org_name"]}')

    def update_external_issues(self, issue_id, integration_data, integration_id):
        url = f'{self.saas_options["url"]}groups/{issue_id}/integrations/{integration_id}/'
        payload = {
            "externalIssue" : integration_data["external_issue"]
        }
        response = request(url, method = "PUT", payload = payload)
        if response is not None and response.status_code in [200,201]:
            return response.json()
        
        print(response.json())
        return None

    def build_discover_query(self, migration_id):
        url = f'https://{self.saas_options["org_name"]}.sentry.io/issues/?query=+migration_id%3A{migration_id}&referrer=issue-list&statsPeriod=90d'
        return url