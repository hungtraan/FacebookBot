import sys, json, traceback
from Utils import FacebookAPI as FB, NLP, Mongo, simsimi
from Utils.Yelp import yelp_search_v3 as yelp_search
from Speech import processor as STT # Speech to Text
from flask import Flask, request, g, session, render_template, redirect, url_for, jsonify, flash
from flask_oauth import OAuth

from geopy.geocoders import Nominatim # https://github.com/geopy/geopy
from pattern.en import parsetree
from datetime import datetime, timedelta
from pymongo import MongoClient

application = Flask(__name__, instance_relative_config=True)
application.config.from_object('config')
application.config.from_pyfile('config.py', silent=True)

app = application

app.secret_key = 'super secret key'
mongo = MongoClient(app.config['MONGO_URI'])
db = mongo[app.config['MONGO_DBNAME']] # Get database
users = db.users # Get users collection
log = db.message_log # Get log collection
uncategorized_messages = db.uncategorized_messages
memos = db.memos

simSimi = simsimi.SimSimi(
        conversation_language='en',
        conversation_key=app.config['SIMSIMI_KEY']
)

# https://pythonhosted.org/Flask-OAuth/
oauth = OAuth()
facebook = oauth.remote_app('facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key=app.config['FACEBOOK_APP_ID'],
    consumer_secret=app.config['FACEBOOK_APP_SECRET'],
    request_token_params={'scope': 'email,public_profile'}
)

@app.before_request
def before_request():
    g.user = None
    # g.web_user = None
    # if 'logged_in' in session and session['logged_in']:
    #     data = facebook.get('/me').data
    #     if 'id' in data and 'name' in data:
    #         user_id = data['id']
            # g.web_user = Mongo.get_user_mongo(users, user_id)

@app.route('/tos', methods=['GET'])
def tos():
    return render_template('tos.html')

@app.route('/privacy', methods=['GET'])
def privacy():
    return render_template('privacy.html')

@app.route('/login')
def login():
    print url_for('oauth_authorized')
    return facebook.authorize(callback=url_for('oauth_authorized', _external=True,
        next=request.args.get('next') or request.referrer or None))

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    session.pop('fb_token', None)
    return redirect(url_for('memo'))

@app.route('/oauth-authorized')
@facebook.authorized_handler
def oauth_authorized(resp):
    next_url = request.args.get('next') or url_for('memo')
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)

    session['logged_in'] = True
    session['fb_token'] = (
        resp['access_token'],
        ''
    )
    data = facebook.get('/me').data
    if 'name' in data:
        user_name = data['name']

    flash('You are signed in as %s'%(user_name))
    return redirect(next_url)


@facebook.tokengetter
def get_fb_token(token=None):
    return session.get('fb_token')

@app.route('/hi', methods=['GET'])
def hi():
    return render_template('hi.html')

@app.route('/memo/<user_id>', methods=['GET'])
def memo(user_id):
    if 'logged_in' in session and session['logged_in']:
        data = facebook.get('/me').data
        if 'id' in data and 'name' in data:
            # user_id = data['id']
            user_name = data['name']
    else:
        user_name = None
    # if not g.web_user:
    #     return redirect(url_for('hi'))
    # user_name = g.web_user['first_name']
    memo_data = Mongo.get_memos_from_user(memos, user_id)
    print memo_data
    return render_template('memo.html', user_name=user_name, memo_data=memo_data)

@app.route('/', methods=['GET'])
def handle_verification():
    print "Handling Verification."
    if request.args.get('hub.verify_token', '') == 'baddest_ass_bot_you_know':
        print "Verification successful!"
        return request.args.get('hub.challenge', '')
    else:
        print "Verification failed!!!"
        return "There's nothing to look here ;)"


