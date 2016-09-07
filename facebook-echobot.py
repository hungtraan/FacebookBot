"""
Simple Facebook Echo bot: Respond with exactly what it receives
"""

import sys, json, traceback
from Utils import FacebookAPI as FB, NLP

from flask import Flask, request

application = Flask(__name__)
application.config.from_object('config')
application.config.from_pyfile('config.py', silent=True)  # Config for local development is found at: instance/config.py. This will overwrite configs in the previous line. The instance folder is ignored in .gitignore, so it won't be deployed to Heroku, in effect applying the production configs.

app = application

@app.route('/', methods=['GET'])
def handle_verification():
    print "Handling Verification."
    if request.args.get('hub.verify_token', '') == 'your_own_token':
        print "Webhook verified!"
        return request.args.get('hub.challenge', '')
    else:
        print "Wrong verification token!"

# ======================= Bot processing ===========================

@app.route('/', methods=['POST'])
def handle_messages():
    payload = request.get_data()

    token = app.config['PAT']

    webhook_type = get_type_from_payload(payload)

    # Handle messages
    if webhook_type == 'message':
        for sender_id, message in messaging_events(payload):
            # Only process message in here
            if not message:
                return "ok"

            # Start processing valid requests
            try:
                FB.show_typing(token, sender_id)
                response = processIncoming(sender_id, message)
                FB.show_typing(token, sender_id, 'typing_off')

                if response is not None and response != 'pseudo':
                    # 'pseudo' is an "ok" signal for functions that sends response on their own
                    # without returning anything back this function
                    print response
                    FB.send_message(token, sender_id, response)

                elif response != 'pseudo':
                    FB.send_message(token, sender_id, "Sorry I don't understand that")
            except Exception, e:
                print e
                traceback.print_exc()
                FB.send_message(app.config['PAT'], sender_id, NLP.oneOf(NLP.error))
    return "ok"

def processIncoming(user_id, message):
    if message['type'] == 'text':
        message_text = message['data']
        return message_text
    # ==/ END Text message type =====================================================

    # Location message type =========================================================
    elif message['type'] == 'location':
        response = "I've received location (%s,%s) (y)"%(message['data'][0],message['data'][1])
        return response

    # ==/ END Location message type ==================================================

    # Audio message type =========================================================
    elif message['type'] == 'audio':
        audio_url = message['data']
        return "I've received %s"%(audio_url)

    # ==/ End Audio message type ====================================================

    # Unrecognizable incoming, remove context and reset all data to start afresh
    else:
        return "*scratch my head*"


# Get type of webhook
# Current support: message, postback
# Reference: https://developers.facebook.com/docs/messenger-platform/webhook-reference/message-received
def get_type_from_payload(payload):
    data = json.loads(payload)
    if "postback" in data["entry"][0]["messaging"][0]:
        return "postback"

    elif "message" in data["entry"][0]["messaging"][0]:
        return "message"

def postback_events(payload):
    data = json.loads(payload)
    
    postbacks = data["entry"][0]["messaging"]
    
    for event in postbacks:
        sender_id = event["sender"]["id"]
        postback_payload = event["postback"]["payload"]
        yield sender_id, postback_payload

# Generate tuples of (sender_id, message_text) from the provided payload.
# This part technically clean up received data to pass only meaningful data to processIncoming() function
def messaging_events(payload):
    
    data = json.loads(payload)
    
    messaging_events = data["entry"][0]["messaging"]
    
    for event in messaging_events:
        sender_id = event["sender"]["id"]

        # Not a message
        if "message" not in event:
            yield sender_id, None

        if "message" in event and "text" in event["message"] and "quick_reply" not in event["message"]:
            data = event["message"]["text"].encode('unicode_escape')
            yield sender_id, {'type':'text', 'data': data, 'message_id': event['message']['mid']}

        elif "attachments" in event["message"]:
            if "location" == event['message']['attachments'][0]["type"]:
                coordinates = event['message']['attachments'][
                    0]['payload']['coordinates']
                latitude = coordinates['lat']
                longitude = coordinates['long']

                yield sender_id, {'type':'location','data':[latitude, longitude],'message_id': event['message']['mid']}

            elif "audio" == event['message']['attachments'][0]["type"]:
                audio_url = event['message'][
                    'attachments'][0]['payload']['url']
                yield sender_id, {'type':'audio','data': audio_url, 'message_id': event['message']['mid']}
            
            else:
                yield sender_id, {'type':'text','data':"I don't understand this", 'message_id': event['message']['mid']}
        
        elif "quick_reply" in event["message"]:
            data = event["message"]["quick_reply"]["payload"]
            yield sender_id, {'type':'quick_reply','data': data, 'message_id': event['message']['mid']}
        
        else:
            yield sender_id, {'type':'text','data':"I don't understand this", 'message_id': event['message']['mid']}

# Allows running with simple `python <filename> <port>`
if __name__ == '__main__':
    if len(sys.argv) == 2: # Allow running on customized ports
        app.run(port=int(sys.argv[1]))
    else:
        app.run() # Default port 5000