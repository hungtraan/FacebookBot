import sys
# import requests
import json
import Yelp
import FacebookAPI
import NLP
import MongoHelper

from pattern.en import parsetree
from datetime import datetime, timedelta
from flask import Flask, request, g
from pymongo import MongoClient

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
# app.config.from_pyfile('config.py')

mongo = MongoClient(app.config['MONGO_URI'])
db = mongo[app.config['MONGO_DBNAME']] # Get database
users = db.users # Get users collection
log = db.message_log # Get log collection

@app.before_request
def before_request():
    g.user = None

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
            FacebookAPI.send_message(app.config['PAT'], sender, response)
    return "ok"

def processIncoming(user_id, message):
    if not MongoHelper.user_exists(users, user_id): # First time user
        g.user = MongoHelper.get_user_mongo(users, user_id)
        response = "%s %s, nice to meet you"%(NLP.sayHiTimeZone(g.user), g.user['first_name'])
        # Some functionality introduction here
        return response
    else:
        g.user = MongoHelper.get_user_mongo(users, user_id)

    now = datetime.now()
    timestamp = datetime.strftime(now,"%Y-%m-%d %H:%M:%S")
    last_seen = datetime.strptime(g.user['last_seen'],"%Y-%m-%d %H:%M:%S")
    recent5min = now - timedelta(minutes=5)

    if last_seen < recent5min:
        MongoHelper.update_last_seen(users, g.user, timestamp)

    contextData = g.user['contexts']
    
    if message['type'] == 'text':
        incomingMessage = NLP.removePunctuation(message['data'])
        if '.' not in incomingMessage: # help separate sentence for parsetree
            incomingMessage+="."
        s = parsetree(incomingMessage, relations=True, lemmata=True)
        sentence = s[0]
        verb = NLP.findVerb(sentence)  # list
        # print "Verbs: ", verb
        nounPhrase = NLP.findNounPhrase(sentence)
        # print "NPs: ", nounPhrase

        if NLP.dismissPreviousRequest(sentence):
            MongoHelper.pop_context(users, g.user)
            return "Sure, no problem"

        if contextData is not None and len(contextData) > 0:
            context = contextData[-1]

            # Find food functionality
            if context['context'] == 'findFood':
                if context['location'] == None and context['coordinates'] == None:
                    context['location'] = nounPhrase
                    location = {'type':'text','data': nounPhrase}
                    MongoHelper.update_context(users, g.user, 'findFood', 'location', nounPhrase)
                    MongoHelper.add_yelp_location_history(users, g.user, location)
                    FacebookAPI.send_message(app.config['PAT'], user_id, "Sure, give me a few seconds...")
                    result = Yelp.yelp_search(context['terms'], nounPhrase)
                    
                    if result['status'] == 1: # Successful search
                        FacebookAPI.send_message(app.config['PAT'], user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
                        FacebookAPI.send_yelp_results(app.config['PAT'], user_id, result['businesses'])
                        FacebookAPI.send_quick_replies_yelp(app.config['PAT'], user_id)
                    else:
                        MongoHelper.pop_context(users, g.user)
                        return "Sorry I can't find any places for that"
                        # Follow up
                    return
                else:
                    MongoHelper.pop_context(users, g.user)
                    return
                
        else:
            if NLP.isGreetings(incomingMessage):
                greeting = "%s %s"%(NLP.sayHiTimeZone(g.user), g.user['first_name'])
                FacebookAPI.send_message(app.config['PAT'], user_id, greeting)
                return "How can I help you?"

            if NLP.isGoodbye(incomingMessage):
                return NLP.sayByeTimeZone(g.user)

            if NLP.yelp(verb):                
                contextNow = {'context':'findFood', 
                              'location': None,
                              'coordinates': None,
                              'terms': nounPhrase
                              }
                MongoHelper.add_context(users, g.user, contextNow)
                return "Can you send me your whereabouts?"
                if NLP.nearBy(s[0]):
                    # https://fbnewsroomus.files.wordpress.com/2015/06/messenger-location-sharing1-copy.png?w=600&h=568
                    MongoHelper.add_context(users, g.user, contextNow)
                    return "Can you send me your whereabouts?"
                else:
                    # follow up to ask for location
                    return message['data']
            else:        
                return #"I'm sorry I can't process that"

    elif message['type'] == 'location':
        FacebookAPI.send_message(app.config['PAT'], user_id, "I've received location (%s,%s)"%(message['data'][0],message['data'][1]))

        if contextData is not None and len(contextData) > 0:
            context = contextData[-1]
            if context['context'] == 'findFood':
                location = {'type':'coordinates','data': message['data']}
                MongoHelper.update_context(users, g.user, 'findFood', 'coordinates', message['data'])
                MongoHelper.add_yelp_location_history(users, g.user, location)
                FacebookAPI.send_message(app.config['PAT'], user_id, "Looking looking... :D")

                result = Yelp.yelp_search(context['terms'], None, message['data'])
                if result['status'] == 1:
                    FacebookAPI.send_message(app.config['PAT'], user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
                    FacebookAPI.send_yelp_results(app.config['PAT'], user_id, result['businesses'])
                    FacebookAPI.send_quick_replies_yelp(app.config['PAT'], user_id)
                return

    elif message['type'] == 'audio':
        return "I've received audio %s"%(message['data'])

    elif message['type'] == 'quick_reply':
        context = contextData[-1]
        cmd = message['data']
        # cmd: [yelp-more, yelp-ok]
        if cmd == 'yelp-more':
            offset = g.user['yelp_offset'] + 5
            MongoHelper.increment_yelp_offset(users, g.user, 5) # actually update
            result = Yelp.yelp_search(context['terms'], context['location'], context['coordinates'], 5, offset)

            if result['status'] == 1: # Successful search
                FacebookAPI.send_message(app.config['PAT'], user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
                FacebookAPI.send_yelp_results(app.config['PAT'], user_id, result['businesses'])
                FacebookAPI.send_quick_replies_yelp(app.config['PAT'], user_id)
            else:
                MongoHelper.pop_context(users, g.user)
                MongoHelper.reset_yelp_offset(users, g.user)
                return "That's all I found for now :)"


        elif cmd == 'yelp-ok':
            MongoHelper.pop_context(users, g.user)
            MongoHelper.reset_yelp_offset(users, g.user)
            FacebookAPI.send_message(app.config['PAT'], user_id, "Glad I can help :)")

    else:
        MongoHelper.pop_context(users, g.user)
        MongoHelper.reset_yelp_offset(users, g.user)

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
            MongoHelper.log_message(log, sender_id, 'text', data)
            yield sender_id, {'type':'text', 'data': data}

        elif "attachments" in event["message"]:
            if "location" == event['message']['attachments'][0]["type"]:
                coordinates = event['message']['attachments'][
                    0]['payload']['coordinates']
                latitude = coordinates['lat']
                longitude = coordinates['long']

                MongoHelper.log_message(log, sender_id, 'coordinates', str([latitude, longitude]))
                yield sender_id, {'type':'location','data':[latitude, longitude]}

            elif "audio" == event['message']['attachments'][0]["type"]:
                audio_url = event['message'][
                    'attachments'][0]['payload']['url']
                MongoHelper.log_message(log, sender_id, 'audio', audio_url)
                yield sender_id, {'type':'audio','data': audio_url}
            else:
                MongoHelper.log_message(log, sender_id, 'other1', event["message"])
                yield sender_id, {'type':'other','data':"I can't echo this"}
        elif "quick_reply" in event["message"]:
            data = event["message"]["quick_reply"]["payload"]
            yield sender_id, {'type':'quick_reply','data': data}
        else:
            MongoHelper.log_message(log, sender_id, 'other2', event["message"])
            yield sender_id, {'type':'other','data':"I can't echo this"}

def get_user_from_message(payload):
    data = json.loads(payload)
    messaging_events = data["entry"][0]["messaging"][-1]
    return messaging_events["sender"]["id"]

def get_most_recent_locations_yelp(limit=3):
    locations = g.user['yelp_location_history']
    return locations[-5:] if len(locations) > limit else locations

# posts.update({"_id":5678},{"$set":{"from_user":"Alberto","source":"unavailable"}}, upsert=True)
# posts.find({"_id":5678}).count()
# posts.update({"_id":1234},{"$unset":{"total_posts":""}})
# posts.update({"_id":1234},{"$pop":{"sentiment":1}})
# posts.update({"_id":1234},{"$push":{"sentiment":{"nb":random.randint(-5, 5),"svm":random.randint(-5, 5)}}})
# posts.update({"_id":5678},{"$addToSet":{"skills":"python"}})  # adds a value to an array only if the value is not in the array already
# posts.update({"_id":5678},{"$pull":{"skills":"java"}}) # The pull operator removes all instances of a value from an existing array. 

# https://console.ng.bluemix.net/?direct=classic/#/resources/serviceGuid=be619d85-cc2a-42be-85d1-97e6468cf813&orgGuid=5e25a0af-ebbd-467d-94c8-fa82ad647f70&spaceGuid=cbeefcec-89d7-482a-83df-183b978ec969&paneId=1
# http://www.ibm.com/watson/developercloud/doc/speech-to-text/http.shtml

if __name__ == '__main__':
    if len(sys.argv) == 2:
        app.run(port=int(sys.argv[1]))
    else:
        app.run()