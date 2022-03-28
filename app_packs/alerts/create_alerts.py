# TODO: some imports might be redundant 
import requests
import jsons
from xml.dom import minidom
import sys
# import getopt
import logging
from datetime import datetime
from pytz import timezone
import pytz
from pathlib import Path
import time
import json
from jproperties import Properties
from collections.abc import MutableMapping

alert_list = []
projects_dict = {}
headers = {}
configs = Properties()   
script_report = {}

# MAKE SURE YOU ADD AN ENTRY FOR "type": "issue" or "type": "metric".
# 
# TODO: Move JSON into individual files for each alert to make this more readable
ISSUE_ALERTS = {
    # Explaining the unintuitive first alert, An Unassigned Error is Occurring:
    # So if we have Issue A that was less than 7 days old and had a spike of 100 events/hr,
    # the above alert would be fired only once for an entire week.
    # After that 1 week is over, the issue is not classified as new anymore (Issue A's age > 7 days)
    # which results in only 1 single alert per issue.
    "An Unassigned Error Is Occurring": jsons.dumps({
        "actionMatch":"all",
        "filterMatch":"all",
        "actions":[],
        "conditions":[{
            "interval":"1h",
            "id":"sentry.rules.conditions.event_frequency.EventFrequencyCondition",
            "comparisonType":"count",
            "value":"100"
        }],
        "filters":[
            {
                "comparison_type":"newer",
                "time":"week",
                "id":"sentry.rules.filters.age_comparison.AgeComparisonFilter",
                "value":1,
                "name":"The issue is newer than 1 week"
            },
            {
                "targetType":"Unassigned",
                "id":"sentry.rules.filters.assigned_to.AssignedToFilter"
            }
        ],
        "frequency":"10080", #perform actions once weekly
        "type":"issue"
    }),
    "Regression Error Occurred": jsons.dumps({
      "actionMatch":"all",
      "filterMatch":"all",
      "actions":[],
      "conditions":[
        {"id":"sentry.rules.conditions.regression_event.RegressionEventCondition"}
       ],
       "filters":[
         {"id":"sentry.rules.filters.latest_release.LatestReleaseFilter"}
       ],
       "frequency":"5",
       "type": "issue" # used by this script, not Sentry API, to determine which alert-creation endpoint to use
    }),
    "Users Experiencing Error Frequently": jsons.dumps({
        "actionMatch":"all",
        "filterMatch":"all",
        "actions":[],
        "conditions": [
            {
                "interval":"5m",
                "id":"sentry.rules.conditions.event_frequency.EventUniqueUserFrequencyCondition",
                "comparisonType":"count",
                "value":"20"
            }
        ],
        "filters":[],
        "frequency":"5",
        "type": "issue"
    }),
    "Error Matches Tag <todo: set tag rule>": jsons.dumps({
            "actionMatch":"all",
            "filterMatch":"all",
            "actions":[],
            "conditions":[
                {
                    "interval":"5m",
                    "id":"sentry.rules.conditions.event_frequency.EventUniqueUserFrequencyCondition",
                    "comparisonType":"count",
                    "value":"50"
                }
            ],
            "filters":[
                {
                    "match":"co",
                    "id":"sentry.rules.filters.tagged_event.TaggedEventFilter",
                    "key":"exampleKey",
                    "value":"exampleValue"
                }
            ],
            "frequency":30,
            "type":"issue"
        })

}

METRIC_ALERTS = {
    "User Crash-Free Rate Dropped": jsons.dumps({
        "dataset":"metrics",
        "aggregate":"percentage(users_crashed, users) AS _crash_rate_alert_aggregate",
        "query":"",
        "timeWindow":60,
        "thresholdPeriod":1,
        "triggers":[
            {"label":"critical","alertThreshold":97,"actions":[]},
            {"label":"warning","alertThreshold":98,"actions":[]}
        ],
        "projects":["blog-nextjs-demo"],
        "environment":None,
        "resolveThreshold":99,
        "thresholdType":1,
        "comparisonDelta":None,
        "queryType":2,
        "type": "metric"
    }),
    "Crash-Free Sessions Rate Dropped": jsons.dumps({
        "dataset":"metrics",
        "aggregate":"percentage(sessions_crashed, sessions) AS _crash_rate_alert_aggregate",
        "query":"",
        "timeWindow":60,
        "thresholdPeriod":1,
        "triggers":[
            {
                "label":"critical",
                "alertThreshold":97,
                "actions":[]
            },
            {
                "label":"warning",
                "alertThreshold":98,
                "actions":[]
            }
        ],
        "projects":["blog-nextjs-demo"],
        "environment":None,
        "resolveThreshold":99,
        "thresholdType":1,
        "comparisonDelta":None,
        "queryType":2,
        "type":"metric"
    }),
    "Percent Change Threshold in Number of Errors": jsons.dumps({
            "dataset":"events",
            "eventTypes":["error"],
            "aggregate":"count()",
            "query":"",
            "timeWindow":60,
            "thresholdPeriod":1,
            "triggers":[
                {
                    "label":"critical",
                    "alertThreshold":10,
                    "actions":[]
                },
                {
                    "label":"warning",
                    "alertThreshold":5,
                    "actions":[]
                }
            ],
            "projects":["blog-nextjs-demo"],
            "environment":None,
            "resolveThreshold":None,
            "thresholdType":0,
            "comparisonDelta":10080,
            "queryType":0,
            "type": "metric"
    }),
}

