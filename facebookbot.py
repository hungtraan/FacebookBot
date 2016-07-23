import sys
<<<<<<< Updated upstream
=======
import json
from Utils import Yelp, FacebookAPI, NLP, MongoHelper
from Speech import processor as STT # Speech to Text
>>>>>>> Stashed changes

from flask import Flask, request, session, g
import json
import requests
import string
from pattern.en import parsetree
from datetime import datetime, timedelta
import time
from math import radians, cos, sin, asin, sqrt
import random

# import mysql.connector as mysql
from bson.objectid import ObjectId
from pymongo import MongoClient, DESCENDING
# from flask_pymongo import PyMongo

from yelp.client import Client
from yelp.oauth1_authenticator import Oauth1Authenticator

<<<<<<< Updated upstream
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'development key'
=======
app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')
>>>>>>> Stashed changes

# app.config['MONGO_DBNAME'] = 'facebookbot'
# app.config['MONGO_URI'] = 'mongodb://localhost:27017/facebookbot'

# mongo = PyMongo(app)
# mongo = MongoClient()
mongo = MongoClient('localhost', 27017)
db = mongo.facebook_bot # Get database
users = db.users # Get users collection
log = db.message_log # Get log collection

# This needs to be filled with the Page Access Token that will be provided
# by the Facebook App that will be created.
PAT = 'EAADhYj0lr14BACDUc9WI2quEuF8cksXZAoOzesZAhes6MgukqS0EQbIlPbehlt69PgZAOuXW5SWQ4C9XFZBJ4aB4MoBBpsBOK5qVRnooHXoqivEoHtd2Sg9OXcGi6DyykIoJF3rNwYotBiMkrA8sBvl9cKB8lCbEl0QHTVZClEQZDZD'

# Yelp Auth
auth = Oauth1Authenticator(
    consumer_key="z6tcXDKgnw_6PptHWG-9LQ",
    consumer_secret="RRd4QiAlikbzhcY-3IM7XrKUdUY",
    token="1T-eGAQp4gnIl7wJ2j-LUVRd_LHU07Xx",
    token_secret="4HaL6UuyhfuN_eXTsq5FPfHWLDY"
)
yelpClient = Client(auth)

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = get_user_mongo(ObjectId(session['user_id']), True)
        # Note: session['user_id'] holds mongo's ObjectId(''), not Facebook user_id

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=15)
# https://github.com/pallets/flask/blob/master/examples/minitwit/minitwit.py
# http://flask.pocoo.org/docs/0.11/api/#flask.Flask.before_first_request

@app.route('/', methods=['GET'])
def handle_verification():
    print "Handling Verification."
    if request.args.get('hub.verify_token', '') == 'baddest_ass_bot_you_know':
        print "Verification successful!"
        return request.args.get('hub.challenge', '')
    else:
        print "Verification failed!"
        return 'Error, wrong validation token'


@app.route('/', methods=['POST'])
def handle_messages():
    print "Handling Messages"
    payload = request.get_data()
    
    # print payload
    for sender, message in messaging_events(payload):
        # print "Incoming from %s: %s" % (sender, message)
        # print "User ID: %s" % (sender)
        response = processIncoming(sender, message)
        if response is not None:
            send_message(PAT, sender, response)
    return "ok"

