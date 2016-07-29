import requests
import json

def get_user_fb(token, user_id):
    r = requests.get("https://graph.facebook.com/v2.6/" + user_id,
                      params={"fields": "first_name,last_name,profile_pic,locale,timezone,gender"
                      ,"access_token": token
                      })
    user = json.loads(r.content)
    return user

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

def send_quick_replies_yelp_save_location(token, user_id, location):
    # options = [Object {name:value, url:value}, Object {name:value, url:value}]
    quickRepliesOptions = [
        {"content_type":"text",
         "title": "Sure",
         "payload": 'yelp-save-location-yes'
        },
        {"content_type":"text",
         "title": "I'll rename it",
         "payload": 'yelp-save-location-rename'
        },
        {"content_type":"text",
         "title": "No, thank you",
         "payload": 'yelp-save-location-no'
        }
    ]
    data = json.dumps({
            "recipient":{ "id": user_id },
            "message":{
                "text":"Do you want me to save this location as \"%s\" for the future? :D"%(location),
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