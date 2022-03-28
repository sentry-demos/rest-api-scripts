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

<img width="784" alt="Screen Shot 2022-11-15 at 4 55 49 PM" src="https://user-images.githubusercontent.com/65051899/202057359-ddceeab9-5cd1-4bc2-a043-8e425ab4bf6e.png">
