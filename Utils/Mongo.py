from bson.objectid import ObjectId
from FacebookAPI import get_user_fb
from datetime import datetime
from config import PAT

def find_user_id(users, user_object_id):
    # Convert from string to ObjectId:
    return users.find_one({'_id': ObjectId(user_object_id)})

# Has to use user_id since user might not exist
def user_exists(users, user_id):
    user = users.find_one({'user_id': user_id})
    if user is None:
        print user_id
        user_fb = get_user_fb(PAT, user_id)
        create_user(users, user_id, user_fb)
        return False
    return True

# Has to use user_id since user has not existed
def create_user(users, user_id, user_fb):
    timestamp = datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S")
    user_insert = {'user_id': user_id, 
                    'created_at': timestamp,
                    'last_seen': "1970-01-01 00:00:00",
                    'first_name':user_fb['first_name'],
                    'last_name':user_fb['last_name'],
                    'gender': user_fb['gender'],
                    'timezone':user_fb['timezone'],
                    'contexts':[],
                    'yelp_location_history':[],
                    'yelp_offset': 0,
                    'first_time_using': {
                        'yelp': 1,
                        'audio': 1,
                        'gps': 1
                    }
                }
    users.insert(user_insert)

# Input: Facebook's user_id
def get_user_mongo(users, user_id):
    return users.find_one({'user_id': user_id})

# ======= Generic update =========
def set_attribute(users, user, attribute, content, upsert=False):
    users.update({'_id': user['_id']},{"$set":{ attribute: content}}, upsert=upsert)
# ======= END Generic update =========

def update_last_seen(users, user):
    now = datetime.now()
    timestamp = datetime.strftime(now,"%Y-%m-%d %H:%M:%S")
    users.update({"user_id": user['user_id']},{"$set":{"last_seen": timestamp}})

def update_first_time(users, user, first_time_name):
    users.update({'_id': user['_id']},{"$set":{"first_time_using." + first_time_name: 0}})

def first_time_using(users, user, first_time_name):
    tried = users.find_one({'_id': user['_id']},{"first_time_using." + first_time_name: 1})['first_time_using']
    if tried:
        return False
    else:
        update_first_time(users, user, first_time_name)
        return True

def get_contexts(users, user):
    user = users.find_one({user['_id']})['contexts']
    
def add_context(users, user, context):
    users.update({'_id': user['_id']}, {"$push":{"contexts": context}})

def increment_yelp_offset(users, user, offset):
    users.update({'_id': user['_id']},{"$inc":{"yelp_offset": offset}})
    return offset # return value to update object
    # original update: g.user = get_user_mongo(user_id)

def reset_yelp_offset(users, user):
    users.update({'_id': user['_id']},{"$set":{"yelp_offset": 0}})

def update_context(users, user, context_name, content_to_update, content):
    users.update({'_id': user['_id'], "contexts.context": context_name},
        { "$set": { "contexts.$.%s"%(content_to_update) : content } })
    
def pop_context(users, user):
    users.update({'_id': user['_id']}, {"$pop":{"contexts":1}})
    
def add_yelp_location_history(users, user, location, location_name=""):
    data = {"name": location_name, "coordinates": location}
    users.update({'_id': user['_id']}, {"$addToSet":{"yelp_location_history": data}})

def log_message(log, sender, mes_type, message):
    now = datetime.now()
    timeStr = datetime.strftime(now,"%Y-%m-%d %H:%M:%S")
    log.insert_one({"sender":sender, "type": mes_type, 
        "message":message, "timestamp": timeStr })

def add_memo(memos, user, text, title=None):
    timestamp = datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S")
    if title == None:
        title = datetime.strftime(datetime.now(),"%b %d, %Y %H:%M")
    memo = {
            'user_object_id': user['_id'],
            'user_id': user['user_id'],
            'created_at': timestamp,
            'title': title,
            'edited': 0,
            'content': text,
            }
    memos.insert(memo)

def get_memos_from_user(memos, user_id):
    memo = memos.find( {"$query":{'user_id': user_id}, "$orderby": { "created_at" : -1 }})
    return memo