HIGH_TRAFFIC = {
    "High Throughput": jsons.dumps({
        "dataset":"transactions",
        "eventTypes":["transaction"],
        "aggregate":"count()",
        # "query":"transaction:<transaction name>", # this will get interpolated!!!
        "timeWindow":60,
        "thresholdPeriod":1,
        "triggers":[
            {"label":"critical","alertThreshold":10,"actions":[]},
            {"label":"warning","alertThreshold":5,"actions":[]}
        ],
        "projects":["blog-nextjs-demo"],
        "environment":None,
        "resolveThreshold":None,
        "thresholdType":0,
        "comparisonDelta":1440,
        "queryType":1,
        "type": "metric"
    })
}

def do_setup():
    global configs
    global headers
    global current_datetime
    required_config_keys = ["ORG_NAME", "AUTH_KEY", "CRITICAL", "WARNING", "SLEEP_TIME", "ALERT_RULE_SUFFIX"]
    try:
        # Init logger
        current_datetime = datetime.now().strftime('%m-%d-%Y_%I:%M:%S %Z')
        logging.basicConfig(filename=f'alert_logfile_{current_datetime}.log', format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %I:%M:%S')
        logging.getLogger().setLevel(logging.ERROR)
        logging.getLogger().setLevel(logging.INFO)

        # Read configuration
        with open('config.properties', 'rb') as config_file:
            configs.load(config_file)

        keys = configs.__dict__
        keys = keys['_key_order']
       
        diff = [i for i in required_config_keys + keys if i not in required_config_keys or i not in keys]
        result = len(diff) == 0
        if not result:
            logging.error(f'These config {len(diff)} key(s) are missing from config file: {diff[:5]}')
            sys.exit()

        for item in required_config_keys:
            if item not in keys:
                print(item)
                logging.error(item + ' is a missing key in your config file.')
                logging.error()
                
      
        for key, value in configs.items():
            if(value.data == ''):
                logging.error('Value for ' + key + ' is missing.')
                sys.exit()

        # Init request headers
        headers = {'Authorization': "Bearer " + configs.get("AUTH_KEY").data, 'Content-Type' : 'application/json'}
    except Exception as e: 
        print(f'do_setup: failed to setup - {e}')
        sys.exit()

    
def get_alerts(): 
    global alert_list
    global configs
    global headers
    try: 
        response = requests.get(f'https://sentry.io/api/0/organizations/{configs.get("ORG_NAME").data}/combined-rules/', headers = headers)
        store_alerts(response.json())
        while response.links["next"]["results"] == "true":
            response = requests.get(response.links["next"]["url"], headers = headers)
            store_alerts(response.json())   
    except Exception as e:
        print(f'get_alerts: failed to call alert rules api - {e}')
        sys.exit()


def store_alerts(json_data):
    for alert in json_data:
        if "name" in alert:
            alert_list.append(alert["name"])
        else:
            logging.error('store_alerts: could not get existing alert name')

def get_projects(projects_to_operate_on):
    global headers
    try: 
        response = requests.get(f' https://sentry.io/api/0/organizations/{configs.get("ORG_NAME").data}/projects/', headers = headers)
        store_projects(response.json(), projects_to_operate_on)

        while response.links["next"]["results"] == "true":
            response = requests.get(response.links["next"]["url"], headers = headers)
            store_projects(response.json(), projects_to_operate_on)
    except Exception as e:
        logging.error(f'get_projects: unable to do get request - {e}')
        sys.exit()


def store_projects(json_data, projects_to_operate_on):
    global projects_dict

    for project in json_data:
        try:
            project_name = project["slug"]

            if projects_to_operate_on and project_name not in projects_to_operate_on:
                # if we've specified projects to operate on, and this isn't one of them
                # -- then skip adding alerts for this project
                continue

            teams = project["teams"]
            projects_dict[project_name] = list()
       
            for team in teams:
                team_id = team["id"]
                projects_dict[project_name].append(team_id)
        except Exception as e:
            logging.error(f'create_project: could not get existing project names - {e}')
            script_report["exists"] += 1

def create_alerts():
    global headers
    global projects_dict
    global alert_list
    global script_report
    proj_team_list = []
    team_list = []
    script_report = {"success": 0, "failed": 0, "exists": 0}
    alert_rule_suffix = configs.get("ALERT_RULE_SUFFIX").data

    print('about to create alerts..')
    for proj_name, teams in projects_dict.items():
        # Create Issue Alerts
        for alert_name, payload in ISSUE_ALERTS.items():
            json = build_alert_json(proj_name, alert_name, payload)
            create_alert(proj_name, alert_name, json, teams)

        # Create Metric Alerts
        for alert_name, payload in METRIC_ALERTS.items():
            json = build_alert_json(proj_name, alert_name, payload)
            create_alert(proj_name, alert_name, json, teams)

        # Create High-Traffic Metric Alerts
        # url_high_traffic_transactions = f'https://sentry.io/api/0/organizations/{configs.get("ORG_NAME").data}/events/?field=transaction&field=project&field=count%28%29&field=avg%28transaction.duration%29&field=p75%28%29&field=p95%28%29&per_page=50&project=5808655&query=event.type%3Atransaction&referrer=api.discover.query-table&sort=-count&statsPeriod=24h'
        # print(url_high_traffic_transactions)
        # print(headers)
        # high_traffic_transactions = requests.get(url_high_traffic_transactions, headers = headers)
        # print(high_traffic_transactions.content)
        # # transactions_to_alert_on = high_traffic_transactions[0:3] # 3 highest-traffic transactions
        # # print(transactions_to_alert_on)
        # # for transaction in transactions_to_alert_on:
        #     #proj_name = # determine this via the response
        #     #
        #     # json = build_alert_json(HIGH_TRAFFIC)

            
def create_alert(proj_name, alert_type, alert_payload_json, teams):
    alert_name = json.loads(alert_payload_json)["name"]
    if no_teams_assigned_to_project(teams):
        script_report["failed"] += 1
        logging.error(f'create_alert: failed to create alert for project: {proj_name} - No teams assigned to project')

    elif alert_already_exists(alert_name):
        script_report["exists"] += 1
        logging.info('create_alert: alert already exists for project ' + proj_name + '!') 
    else:
        try:
            alert_type = json.loads(alert_payload_json)["type"]
            alert_via_api(proj_name, alert_name, alert_payload_json, teams, alert_type)
        except Exception as e:
            script_report["failed"] += 1
            logging.error(f'create_alert: ensure the alert json has a "type" key with value corresponding to "metric" or "issue" : {alert_name}')

def alert_via_api(proj_name, alert_name, json_data, teams, alert_type):
    url = generate_url(proj_name, alert_name, alert_type)

    try:
        print(f'- Attempting to create alert: "{alert_name}"')
        response = requests.post(
                    url,
                    headers = headers, 
                    data=json_data)

        if(response.status_code in [200, 201]):
            script_report["success"] += 1
            logging.info('alert_via_api: Successfully created the metric alert ' + alert_name + ' for project: ' + proj_name)
        elif (response.status_code == 400):
            script_report["failed"] += 1
            logging.error('alert_via_api: could not create alert for project: ' + proj_name)
            logging.error(str(response.json()) + proj_name)
        elif (response.status_code == 403):
            logging.error('alert_via_apis: received the following status code: ' + str(response.status_code) + ' \nYou may be using your user level token without the necessary permissions.  \nPlease assign the AUTH_KEY to your org level token and refer to the README on how to create one.')
            sys.exit()
        else: 
            script_report["failed"] += 1
            logging.error('alert_via_api: received the following status code: ' + str(response.status_code) + ' for project: ' + proj_name)   

    except Exception as e:
        script_report["failed"] += 1
        logging.error(f'alert_via_api: failed to create alert for project : {proj_name} - {e}')
                   
    time.sleep(int(configs.get("SLEEP_TIME").data)/1000)

def no_teams_assigned_to_project(teams):
    return len(teams) == 0

def alert_already_exists(alert_name):
    return alert_name in alert_list

def build_alert_json(proj_name, alert_name, payload):
    payload = jsons.loads(payload)
    name = proj_name + " - " + alert_name

    # Alert names can only contain up to 64 characters
    name64 = name[:60] + " ..." if len(name) > 64 else name

    payload["name"] = name64    
    return jsons.dumps(payload)

def generate_url(proj_name, alert_name, alert_type):
    url = f'https://sentry.io/api/0/projects/{configs.get("ORG_NAME").data}/{proj_name}'
    
    if alert_type == 'issue':
        url += "/rules/"
    elif alert_type == 'metric':
        url += "/alert-rules/"
    else:
        script_report["failed"] += 1
        logging.error(f'alert_via_api: no alert type detected for {alert_name}')
        return
    return url

def main(argv):
    global alert_list
    global configs
    global headers
    global script_report
    global current_datetime

    projects_to_operate_on = argv

    do_setup() 


    if not projects_to_operate_on:
        selection = input(f"Caution: you are about to create alerts for all projects in {configs.get('ORG_NAME').data}.\n  - Continue? y/n:\n")
        if selection != "y":
            print("'y' not selected. Exiting program.")
            sys.exit()

    get_alerts()
    get_projects(projects_to_operate_on)
    create_alerts()

    # Print final script status
    print("Script report:  ", script_report)
    print(f"Check log file alert_logfile_{current_datetime}.log for details.")
    
if __name__ == '__main__':
     main(sys.argv[1:])