def processIncoming(user_id, message):
    # sender = get_user_mongo(user_id) # Sender now is a dict object

    if g.user is None:
        if not user_exists(user_id): # First time user
            g.user = get_user_mongo(user_id)
            response = "%s %s, nice to meet you"%(sayHiTimeZone(), g.user['first_name'])
            # Some functionality introduction here
            return response
        else:
            g.user = get_user_mongo(user_id)
            session['user_id'] = str(g.user['_id'])
            
    contextData = g.user['contexts']
    
    if message['type'] == 'text':
        incomingMessage = message['data']
        if '.' not in incomingMessage:
            incomingMessage+="."
        s = parsetree(incomingMessage, relations=True, lemmata=True)
        sentence = s[0]
        verb = findVerb(sentence)  # list
        # print "Verbs: ", verb
        nounPhrase = findNounPhrase(sentence)
        # print "NPs: ", nounPhrase

        if contextData is not None and len(contextData) > 0:
            context = contextData[-1]
            if context['context'] == 'findFood':
                if context['location'] == None and context['coordinates'] == None:
                    context['location'] = nounPhrase
                    location = {'type':'text','data': nounPhrase}
                    update_context(user_id, 'findFood', 'location', nounPhrase)
                    add_yelp_location_history(user_id, location)
                    send_message(PAT, user_id, "Sure, give me a few seconds...")
                    result = yelp_search(context['terms'], nounPhrase)
                    
                    if result['status'] == 1: # Successful search
                        send_message(PAT, user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
                        send_yelp_results(user_id, result['businesses'])
                        send_quick_replies_yelp(PAT, user_id)
                    else:
                        pop_context()
                        return "Sorry I can't find any places for that"
                        # Follow up
                    return
                else:
                    pop_context()
                    return
                
        else:
            if isGreetings(incomingMessage):
                greeting = "%s %s"%(sayHiTimeZone(), g.user['first_name'])
                send_message(PAT, user_id, greeting)
                return "How can I help you?"

            if isGoodbye(incomingMessage):
                return sayByeTimeZone()

            if yelp(verb):                
                contextNow = {'context':'findFood', 
                              'location': None,
                              'coordinates': None,
                              'terms': nounPhrase
                              }
                add_context(user_id, contextNow)
                return "Can you send me your whereabouts?"
                if nearBy(s[0]):
                    # https://fbnewsroomus.files.wordpress.com/2015/06/messenger-location-sharing1-copy.png?w=600&h=568
                    add_context(user_id, contextNow)
                    return "Can you send me your whereabouts?"
                else:
                    # follow up to ask for location
                    return message['data']
            else:        
                return #"I'm sorry I can't process that"

    elif message['type'] == 'location':
        send_message(PAT, user_id, "I've received location (%s,%s)"%(message['data'][0],message['data'][1]))

        if contextData is not None and len(contextData) > 0:
            context = contextData[-1]
            if context['context'] == 'findFood':
                location = {'type':'coordinates','data': message['data']}
                update_context(user_id, 'findFood', 'coordinates', message['data'])
                add_yelp_location_history(user_id, location)
                send_message(PAT, user_id, "Looking looking... :D")
                result = yelp_search(context['terms'], None, message['data'])
                if result['status'] == 1:
                    send_message(PAT, user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
                    send_yelp_results(user_id, result['businesses'])
                    send_quick_replies_yelp(PAT, user_id)
                return

    elif message['type'] == 'audio':
        return "I've received audio %s"%(message['data'])

    elif message['type'] == 'quick_reply':
        context = contextData[-1]
        cmd = message['data']
        # cmd: [yelp-more, yelp-ok]
        if cmd == 'yelp-more':
            increment_yelp_offset(user_id, 5)
            offset = g.user['yelp_offset']
            result = yelp_search(context['terms'], context['location'], context['coordinates'], 5, offset)

            if result['status'] == 1: # Successful search
                send_message(PAT, user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
                send_yelp_results(user_id, result['businesses'])
                send_quick_replies_yelp(PAT, user_id)
            else:
                pop_context()
                reset_yelp_offset()
                return "That's all I found for now :)"


        elif cmd == 'yelp-ok':
            pop_context()
            reset_yelp_offset()
            send_message(PAT, user_id, "Glad I can help :)")

    else:
        pop_context()

def messaging_events(payload):
    """Generate tuples of (sender_id, message_text) from the
    provided payload.
    """
    data = json.loads(payload)
    # print data
    messaging_events = data["entry"][0]["messaging"]
    for event in messaging_events:
        sender_id = event["sender"]["id"]
        if "message" in event and "text" in event["message"] and "quick_reply" not in event["message"]:
            data = event["message"]["text"].encode('unicode_escape')
            log_message(sender_id, 'text', data)
            yield sender_id, {'type':'text', 'data': data}

        elif "attachments" in event["message"]:
            if "location" == event['message']['attachments'][0]["type"]:
                coordinates = event['message']['attachments'][
                    0]['payload']['coordinates']
                latitude = coordinates['lat']
                longitude = coordinates['long']
                log_message(sender_id, 'coordinates', str([latitude, longitude]))
                yield sender_id, {'type':'location','data':[latitude, longitude]}

            elif "audio" == event['message']['attachments'][0]["type"]:
                audio_url = event['message'][
                    'attachments'][0]['payload']['url']
                log_message(sender_id, 'audio', audio_url)
                yield sender_id, {'type':'audio','data': audio_url}
            else:
                log_message(sender_id, 'other1', event["message"])
                yield sender_id, {'type':'other','data':"I can't echo this"}

# {u'entry': [{u'messaging': [{u'timestamp': 1468473549239, u'message': {u'text': u"That's good for me", u'mid': u'mid.1468473549228:3858f641f8ed244772', u'seq': 995, u'quick_reply': {u'payload': u'payload_ok'}}, u'recipient': {u'id': u'1384358948246110'}, u'sender': {u'id': u'1389166911110336'}}], u'id': u'1384358948246110', u'time': 1468473549266}], u'object': u'page'}
        elif "quick_reply" in event["message"]:
            data = event["message"]["quick_reply"]["payload"]
            yield sender_id, {'type':'quick_reply','data': data}
        else:
            log_message(sender_id, 'other2', event["message"])
            yield sender_id, {'type':'other','data':"I can't echo this"}

def get_user_from_message(payload):
    data = json.loads(payload)
    messaging_events = data["entry"][0]["messaging"][-1]
    return messaging_events["sender"]["id"]

def get_user_fb(user_id):
    r = requests.get("https://graph.facebook.com/v2.6/" + user_id,
                      params={"fields": "first_name,last_name,profile_pic,locale,timezone,gender"
                      ,"access_token": PAT
                      })
    user = json.loads(r.content)
    return user

def find_user_id(user_object_id):
    # Convert from string to ObjectId:
    return users.find_one({'_id': ObjectId(user_object_id)})

def user_exists(user_id):
    user = users.find_one({'user_id': user_id})
    if user is None:
        user_fb = get_user_fb(user_id)
        add_user_mongo(user_id, user_fb)
        return False
    return True

def get_user_mongo(user_id, useObjectId=False):
    return users.find_one({'user_id': user_id}) if not useObjectId else users.find_one({'_id': user_id})

def add_user_mongo(user_id, user_fb):
    user_insert = {'user_id': user_id, 
                    'first_name':user_fb['first_name'],
                    'last_name':user_fb['last_name'],
                    'gender': user_fb['gender'],
                    'timezone':user_fb['timezone'],
                    'contexts':[],
                    'yelp_location_history':[]}
    users.insert(user_insert)

def get_context(user_id):
    user = users.find_one({'user_id': user_id})
    if user is None:
        return None
    else:
        return user['contexts']

def add_context(user_id, context):
    users.update({'user_id': user_id}, {"$push":{"contexts": context}})

def increment_yelp_offset(user_id, offset):
    users.update({"user_id":user_id},{"$inc":{"yelp_offset": offset}})
    g.user = get_user_mongo(user_id)

def reset_yelp_offset():
    users.update({"user_id": g.user['user_id']},{"$set":{"yelp_offset": 0}})

def update_context(user_id, find_by, context_to_update, content):
    users.update({'user_id': user_id, "contexts.context": find_by},
        { "$set": { "contexts.$.%s"%(context_to_update) : content } })
    
def pop_context(user_id=None):
    if user_id is None:
        users.update({'_id': g.user['_id']}, {"$pop":{"contexts":1}})
    else:
        users.update({'user_id': user_id}, {"$pop":{"contexts":1}})
    
def get_most_recent_location_yelp(user_id=None):
    if user_id is None:
        return g.user['yelp_location_history'][-1]
    else:
        return users.find_one({'user_id': user_id})['yelp_location_history'][-1]

def add_yelp_location_history(user_id, location):
    users.update({'user_id': user_id}, {"$addToSet":{"yelp_location_history": location}})
    
def log_message(sender, mes_type, message):
    now = datetime.now()
    timeStr = datetime.strftime(now,"%Y-%m-%d %H:%M:%S")
    log.insert_one({"sender":sender, "type": mes_type, "message":message, "timestamp": timeStr })

# posts.update({"_id":5678},{"$set":{"from_user":"Alberto","source":"unavailable"}}, upsert=True)
# posts.find({"_id":5678}).count()
# posts.update({"_id":1234},{"$unset":{"total_posts":""}})
# posts.update({"_id":1234},{"$pop":{"sentiment":1}})
# posts.update({"_id":1234},{"$push":{"sentiment":{"nb":random.randint(-5, 5),"svm":random.randint(-5, 5)}}})
# posts.update({"_id":5678},{"$addToSet":{"skills":"python"}})  # adds a value to an array only if the value is not in the array already
# posts.update({"_id":5678},{"$pull":{"skills":"java"}}) # The pull operator removes all instances of a value from an existing array. 


def send_message(token, recipient, text):
    """Send the message text to recipient with id recipient.
    """

    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                          "recipient": {"id": recipient},
                          "message": {"text": text.decode('unicode_escape')}
                      }),
                      headers={'Content-type': 'application/json'})
    if r.status_code != requests.codes.ok:
        print r.text

