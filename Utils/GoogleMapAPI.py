import requests

class GoogleMap:
    def __init__(self):
        self.place_endpoint = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        self.place_detail_endpoint = 'https://maps.googleapis.com/maps/api/place/details/json'
        self.place_photo_endpoint = 'https://maps.googleapis.com/maps/api/place/photo'
        self.api_key = 'AIzaSyBVNFviKv3cJW1NyaKgOKgyiTVTWzgXcLY'

    def search_place(self, **params):
        params['key'] = self.api_key
        r = requests.get(self.place_endpoint, params=params)
        return r.json()['results']

    def get_details(self, placeid):
        params = {
            'placeid': placeid,
            'key': self.api_key
        }
        r = requests.get(self.place_detail_endpoint, params=params)
        return r.json()['result']

    # Not working yet
    def get_image(self, ref_id):
        params = {
            'maxwidth': 400,
            'photoreference': ref_id,
            'key': self.api_key
        }
        r = requests.get(self.place_photo_endpoint, params=params, stream=True)
        image_blob = r.raw.read()
        return image_blob
        