@app.route('/', methods=['POST'])
def handle_messages():
    # print "Handling Messages"
    payload = request.get_data()
    if app.config['PRINT_INCOMING_PAYLOAD']:
        print payload
    token = app.config['PAT']

    for sender, message in messaging_events(payload):
        if app.config['PRINT_INCOMING_MESSAGE']:
            print "User ID: %s\nMessage:%s" % (sender, message)
        try:
            FB.show_typing(token, sender)
            response = processIncoming(sender, message)
            FB.show_typing(token, sender, 'typing_off')

            if response is not None and response != 'pseudo':
                # 'pseudo' is an "ok" signal for functions that sends response on their own
                # without returning anything back this function
                FB.send_message(token, sender, response)

            elif response != 'pseudo':
                if NLP.randOneIn(7):
                    FB.send_message(token, sender, NLP.oneOf(NLP.no_response))
                    FB.send_picture(token, sender, 'https://monosnap.com/file/I6WEAs2xvpZ5qTNmVauNguEzcaRrnI.png')
        except Exception, e:
            print e
            traceback.print_exc()
            FB.send_message(app.config['PAT'], sender, NLP.oneOf(NLP.error))
            Mongo.pop_context(users, g.user)
            if NLP.randOneIn(7):
                FB.send_picture(app.config['PAT'], sender, 'https://monosnap.com/file/3DnnKT60TkUhF93dwjGbNQCaCUK9WH.png')
    return "ok"

temp_audio_url = ""