def send_picture(token, recipient, imageUrl, title, subtitle=""):
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                          "recipient": {"id": recipient},
                          "message":{
                              "attachment": {
                                  "type": "template",
                                  "payload": {
                                      "template_type": "generic",
                                      "elements": [{
                                          "title": title,
                                          "subtitle": subtitle,
                                          "image_url": imageUrl
                                      }]
                                  }
                              }
                            }
                      }),
                      headers={'Content-type': 'application/json'})
    if r.status_code != requests.codes.ok:
        print r.text

def send_template_yelp(token, recipient, businesses):
    options = []

    for business in businesses:
        subtitle = business['address'] 
        if 'distance' in business:
            subtitle += " (" + str(business['distance']) + " mi.)"
        subtitle += "\n" + business['categories']

        obj = {
                "title": business['name'] + " - " + business['rating'],
                "image_url": business['image_url'],
                "subtitle": subtitle,
                "buttons":[
                    {
                    "type":"web_url",
                    "url": business['url'],
                    "title":"View details"
                    }
                    # ,{
                    # "type":"postback",
                    # "title":"Start Chatting",
                    # "payload":"USER_DEFINED_PAYLOAD"
                    # }          
                ]
                }
        options.append(obj) 
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                            "recipient": {"id": recipient},
                            "message":{
                                "attachment":{
                                    "type":"template",
                                    "payload":{
                                        "template_type":"generic",
                                        "elements": options
                                    }
                                }
                            }
                      }),
                      headers={'Content-type': 'application/json'})
    if r.status_code != requests.codes.ok:
        print r.text

