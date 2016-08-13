import requests, json
from flask import url_for

def get_user_fb(token, user_id):
    r = requests.get("https://graph.facebook.com/v2.6/" + user_id,
                    params={"fields": "first_name,last_name,profile_pic,locale,timezone,gender"
                        ,"access_token": token
                    })
    if r.status_code != requests.codes.ok:
        print r.text
        return
    user = json.loads(r.content)
    return user

def show_typing(token, user_id, action='typing_on'):
  r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                          "recipient": {"id": user_id},
                          "sender_action": action
                      }),
                      headers={'Content-type': 'application/json'})
  if r.status_code != requests.codes.ok:
        print r.text

def send_message(token, user_id, text):
    """Send the message text to recipient with id recipient.
    """
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                          "recipient": {"id": user_id},
                          "message": {"text": text.decode('unicode_escape')}
                      }),
                      headers={'Content-type': 'application/json'})
    if r.status_code != requests.codes.ok:
        print r.text

def send_picture(token, user_id, imageUrl, title="", subtitle=""):
    if title != "":
        data = {"recipient": {"id": user_id},
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
              }
    else:
        data = { "recipient": {"id": user_id},
                "message":{
                  "attachment": {
                      "type": "image",
                      "payload": {
                          "url": imageUrl
                      }
                  }
                }
            }
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps(data),
                      headers={'Content-type': 'application/json'})
    if r.status_code != requests.codes.ok:
        print r.text    

