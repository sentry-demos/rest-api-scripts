# rest-api-scripts

For the above python scripts, please make sure to set the following environment variables: 

- `SENTRY_ONPREMISE_AUTH_TOKEN`
- `SENTRY_CLOUD_AUTH_TOKEN`  

Additionally, please make sure to change the following in the script to match your on-premise version of Sentry and your SaaS Sentry org slug: 

- `<ON_PREMISE_URL>`
- `<ON_PREMISE_ORG_SLUG>`
- `<ORG_SLUG>`

For the following script, `sentry_member_team_map.py`, you will need to have Python3 to run.  It was tested scucessfully with Python3.7.  

The permissions you will need for your internal integration that will generate the necessary auth tokens are shown below:

<img width="859" alt="Screen Shot 2022-06-01 at 5 21 17 PM" src="https://user-images.githubusercontent.com/4613264/171522708-254232b0-f2a1-428d-98dc-b02937db7959.png">