def send_quick_replies_yelp(token, user_id):
    # options = [Object {name:value, url:value}, Object {name:value, url:value}]
    quickRepliesOptions = [
        {"content_type":"text",
         "title": "Get more suggestions",
         "payload": 'yelp-more'
        },
        {"content_type":"text",
         "title": "That's good for me",
         "payload": 'yelp-ok'
        }
    ]
    data = json.dumps({
            "recipient":{ "id": user_id },
            "message":{
                "text":"Do you want to find more results?",
                "quick_replies": quickRepliesOptions
                }
            })
    data = data.encode('utf-8')
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
        params={"access_token": token},
        data=data,
        headers={'Content-type':'application/json'})

    if r.status_code != requests.codes.ok:
        print r.text

def yelp_search(searchTerm, location, coordinates=None, limit=None, offset=0):
    if limit is None:
        limit = 5

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
    km = 6367 * c
    mi = km / 1.609344
    return round(mi, 2)

def send_yelp_results(sender, businesses):
    send_template_yelp(PAT, sender, businesses)
    # for business in businesses:
    #     response = business['name'] + " - " + business['rating'] + "\n"
    #     response += business['address']+ "\n"
    #     response += business['url'] 
    #     subtitle = business['rating'] + "\n"
    #     subtitle += business['address'] + "\n"
    #     subtitle += business['url'] 
    #     # send_message(PAT, sender, response)
        # send_picture(token, recipient, imageUrl, title, subtitle=""):
        # send_picture(PAT, sender, business['image_url'], business['name'],subtitle)

def removePunctuation(str):
    return str.translate(None, string.punctuation)