def send_quick_replies_yelp_search(token, user_id):
    # options = [Object {name:value, url:value}, Object {name:value, url:value}]
    quickRepliesOptions = [
        {"content_type":"text",
         "title": "Get more suggestions",
         "payload": 'yelp-more-yes'
        },
        {"content_type":"text",
         "title": "That's good for me",
         "payload": 'yelp-more-no'
        }
    ]
    data = json.dumps({
            "recipient":{ "id": user_id },
            "message":{
                "text":"Do you want to find more results? :D",
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

def send_quick_replies_yelp_save_location(token, user_id, location=None):
    # options = [Object {name:value, url:value}, Object {name:value, url:value}]
    quickRepliesOptions = [
        {"content_type":"text",
         "title": "Sure",
         "payload": 'yelp-save-location-yes'
        }]
    if location != None: # Place this here to make sure this option comes second
        rename = {"content_type":"text",
         "title": "I'll rename it",
         "payload": 'yelp-save-location-rename'
        }
        quickRepliesOptions.append(rename)
    no = {"content_type":"text",
         "title": "No, thank you",
         "payload": 'yelp-save-location-no'
        }
    quickRepliesOptions.append(no)
    
    if location == None:
        message = "Do you want me to save this location?"
    else:
        message = "Do you want me to save this location as \"%s\" for the future? :D"%(location)
    data = json.dumps({
            "recipient":{ "id": user_id },
            "message":{
                "text": message,
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

def send_quick_replies_yelp_suggest_location(token, user_id, locations):
    quickRepliesOptions = []
    i = 0
    for location in locations:
        location_name = location['name'][:17] + "..." if len(location['name']) > 20 else location['name']

        obj = {"content_type":"text",
         "title": location_name,
         "payload": 'yelp-cached-location-%s'%(i)
        }
        quickRepliesOptions.append(obj)
        i += 1
    
    data = json.dumps({
            "recipient":{ "id": user_id },
            "message":{
                "text":"Or choose one of the saved locations :D",
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

def send_yelp_results(token, user_id, businesses):
    options = []

    for business in businesses:
        subtitle = ""
        if 'price' in business and business['price'] != "":
            subtitle += business['price'] + " - "
        subtitle += business['address'] 
        if 'distance' in business:
            subtitle += " (" + str(business['distance']) + " mi.)"
        if 'is_open_now' in business:
            subtitle += "\n" + "Open now - " if business['is_open_now'] else "\n" 
        if 'hours_today' in business and len(business['hours_today']) > 0:
            subtitle += "Hours today: %s"%(business['hours_today'])
        subtitle += "\n" + business['categories']

        img_url = business['image_url'] if business['image_url'] != "" else url_for('static', filename='assets/img/empty-placeholder.jpg', _external=True)
        
        obj = {
                "title": business['name'] + " - " + business['rating'] ,
                "image_url": img_url,
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
                            "recipient": {"id": user_id},
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

def send_url(token, user_id, text, title, url):
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                            "recipient": {"id": user_id},
                            "message":{
                                "attachment":{
                                    "type":"template",
                                    "payload":{
                                        "template_type":"button",
                                        "text": text,
                                        "buttons":[
                                            {
                                            "type":"web_url",
                                            "url": url,
                                            "title": title
                                            }
                                        ]
                                    }
                                }
                            }
                      }),
                      headers={'Content-type': 'application/json'})
    if r.status_code != requests.codes.ok:
        print r.text

def send_intro_screenshots(app, token, user_id):
    chat_speak = {
        "title": 'You can both chat and speak to me',
        "image_url": url_for('static', filename="assets/img/intro/1-voice-and-text.jpg", _external=True),
        "subtitle": 'I understand voice and natural language (I try to be smarter everyday :D)'
    }
    location_text = {
        "title": "Find a restaurant/shop for you",
        "image_url": url_for('static', filename="assets/img/intro/2-yelp-gps-location.jpg", _external=True),
        "subtitle": "Tell me what you want, then your location name, address or GPS"
    }
    location_gps = {
        "title": "In case you've never sent location in Messenger",
        "image_url": url_for('static', filename="assets/img/intro/3-how-to-send-location.jpg", _external=True),
        "subtitle": "GPS will be the best option, but just a distinctive name would do",
    }
    location_save = {
        "title": "Save your favorite locations",
        "image_url": url_for('static', filename="assets/img/intro/4-save-location.jpg", _external=True),
        "subtitle": "Make it convenient for you"
    }
    memo1 = {
        "title": "Say \"Memorize\" or \"Memorize this for me\"",
        "image_url": url_for('static', filename="assets/img/intro/5-memo.jpg", _external=True),
        "subtitle": "Then your memo in the same/separate message"
    }
    news = {
      "title": "Keep you updated",
      "image_url": url_for('static', filename="assets/img/intro/6-news.jpg", _external=True),
      "subtitle": "With the most trending news"
    }

    options = [chat_speak, location_text, location_gps, location_save, memo1, news]

    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
          params={"access_token": token},
          data=json.dumps({
                "recipient": {"id": user_id},
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

def send_trending_news(token, user_id, posts):
    options = []
    for post in posts:
        img_url = post['image_url'] if post['image_url'] != "" else url_for('static', filename='assets/img/empty-placeholder.jpg', _external=True)
        obj = {
            "title": post['title'],
            "image_url": img_url,
            "subtitle": post['subtitle'],
            "buttons":[
                {
                "type":"web_url",
                "url": post['url'],
                "title":"Read more"
                }
            ]
        }
        options.append(obj) 
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                            "recipient": {"id": user_id},
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


def set_menu():
    r = requests.post("https://graph.facebook.com/v2.6/me/thread_settings",
                    params={"access_token": 'EAADhYj0lr14BAGP2HCx2mcYcxQbtQG7iXfaGpOieFsGlgJEYv0Y74bdIYtQ3UcnK1kktfUCDInciDniwTOm1c6l2Fq2GEBsm0Lu4syz5HUc41MGepASZBuXw1caZBkZBGRX5kIZCT7q5QOkiPVnZC3n8iBcqVMCBGnZCiSgscQogZDZD'},
                    data=json.dumps({
                        "setting_type" : "call_to_actions",
                        "thread_state" : "existing_thread",
                        "call_to_actions":[
                            {
                                "type":"postback",
                                "title":"What can you do?",
                                "payload":"OPTIMIST_HELP"
                            },
                            {
                                "type":"web_url",
                                "title":"View Facebook Page",
                                "url": "https://www.facebook.com/optimistPrimeBot/"
                            }
                        ]
                    }),
                    headers={'Content-type': 'application/json'})
    print r.content
    if r.status_code != requests.codes.ok:
        print r.text

def set_get_started_button():

    r = requests.post("https://graph.facebook.com/v2.6/me/thread_settings",
                    params={"access_token": 'EAADhYj0lr14BAGP2HCx2mcYcxQbtQG7iXfaGpOieFsGlgJEYv0Y74bdIYtQ3UcnK1kktfUCDInciDniwTOm1c6l2Fq2GEBsm0Lu4syz5HUc41MGepASZBuXw1caZBkZBGRX5kIZCT7q5QOkiPVnZC3n8iBcqVMCBGnZCiSgscQogZDZD'},
                    data=json.dumps({
                        "setting_type":"call_to_actions",
                        "thread_state":"new_thread",
                        "call_to_actions":[
                            {
                            "payload":"OPTIMIST_GET_STARTED"
                            }
                        ]
                    }),
                    headers={'Content-type': 'application/json'})
    print r.content
    if r.status_code != requests.codes.ok:
        print r.text

# set_menu()
# set_get_started_button()