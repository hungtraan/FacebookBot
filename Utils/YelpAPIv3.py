import requests

class Client3:
    def __init__(self, token):
        self.endpoint = 'https://api.yelp.com/v3/businesses/search'
        self.headers = {"Authorization": "Bearer {}".format(token)}
        self.endpoint_id = 'https://api.yelp.com/v3/businesses/'
    def search(self, **params):
        r = requests.get(self.endpoint, headers=self.headers, params=params)
        return r.json()

    def search_by_coordinates(self, **params):
        r = requests.get(self.endpoint, headers=self.headers, params=params)
        return r.json()

    def get_details(self, business_id):
        endpoint = self.endpoint_id + business_id
        r = requests.get(endpoint, headers=self.headers)
        return r.json()

    def get_reviews(self, business_id):
        endpoint = self.endpoint_id + business_id + "/reviews"
        r = requests.get(endpoint, headers=self.headers)
        return r.json()