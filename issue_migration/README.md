## Migration Script

The goal of this script is to migrate issue data from an on-prem version to SaaS Sentry. 

For this script to run, please make sure you have the following env variables:
- `ON_PREM_AUTH_TOKEN`
- `ON_PREM_URL`
- `ON_PREM_ORG_NAME`
- `ON_PREM_PROJECT_NAME`
- `SAAS_AUTH_TOKEN`
- `SAAS_ORG_NAME`
- `SAAS_PROJECT_NAME`
- `SAAS_PROJECT_DSN`
- `SAAS_URL`

Run `bash install.sh` to check python version as well as create virtual environment

Go into the virtual env by running `source venv/bin/activate`

Run `bash run.sh` to start the migration process.

**NOTE:** The auth token will need the following permissions:
- `issue&event:admin` 
- `project:admin`
- `org:admin`
- `member:read`


### How it works:
---
Given a list of `issue IDs` or a `start` and `end` time range, the script will fetch issues from an on-prem instance, normalize them and create the issues in the SaaS org. The script follow these steps:

1. Read CLI arguments or env variables to define criteria to fetch issues. See more in [Script Arguments](#script-arguments)
2. Fetch issues from the on-prem instance based on the defined criteria.
3. Generate new payload from issue data and stack trace normalization based on the data expected in the [Store endpoint](https://develop.sentry.dev/sdk/store/)
4. Get issue-level data from on-prem issues such as:
	- Issue `firstSeen`
	- Issue `lastSeen`
	- Issue `assignee` 
	- Linked JIRA tickets
5. Send the created payload (new SaaS issue) to Sentry using the [Store endpoint](https://develop.sentry.dev/sdk/store/)
6. Batch newly created issues
7. Update batches with the issue-level data gathered in step 4

The script will output logs in 2 places:
1. The terminal
2. It will create a log file with the current date as the name where information will be printed (If the script is run using the `--dry-run` flag, the payload output will only be printed to the file) 

**NOTE:** To migrate over issue assignee information, the script assumes that you are using the same SCIM provider in both your on-prem and SaaS instances. Or in other words, the email of the issue assignee is the same in both on-prem and SaaS.

### Script Arguments
---
The script will accept different CLI arguments at the time of calling `main.py`. Arguments like:

- `--dry-run` -> Runs the script in dry-mode. Events will not be sent to SaaS but it will print the payload that was generated
- `--help` -> Prints help log - It will print out all the CLI arguments that are available

There are 2 ways that you can specify the criteria that are used to fetch issues from an on-prem instance:

1. Specify arguments via the CLI when you run the `main.py` script. Arguments like:
	- `--issues` = A list of issues that will be fetched from an on-prem instance. (E.g `--issues 1,2,3`)
	- `--start` = (`YYYY-mm-dd`) ISO Start date when issues are going to be fetched from an on-prem instance - This value can't be older than 90 days (If this argument is specified, then the `--end` argument has to also be specified)
	- `--end` = (`YYYY-mm-dd`) ISO End date when issues are going to be fetched from an on-prem instance. (If this argument is specified, then the `--start` argument has to also be specified)
	
	**NOTE:** If you specify all possible arguments (`--issues`, `--start`, `--end`), then the value from the `--issues` argument will overwrite the others.

2. Specify variables in an `.env` file:
	- `ISSUES` = A list of issues that will be fetched from an on-prem instance.
	- `START` = (`YYYY-mm-dd`) ISO start date when issues are going to be fetched from an on-prem instance. (If this argument is specified, then the `END` argument has to also be specified)
	- `END` = (`YYYY-mm-dd`) ISO end date when issues are going to be fetched from an on-prem instance. (If this argument is specified, then the `START` argument has to also be specified)

**NOTE:** Values specified via the CLI will overwrite values specified in an `.env` file

## Things to look out for

- If you are migrating over issue assignee information, make sure that the team or person assigned to a ticket in the on-prem instance also exists on SaaS
- Might be a good idea to turn spike protection off while the script runs. This is because Sentry might drop some events if the volume ingested goes over the average consumed.
