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
        user_fb = get_user_fb(PAT, user_id)
        create_user_mongo(user_id, user_fb)
        return False
    return True

# Has to use user_id since user has not existed
def create_user_mongo(users, user_id, user_fb):
    timestamp = datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S")
    user_insert = {'user_id': user_id, 
                    'last_seen': timestamp,
                    'first_name':user_fb['first_name'],
                    'last_name':user_fb['last_name'],
                    'gender': user_fb['gender'],
                    'timezone':user_fb['timezone'],
                    'contexts':[],
                    'yelp_location_history':[]}
    users.insert(user_insert)

# Input: Facebook's user_id
def get_user_mongo(users, user_id):
    return users.find_one({'user_id': user_id})

def update_last_seen(users, user, timestamp):
    users.update({"user_id": user['user_id']},{"$set":{"last_seen": timestamp}})

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

def update_context(users, user, find_by, context_to_update, content):
    users.update({'_id': user['_id'], "contexts.context": find_by},
        { "$set": { "contexts.$.%s"%(context_to_update) : content } })
    
def pop_context(users, user):
    users.update({'_id': user['_id']}, {"$pop":{"contexts":1}})
    
def add_yelp_location_history(users, user_id, location):
    users.update({'user_id': user_id}, {"$addToSet":{"yelp_location_history": location}})
    
def log_message(log, sender, mes_type, message):
    now = datetime.now()
    timeStr = datetime.strftime(now,"%Y-%m-%d %H:%M:%S")
    log.insert_one({"sender":sender, "type": mes_type, "message":message, "timestamp": timeStr })