def processIncoming(user_id, message, just_text=False):
    # First time user
    if not Mongo.user_exists(users, user_id):
        g.user = Mongo.get_user_mongo(users, user_id)
        return handle_first_time_user(users, g.user)
    else:
        g.user = Mongo.get_user_mongo(users, user_id)

    last_seen = datetime.strptime(g.user['last_seen'],"%Y-%m-%d %H:%M:%S")
    recent5min = datetime.now() - timedelta(minutes=5)

    if last_seen < recent5min:
        Mongo.update_last_seen(users, g.user)

    contextData = g.user['contexts']

    # Text message type =========================================================
    if just_text or message['type'] == 'text':
        # just_text is transcribe audio
        message_text = message if just_text else message['data']

        if dev_area(message_text): # go through development codes
            return 'pseudo'

        if message_text.lower() == "help":
            handle_help(user_id)
            return 'pseudo'
        
        if message_text[-1] != ".": # help separate sentence for parsetree
            dotted_message = message_text + "."
        s = parsetree(dotted_message, relations=True, lemmata=True)
        sentence = s[0]
        nounPhrase = NLP.findNounPhrase(sentence)

        if NLP.dismissPreviousRequest(sentence):
            Mongo.pop_context(users, g.user)
            return "Sure, no problem"

        if contextData is not None and len(contextData) > 0:
            context = contextData[-1]

            # Find food functionality
            if context['context'] == 'find-food':
                return handle_find_food(user_id, context, sentence, nounPhrase, message, message_text, 'receive_location_text')
            
            elif context['context'] == 'yelp-rename':
                handle_yelp_rename(user_id, g.user, context, message_text)
                Mongo.pop_context(users, g.user) # pop yelp-rename
                return "Ta da! %s is now in my cloudy memory :D"%(message_text)

            elif context['context'] == 'create-memo':
                return handle_memo(user_id, message_text)
    
        else:
            if NLP.isGreetings(message_text):
                greeting = "%s %s :D"%(NLP.sayHiTimeZone(g.user), g.user['first_name'])
                FB.send_message(app.config['PAT'], user_id, greeting)
                return "How can I help you?"

            elif NLP.isGoodbye(message_text):
                return NLP.sayByeTimeZone(g.user)

            elif NLP.isYelp(sentence):                
                return handle_find_food(user_id, None, sentence, nounPhrase, message, message_text, 'receive_request')

            elif NLP.isMemoCommandOnly(message_text):
                data = { 'context': 'create-memo' }
                Mongo.add_context(users, g.user, data)
                return "I'm listening, go ahead :D"

            elif NLP.isMemo(message_text):
                content = NLP.get_memo_content(message_text)
                return handle_memo(user_id, content)

            else:
                # Log this message for categorization later
                Mongo.log_message(uncategorized_messages, user_id, "text", message_text)
                try:
                    response = simSimi.getConversation(message_text)['response']
                    bad_times = 0
                    while NLP.badWords(response):
                        bad_times += 1
                        print response
                        response = simSimi.getConversation(message_text)['response']
                        if bad_times == 5:
                            return "Hmm... I can't think of anything witty enough to respond to that :P"
                    if 'simsimi' in response:
                        response = response.replace("simsimi", "Optimist Prime")
                    return response
                except simsimi.SimSimiException as e:
                    print e
                    return
    # ==/ END Text message type =====================================================

    # Location message type =========================================================
    elif message['type'] == 'location':
        FB.send_message(app.config['PAT'], user_id, "I've received location (%s,%s) (y)"%(message['data'][0],message['data'][1]))

        if contextData is not None and len(contextData) > 0:
            context = contextData[-1]
            if 'context' in context and context['context'] == 'find-food':
                return handle_find_food(user_id, context, None, None, message, None, 'receive_location_gps')
        else:
            return 'pseudo'
    # ==/ END Location message type ==================================================

    # Audio message type =========================================================
    elif message['type'] == 'audio':
        audio_url = message['data']

        # Handle Facebook bug when receiving long audio
        # The bug: The app keeps receiving the same POST request
        # This acts as a rescue exit signal
        global temp_audio_url 
        if audio_url == temp_audio_url:
            return 'pseudo'
        temp_audio_url = audio_url

        # Get text from audio
        try:
            message_text = STT.transcribe(audio_url)
            if message_text == "" or message_text == None:
                return
            # if 'DISPLAY_STT_RESULT' in os.environ and os.environ['DISPLAY_STT_RESULT'] != 0:
            print message_text
        except Exception, e:
            message_text = "Sorry I can't process that now :("
            FB.send_message(app.config['PAT'], user_id, message_text)
            print e
            return

        # Begin processing audio command
        message_text = message_text.decode('utf-8')
        return processIncoming(user_id, message_text, True)
    # ==/ End Audio message type ====================================================


    # Quick Reply message type ======================================================
    elif message['type'] == 'quick_reply':
        context = contextData[-1]
        cmd = message['data']
        
        return handle_quick_reply(user_id, context, cmd)
    # ==/ END Quick Reply message type ==================================================


    else:
        Mongo.pop_context(users, g.user)
        Mongo.reset_yelp_offset(users, g.user)

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
            Mongo.log_message(log, sender_id, 'text', data)
            yield sender_id, {'type':'text', 'data': data}

        elif "attachments" in event["message"]:
            if "location" == event['message']['attachments'][0]["type"]:
                coordinates = event['message']['attachments'][
                    0]['payload']['coordinates']
                latitude = coordinates['lat']
                longitude = coordinates['long']

                Mongo.log_message(log, sender_id, 'coordinates', str([latitude, longitude]))

                yield sender_id, {'type':'location','data':[latitude, longitude]}

            elif "audio" == event['message']['attachments'][0]["type"]:
                audio_url = event['message'][
                    'attachments'][0]['payload']['url']
                Mongo.log_message(log, sender_id, 'audio', audio_url)
                yield sender_id, {'type':'audio','data': audio_url}
            
            else:
                Mongo.log_message(log, sender_id, 'other1', event["message"])
                yield sender_id, {'type':'other','data':"I can't echo this"}
        elif "quick_reply" in event["message"]:
            data = event["message"]["quick_reply"]["payload"]
            yield sender_id, {'type':'quick_reply','data': data}
        else:
            Mongo.log_message(log, sender_id, 'other2', event["message"])
            yield sender_id, {'type':'other','data':"I can't echo this"}

def get_user_from_message(payload):
    data = json.loads(payload)
    messaging_events = data["entry"][0]["messaging"][-1]
    return messaging_events["sender"]["id"]

def get_recent_locations_yelp(idx=None):
    # Locations acts like a stack
    locations = g.user['yelp_location_history']
    if idx is not None:
        return locations[len(locations)-1-idx]
    locations = locations[-5:] if len(locations) > 5 else locations
    locations_newest_first = []
    for place in locations:
        locations_newest_first.insert(0, place)

    return locations_newest_first

