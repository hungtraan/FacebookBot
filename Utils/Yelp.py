from yelp.client import Client
from YelpAPIv3 import Client3
from GoogleMapAPI import GoogleMap
from yelp.oauth1_authenticator import Oauth1Authenticator
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import config
from bs4 import BeautifulSoup
import requests

# Yelp Auth API v2
auth = Oauth1Authenticator(
    consumer_key=config.CONSUMER_KEY,
    consumer_secret=config.CONSUMER_SECRET,
    token=config.TOKEN,
    token_secret=config.TOKEN_SECRET
)

yelpClient = Client(auth)
yelpClient3 = Client3(config.YELP_V3_TOKEN)

def yelp_search_v2(searchTerm, location, coordinates=None, limit=None, offset=0):
    if limit is None:
        limit = 10

    params = {
        'term': searchTerm,
        'lang': 'en',
        'limit': limit,
        'offset': offset
        # 'category_filter':''
    }

    returnData = {}
    returnData['businesses'] = []
    returnData['status'] = 0
    
    try:
        if coordinates is not None:
            response = yelpClient.search_by_coordinates(coordinates[0], coordinates[1], **params)
        elif location != '':
            response = yelpClient.search(location, **params)
    except Exception, e:
        print e
        return returnData
    
    # v2      
    if len(response.businesses):
        returnData['status'] = 1
        for biz in response.businesses:
            business = {}
            business['name'] = biz.name
            business['address'] = biz.location.address[0]
            if coordinates is not None:
                business['distance'] = calculate_distance(coordinates, [biz.location.coordinate.latitude, biz.location.coordinate.longitude])
            business['rating'] = str(biz.rating) +u"\u2605 (" + str(biz.review_count) + " reviews)"
            business['url'] = biz.url
            business['image_url'] = biz.image_url
            business['categories'] = ', '.join([b.name for b in biz.categories])
            returnData['businesses'].append(business)
    else:
        returnData['status'] = 0

    return returnData

def yelp_search_v3(searchTerm, location, coordinates=None, limit=None, offset=0):
    if limit is None:
        limit = 10

    params = {
        'term': searchTerm,
        'lang': 'en',
        'limit': limit,
        'offset': offset,
        'location': location
        # 'category_filter':''
    }

    returnData = {}
    returnData['businesses'] = []
    returnData['status'] = 0
    print coordinates
    try:
        if coordinates is not None:
            params['latitude'] = coordinates[0]
            params['longitude'] = coordinates[1]
            response = yelpClient3.search_by_coordinates(**params)
            # print response
        elif location != '':
            response = yelpClient3.search(**params)
            # print response
    except Exception, e:
        print e
        return returnData
            
    if len(response['businesses']):
        returnData['status'] = 1
        for biz in response['businesses']:
            details = yelpClient3.get_details(biz['id'])
            business = {}
            business['id'] = biz['id']
            business['name'] = biz['name']
            business['price'] = biz['price'] if 'prize' in biz else ""
            # business['hours'] = details['hours'][0]['open']
            if 'hours' in details and len(details['hours']) > 0:
                business['is_open_now'] = details['hours'][0]['is_open_now']
                if len(details['hours'][0]['open']) > 0:
                    business['hours_today'] = hours_today(details['hours'][0]['open'])
            business['address'] = biz['location']['address1']
            if coordinates is not None:
                business['distance'] = calculate_distance(coordinates, [biz['coordinates']['latitude'], biz['coordinates']['longitude']])
            business['rating'] = str(biz['rating']) +u"\u2605 (" + str(biz['review_count']) + " reviews)"
            business['url'] = biz['url']
            business['image_url'] = biz['image_url']
            business['categories'] = ', '.join([b['title'] for b in biz['categories']])
            returnData['businesses'].append(business)
    
    return returnData

def hours_today(hours, api='yelp'):
    todayWkday = datetime.weekday(datetime.now())
    if todayWkday >= len(hours):
        return ""
    if api == 'yelp':
        start = hours[todayWkday]['start']
        end = hours[todayWkday]['end']
    elif api == 'google':
        start = hours[todayWkday]['open']['time']
        start = hours[todayWkday]['close']['time']
    
    return "%s:%s - %s:%s"%(start[:2], start[2:], end[:2], end[2:])

def get_reviews(business_id, limit=3):
    return yelpClient3.get_reviews(business_id)['reviews']
    
def calculate_distance(coord1, coord2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    coords = coord1 + coord2
    lon1, lat1, lon2, lat2 = map(radians, coords)
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6371 * c # earth radius * c
    mi = km / 1.609344
    return round(mi, 2)

def filtered_search(returnData, filter_list):
    businesses = returnData['businesses']
    result = []
    for business in businesses:
        url = business['url']
        r = requests.get(url)
        soup = BeautifulSoup(r, "html")
        attr_list = soup.select('.short-def-list > dl')
        open_div = soup.select(".open")

        if 'wifi' in filter_list:
            for attr in attr_list:
                if "Wi-Fi" in str(attr) and "Free" in str(attr):
                    if 'open_now' in filter_list:
                        if len(open_div) != 0:
                            result.append(business)
                    else:
                        result.append(business)

    return result

googlePlaceClient = GoogleMap()

# Not using Google Place Search since it doesn't provide a image URL
# but rather an image blob
def google_place_search(searchTerm, location, coordinates=None):

    query = "%s %s"%(searchTerm, location) if location is not None else searchTerm
    params = {
        'query': query,
    }
    if coordinates is not None:
        params['location'] = ",".join([str(coord) for coord in coordinates])
        params['radius'] = 10000 # meters

    returnData = {}
    returnData['businesses'] = []
    returnData['status'] = 0
    
    try:
        results = googlePlaceClient.search_place(**params)
        
    except Exception, e:
        print e
        return returnData
            
    if len(results['businesses']):
        returnData['status'] = 1
        for biz in results:
            details = googlePlaceClient.get_details(biz['place_id'])
            business = {}
            business['id'] = biz['id']
            business['name'] = biz['name']
            business['rating'] = str(biz['rating']) +u"\u2605 (" + str(biz['review_count']) + " reviews)"
            business['price'] = ""
            if 'opening_hours' in details:
                business['opening_hours'] = details['opening_hours']['open_now']
                if len(details['opening_hours']['periods']) > 0:
                    business['hours_today'] = hours_today(details['opening_hours']['periods'], 'google')
            business['address'] = biz['formatted_address']
            if coordinates is not None:
                business['distance'] = calculate_distance(coordinates, [biz['geometry']['location']['lat'], biz['geometry']['location']['lng']])
            business['url'] = details['url']
            business['image_url'] = ""
            business['categories'] = ""
            returnData['businesses'].append(business)
    
    return returnData