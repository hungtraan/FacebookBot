import requests
import json

def get_user_fb(token, user_id):
    r = requests.get("https://graph.facebook.com/v2.6/" + user_id,
                      params={"fields": "first_name,last_name,profile_pic,locale,timezone,gender"
                      ,"access_token": token
                      })
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
        obj = {
                "title": business['name'] + " - " + business['rating'] ,
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

def send_intro_screenshots(token, user_id, feature):

    if feature == 'yelp':
        location_text = {
            "title": "Tell me the name of the location",
            "image_url": "https://monosnap.com/file/1zh6Wt1C7Bt2sqOP7wly8cXZQbmLAT.png",
            "subtitle": "Find a restaurant/shop for you",
        }
        location_gps = {
            "title": "Send me the GPS information",
            "image_url": "https://monosnap.com/file/SFQWVXrRSEof5DuhCohUcOqgd3yv28.png",
            "subtitle": "Find a restaurant/shop for you",
        }
        location_save = {
            "title": "I can also save your favorite locations",
            "image_url": "https://monosnap.com/file/oCUr8Cz7hwijK3EcuisdBAAFvJd79a.png",
            "subtitle": "Find a restaurant/shop for you",
        }
        options = [location_text, location_gps, location_save]

    elif feature == 'memo':
        memo1 = {
            "title": "Keeping your memos",
            "image_url": "https://monosnap.com/file/aUQoBEpgmy6aPET9S6bb3j6CS8eLep.png",
            "subtitle": "Say \"memorize\", followed by your memo in the same or separate message",
        }
        options = [memo1]

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
        obj = {
            "title": post['title'],
            "image_url": post['image_url'],
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