def handle_find_food(user_id, context, sentence, nounPhrase, message, incomingMessage, stage, location_from_memory=0):
    
    if stage == 'receive_request':
        # "Stage 1"
        contextNow = {'context':'find-food', 
                      'location': None,
                      'coordinates': None,
                      'terms': nounPhrase,
                      'location_from_memory': location_from_memory
                      }
        Mongo.add_context(users, g.user, contextNow)
        FB.send_message(app.config['PAT'], user_id, "Can you send me your location? :D")
        if len(g.user['yelp_location_history']) > 0:
            FB.send_quick_replies_yelp_suggest_location(app.config['PAT'], user_id, get_recent_locations_yelp())
        return 'pseudo'
        
    elif stage == 'receive_location_gps':
        # "Stage 2-GPS"
        if location_from_memory == 1:
            Mongo.update_context(users, g.user, 'find-food', 'location_from_memory', 1)

        location = message['data']
        Mongo.update_context(users, g.user, 'find-food', 'coordinates', location)
        FB.send_message(app.config['PAT'], user_id, NLP.oneOf(NLP.looking_replies))
        FB.show_typing(app.config['PAT'], user_id)     

        result = yelp_search(context['terms'], None, location)
        FB.show_typing(app.config['PAT'], user_id, 'typing_off')

        if result['status'] == 1:
            FB.send_message(app.config['PAT'], user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
            FB.send_yelp_results(app.config['PAT'], user_id, result['businesses'])
            FB.send_quick_replies_yelp_search(app.config['PAT'], user_id)
            return 'pseudo'
        else:    
            return "Sorry I couldn't find anything :("

    elif stage == 'receive_location_text':
        # "Stage 2 - Text"

        if context['location'] == None and context['coordinates'] == None:
            context['location'] = nounPhrase
            try:
                geolocator = Nominatim()
                location_lookup = geolocator.geocode(nounPhrase)
                coords = [location_lookup.latitude, location_lookup.longitude]
                Mongo.update_context(users, g.user, 'find-food', 'coordinates', coords)
                Mongo.update_context(users, g.user, 'find-food', 'location', nounPhrase)
                FB.show_typing(app.config['PAT'], user_id)
                FB.send_message(app.config['PAT'], user_id, NLP.oneOf(NLP.looking_replies))
                result = yelp_search(context['terms'], None, coords)

            except Exception, e:
                print e
                Mongo.update_context(users, g.user, 'find-food', 'location', nounPhrase)
                FB.send_message(app.config['PAT'], user_id, NLP.oneOf(NLP.looking_replies))
                result = yelp_search(context['terms'], nounPhrase)
            
            FB.show_typing(app.config['PAT'], user_id, 'typing_off')
            if result['status'] == 1: # Successful search
                FB.send_message(app.config['PAT'], user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
                FB.send_yelp_results(app.config['PAT'], user_id, result['businesses'])
                FB.send_quick_replies_yelp_search(app.config['PAT'], user_id)
                return 'pseudo'
            else:
                Mongo.pop_context(users, g.user)
                return "Sorry I can't find any results for that :("
                # Follow up?
        else:
            Mongo.pop_context(users, g.user)
            return

def handle_yelp_rename(user_id, user, context, name):
    Mongo.add_yelp_location_history(users, user, context['coordinates'], name)

def handle_memo(user_id, message_text):
    if len(message_text.split(" ")) > 10:
        Mongo.add_memo(memos, g.user, message_text)
        url = url_for("memo", user_id=user_id, _external=True)
        FB.send_url(app.config['PAT'], user_id, "I've saved it for you :D", "View Memos", url)
    Mongo.pop_context(users, g.user)
    return 'pseudo'

def handle_quick_reply(user_id, context, cmd):
    # cmd: [yelp-more, yelp-ok]
    if cmd == 'yelp-more-yes':
        offset = g.user['yelp_offset'] + 5
        Mongo.increment_yelp_offset(users, g.user, 5) # actually update
        result = yelp_search(context['terms'], context['location'], context['coordinates'], 5, offset)

        if result['status'] == 1: # Successful search
            FB.send_message(app.config['PAT'], user_id, "Okay, I've found %s places:"%(len(result['businesses'])))
            FB.send_yelp_results(app.config['PAT'], user_id, result['businesses'])
            FB.send_quick_replies_yelp_search(app.config['PAT'], user_id)
            return 'pseudo'
        else:
            Mongo.pop_context(users, g.user)
            Mongo.reset_yelp_offset(users, g.user)
            return "That's all I found for now :)"

    elif cmd == 'yelp-more-no':
        context = g.user['contexts'][-1]
        Mongo.reset_yelp_offset(users, g.user)

        if context['location_from_memory'] == 1:
            Mongo.pop_context(users, g.user)
            return "Glad I can help :)"

        if context['context'] == 'find-food' and context['location'] is not None and context['coordinates'] is not None:
            latest_location = context['location']
            FB.send_quick_replies_yelp_save_location(app.config['PAT'], user_id, latest_location)
            return 'pseudo'

        elif context['context'] == 'find-food' and context['coordinates'] is not None and context['location'] is None:
            # Suggest saving this location
            FB.send_quick_replies_yelp_save_location(app.config['PAT'], user_id)
            return 'pseudo'

        else:
            Mongo.pop_context(users, g.user)
            return "Glad I can help :)"
    
    elif cmd == 'yelp-save-location-yes':
        context = g.user['contexts'][-1]
        latest_coords = context['coordinates']
        latest_location = context['location']
        
        if context['location'] == None: # A search with only coordinates
            contextNow = {'context':'yelp-rename',
                  'name': 'untitled',
                  'coordinates': latest_coords,
                  }
            Mongo.pop_context(users, g.user) # pop find-food context
            Mongo.add_context(users, g.user, contextNow)
            return "What do you want to call it? :D"

        else:
            Mongo.add_yelp_location_history(users, g.user, latest_coords, latest_location)
            Mongo.pop_context(users, g.user)
            Mongo.reset_yelp_offset(users, g.user)
            return "Ta da! I wrote it to my cloudy memory :D"

    elif cmd == 'yelp-save-location-no':
        Mongo.pop_context(users, g.user)
        Mongo.reset_yelp_offset(users, g.user)
        return "OK (y) Hope you like those places I found :D"
    
    elif cmd == 'yelp-save-location-rename':
        context = g.user['contexts'][-1]
        latest_location = context['location']
        latest_coords = context['coordinates']
        contextNow = {'context':'yelp-rename', 
                  'name': latest_location,
                  'coordinates': latest_coords,
                  }
        Mongo.pop_context(users, g.user) # pop find-food context
        Mongo.add_context(users, g.user, contextNow)
        return "What do you want to call it? :D"

    elif 'yelp-cached-location-' in cmd:
        idx = int(cmd[-1])
        location = get_recent_locations_yelp(idx)
        FB.send_message(app.config['PAT'], user_id, "Looking around %s :D"%(location['name']))
        message = {}
        message['data'] = location['coordinates']
        return handle_find_food(user_id, context, None, None, message, None, 'receive_location_gps', 1)

def handle_first_time_user(users, user):
    user_id = user['user_id']
    token = app.config['PAT']

    hi = "%s %s, nice to meet you :)"%(NLP.sayHiTimeZone(user), user['first_name'])
    FB.send_message(token, user_id, hi)
    FB.send_picture(app.config['PAT'], user_id, 'https://monosnap.com/file/I6WEAs2xvpZ5qTNmVauNguEzcaRrnI.png')
    
    handle_help(user_id)

def handle_help(user_id):
    token = app.config['PAT']

    FB.send_message(token, user_id, "You can both chat and speak to me, I understand voice and natural language (I try to be smarter everyday :D)")
    FB.send_picture(token, user_id, 'https://monosnap.com/file/fxDiSsKwBo6HvZv0EFLhYqATAQ5eou.png', "How to speak to me")
    FB.send_message(token, user_id, "You can also tell me to find you any restaurant/shop by saying something like \"Find me a Italian restaurant\"")
    FB.send_intro_screenshots(token, user_id, 'yelp')

    FB.send_message(token, user_id, "Lastly, I can keep your memos for you on the cloud, you only need to chat or speak to me something like \"Memorize\" or \"Memorize this for me: The long memo (in the same recording)\"")
    FB.send_intro_screenshots(token, user_id, 'memo')



def dev_area(message_text):
    return False

if __name__ == '__main__':
    if len(sys.argv) == 2:
        app.run(port=int(sys.argv[1]))
    else:
        app.run()