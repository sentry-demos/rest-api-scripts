# Automatically Create Alert App Packs Via Script

## Summary:

#### The essentials
- Run this API script to create Alert App Pack rules for projects within an org.
- :warning: By default, it will create alerts for every project in an org.
- You can also pass a list of projects to create alerts for (see Run Script section).
  
#### Other things to know
- The alerts are created without being assigned any teams. SEs or customers will need to assign teams.
- The alerts are created with zero actions. SEs will need to encourage customers to add actions (i.e. set up an email/slack notification)
- Alert creation via the script is idempotent, i.e. you can run the script as many times as you want and it will not create duplicate alerts.

## Initial Setup

To setup the python env for this script:

1. Create env - ```python3 -m venv env```
2. Activate venv - ```source env/bin/activate```
3. Install requirements - ```pip install -r ./requirements.txt```

## Configure

Prior to running create_alerts.py, you can configure the following fields in the config.properties file:

1. `ORG_NAME= <org name> ` - This should be assigned to your Organization Slug, found under Settings --> General Settings.

2. `AUTH_KEY= <auth_key>` - Your **org level** auth key can be found under Settings --> Developer Settings --> Internal Integrations.

    a. If you don't have Internal Integrations set up, select New Internal Integrations and provide a Name for your integration. 

    b. The Project and Organization permissions should be set to Read & Write. 
    <img width="957" alt="Screen Shot 2021-05-17 at 2 29 02 PM" src="https://user-images.githubusercontent.com/82904656/118559227-7849c580-b71c-11eb-83ea-2b7fcdbe9461.png">
    
    c. Once the above fields have been configured, click on Save Changes.

    d. This should redirect you to your Internal Integrations page with a token. This token is your **org level** auth key. 

3. `CRITICAL=10000` - Critical threshold is set in the config file. No need to modify this value. 
4. `WARNING=8000` - Warning threshold is set in the config file. No need to modify this value. 
5. `SLEEP_TIME=<milliseconds>` - When updating sleep time, please provide this value in milliseconds.
6. `ALERT_RULE_SUFFIX=_quota_limit` - If you would like to rename the alert rule suffix, this can be done in the config file. 


## Run Script 

Create Alerts for All Projects

```
// Create alerts for ALL projects
$ python3 create_alerts.py

// Create alerts only for specified projects by passing one or more project slugs
// as command-line arguments.
$ python3 create_alerts.py myproj-javascript otherprojname-python third-proj-react
```

## Confirm Alert Creation

1. To confirm via UI navigate to the Alerts page to view the created alerts.
2. By running python3 create_alerts.py a second time you can confirm if the alert already exists. (Check the log file for `"alert already exists for + [project name]!"`)

## How To Present Alerts to the Customer

This script creates alerts with:
- no specified action
- certain default values that can and should change based on customer needs

You should walk the customer through the alerts you've created, on a call. Explain that they need to enable an action for any alerts they're interested in, and point out a few values that have been configured with defaults, that they can change as desired.

For example:

1. For the "Regression Error Occurred" alerts, we alert on the latest release. This is a fine default, but let customers know they could change it to remove that filter and alert on ANY regression if they wanted to.

![Screen Shot 2022-10-28 at 7 36 15 PM](https://user-images.githubusercontent.com/12092849/199081488-030da875-243a-4077-a701-f73fc5f470d7.png)

2. For the "Error Matches Tag <todo: set tag rule>", they will need to set a tag in the alert rules, and update the title accordingly.

![error matches tag](https://user-images.githubusercontent.com/12092849/199081908-826ec0dd-9e17-4c2b-aa77-73f8ee02b643.png)

3. In the "Users Experiencing Error Frequently", the default is currently to trigger when an issue is seen by more than 20 users in 5 minutes. Tell the customer they are free to tweak these numbers if there are numbers that make more sense for them.

![Screen Shot 2022-10-28 at 7 42 58 PM](https://user-images.githubusercontent.com/12092849/199081490-03c405a4-108c-4a8d-93fa-31c81dd1cf08.png)

## Debug and Logging

After running the script you will see a log file created with the following naming convention - `alert_logfile_{current_datetime}.log`

Potential error and info logs will be displayed here. 

## Adding New Alerts to the Script

You can add new alerts to the script. Add them to the relevant `ISSUE_ALERTS` or `METRIC_ALERTS` constant.
To successfully create a metric alert make sure each project has at least one team assigned to it! 
