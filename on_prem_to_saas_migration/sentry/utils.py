import re
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

def get_attributes_from_dsn(dsn):
    if dsn is not None:
        dsn_string = re.search(".*?\/\/(.*)@(.*)\/(.*)", dsn)
        if dsn_string is not None:
            if len(dsn_string.groups()) == 3:
                return dsn_string
    raise Exception("Could no retrieve project key")

def filter_exception(event_data):
    props = []
    valid_types = ["exception", "stacktrace", "threads", "message"]
    for data in event_data:
        if data["type"] in valid_types:
            props.append(data)
    return props

def filter_issues(issues, filters):
    if filters is None or "issues" in filters:
        return issues

    filtered_issues = []
    filter = None
    last_seen = None
    date_formats = ['%Y-%m-%dT%H:%M:%S%fZ', '%Y-%m-%dT%H:%M:%S.%fZ']

    if "start" in filters and filters["start"] is not None:
        filter = "timerange"
        start = filters["start"]
        if "end" not in filters:
            raise Exception("No end date provided")
        end = filters["end"]
    
    for issue in issues:
        if filter == "timerange":
            #print(issue)
            for format in date_formats:
                try:
                    last_seen = datetime.strptime(issue["lastSeen"], format).date()
                except ValueError as e:
                    #print(f'On-prem issue with ID {issue["id"]} had invalid "lastSeen" value {issue["lastSeen"]}')
                    pass

            if last_seen is not None and last_seen >= start and last_seen <= end:
                filtered_issues.append(issue)
                
    return filtered_issues

def parse_string_date(date):
    date_formats = ['%Y-%m-%dT%H:%M:%S%fZ', '%Y-%m-%dT%H:%M:%S.%fZ']
    parsed_date = None
    try:
        for format in date_formats:
            try:
                parsed_date = datetime.strptime(date, format).date()
            except ValueError as e:
                #print(f'On-prem issue with ID {issue["id"]} had invalid "lastSeen" value {issue["lastSeen"]}')
                continue
            break
    except:
        print("something went wrong")
    return parsed_date


def get_issue_attr(event_id, metadata, attr_name):
    for data in metadata:
        if data["event_id"] == event_id:
            return data[attr_name]
    return None

def get_dry_run(args):
    if len(args) > 1:
        if "--dry-run" in args:
            return True
        else:
            raise Exception("Invalid argument : To dry-run script, please specify the '--dry-run' argument")
    return False

def process_cli_args(args, logger):
    valid_args = ["--dry-run", "--start", "--end", "--issues", "--fetchRelease"]
    if "--help" in args:
        print_help_log()
        return False
    args = args[1::]
    for arg in args:
        sp = arg.split("=")
        if sp[0] not in valid_args:
            logger.error(f'Invalid argument `{arg}`')
            print_help_log()
    return args

def print_help_log():
    args = [
        {
            "--dry-log" : "\tRun script in dry-mode. Events will not be sent to SaaS but it will print the output"
        },
        {
            "--start" : "\t\tStart date to fetch issues from on-prem"
        },
        {
            "--end" : "\t\tEnd date to fetch issues from on-prem"
        },
        {
            "--issues" : "\tList of issues to migrate from on-prem to SaaS"
        }
    ]
    print('ARGUMENT \t DESCRIPTION')
    print()

    for i in args:
        for key in i:
            print(f'{key}{i[key]}')


def replace_all(str, chars, new_val = ""):
    for char in chars:
        str = str.replace(char, new_val)
    return str

def get_request_filters(cli_args, logger):
    load_dotenv()

    if len(cli_args) == 1:
        return True

    start = None
    end = None
    issues = None
    fetch_release = False
    date_format = '%Y-%m-%d'
    for arg in cli_args:
        sp = arg.split("=")
        if len(sp) > 1:
            if "issues" in sp[0]:
                issues = sp[1].split(",")
            if "start" in sp[0] or "end" in sp[0]:
                try:
                    date_object = datetime.strptime(sp[1], date_format)
                    if "start" in sp[0]:
                        start = date_object.date()
                    elif "end" in sp[0]:
                        end = date_object.date()
                except ValueError:
                    logger.error(f'Invalid date {sp[1]} - Date should be in YYYY-mm-dd format')
                    return None
            if "fetchRelease" in sp[0]:
                fetch_release = sp[1].lower() == "true"
    
    if issues is None:
        if "ISSUES" in os.environ and os.environ["ISSUES"] is not None:
            issues = os.environ["ISSUES"].split(",")
    if start is None:
        if "START" in os.environ:
            try:
                date_object = datetime.strptime(os.environ["START"], date_format)
                start = date_object.date()
            except ValueError:
                logger.error(f'Invalid date {os.environ["START"]} - Date should be in YYYY-mm-dd format')
                return None
    if end is None:
        if "END" in os.environ:
            try:
                date_object = datetime.strptime(os.environ["END"], date_format)
                start = date_object.date()
            except ValueError:
                logger.error(f'Invalid date {os.environ["END"]} - Date should be in YYYY-mm-dd format')
                return None

    
    if issues is not None:
        logger.debug(f'Filtering issues based on list {str(issues)}')
        return {
            "issues" : issues,
            "fetch_release": fetch_release
        }
    if start is not None:
        if end is None:
            logger.error("end argument is required if start was specified")
            return None
        else:
            if start >= end:
                logger.error("start value has to be before end value")
                return None
            if start < (datetime.today() - timedelta(days=90)).date():
                logger.error("start date can't be older than 90 days")
                return None
            logger.debug(f'Filtering issues based on start {start} and end {end}')
            return {
                "start" : start,
                "end" : end,
                "fetch_release": fetch_release
            }
    if end is not None:
        logger.error("start argument is required if end was specified")
    
    return None
       
    