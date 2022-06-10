
import os
import sys

import requests


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

        return results
        
    def get_projects(self):
        results = self._get_api_pagination(f'/api/0/projects/healthsherpa/healthsherpa/issues/')
        return results


if __name__ == '__main__':
    
    os.environ['SENTRY_CLOUD_AUTH_TOKEN'] = ''
    cloud_token = os.environ['SENTRY_CLOUD_AUTH_TOKEN']
   
    sentry_cloud = Sentry('https://sentry.io',
                          '<ORG_SLUG>',
                          cloud_token)

    sentry_response = sentry_cloud.get_projects() 
    print(sentry_response)
    