def sayHiTimeZone():
    server_now = datetime.now()
    user_now = getUserTime()
    if recentChat(server_now):
        return "Hi again"
    if user_now.hour < 12:
        return "Good morning"
    elif user_now.hour < 19:
        return "Good afternoon"
    else:
        return "Good evening"

def sayByeTimeZone():
    user_now = getUserTime()
    goodnights = ["Good night", "Have a good night", "Bye now", "See you later"]
    byes = ["Goodbye", "Bye then", "See you later", "Bye, have a good day"]
    
    if user_now.hour > 20:
        return goodnights[random.randint(0,len(goodnights))]
    else:
        return byes[random.randint(0,len(byes))]

def getUserTime():
    user_tz = g.user['timezone']
    offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
    server_tz = offset / 60 / 60 * -1
    time_diff = user_tz - server_tz
    server_now = datetime.now()
    return server_now + timedelta(hours=time_diff)

def recentChat(now):
    recent2messages = log.find({'sender': g.user['user_id']}, sort=[("timestamp", DESCENDING)]).limit(2)
    messageToCheck = recent2messages[1]
    timestamp = datetime.strptime(messageToCheck['timestamp'],"%Y-%m-%d %H:%M:%S")
    time_since_chat = now - timestamp
    recent30min = timedelta(minutes=30)
    if time_since_chat < recent30min:
        return True
    else:
        return False

def isGreetings(inp_str):
    string = removePunctuation(inp_str).lower()
    greetings = ['hi','hey','hello', 'greetings', 'good morning', 'good afternoon', 'good evening']
    for word in greetings:
        if word in string:
            return True
    return False

def isGoodbye(inp_str):
    string = removePunctuation(inp_str).lower()
    byes = ['bye', 'see you']
    for word in byes:
        if word in string:
            return True
    return False

def findVerb(sentence):
    result = []
    for chunk in sentence.chunks:
        if chunk.type in ['VP']:
            strings = [w.string for w in chunk.words if w.type in ['VB','VBP']]
            result.extend(strings)
        # print chunk.type, [(w.string, w.type) for w in chunk.words ]
    return result


def findNounPhrase(sentence):
    res = ""
    for chunk in sentence.chunks:
        if chunk.type == 'NP':
            res += " ".join([w.string for w in chunk.words if w.type not in ['PRP', 'DT']])
            res += " "
    return res

def findProperNoun(sentence):
    for chunk in sentence.chunks:
        if chunk.type == 'NP':
            for w in chunk.words:
                if w.type == 'NNP':
                    return w.string
    return None

def yelp(verbList):
    print verbList
    yelpVerbs = ['eat', 'drink', 'find']
    for verb in verbList:
        if verb.lower() in yelpVerbs:
            return True
    return False


def nearBy(sentence):
    res = ""
    for chunk in sentence.chunks:
        if chunk.type in ['PP', 'ADVP']:
            res += " ".join([w.string for w in chunk.words if w.type in ['RB', 'PRP', 'IN']])
            res += " "
    res = res.strip()
    if res in ['near', 'around here', 'around', 'here', 'near here', 'nearby', 'near by', 'close by', 'close']:
        return True
    return False

# def db():
#     host = 'http://us-cdbr-iron-east-03.cleardb.net/'
#     username = 'bbaf414965fded'
#     passwd = '2f3310e8'
#     database = 'heroku_fa3c47157b8ffc1'
#     db = mysql.connect(host=host, user=username, passwd=passwd,
#                         db=database, charset='utf8', use_unicode=True)

#     return db

# def dbInsert(db, cmd):
#     c = db.cursor()
#     try:
#         c.execute(cmd)
#         db.commit()
#     except Exception as e:
#         print(e)
#         pass

# https://console.ng.bluemix.net/?direct=classic/#/resources/serviceGuid=be619d85-cc2a-42be-85d1-97e6468cf813&orgGuid=5e25a0af-ebbd-467d-94c8-fa82ad647f70&spaceGuid=cbeefcec-89d7-482a-83df-183b978ec969&paneId=1
# http://www.ibm.com/watson/developercloud/doc/speech-to-text/http.shtml

if __name__ == '__main__':
    if len(sys.argv) == 2:
        app.run(port=int(sys.argv[1]))
    else:
        app.run()