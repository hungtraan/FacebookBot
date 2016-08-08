import time, string, random, re
from bad_words import BAD_WORDS
from datetime import datetime, timedelta
from pattern.en import parsetree, singularize
from pattern.search import search

# Random response sets
no_response = ["*scratch my head* :(", "How do I respond to that... :O", "I can be not-so-smart from time to time... :(", "Err... you know I'm not human, right? :O"]
error = ["Sorry I've got a little bit sick. BRB :(", "Oops... 404 My Witty Mind Not Found :O", "Oops... My brain went MIA in the cloud :(", "Hmm... How should I respond to that..."]
looking_replies = ["Sure, give me a few seconds... B-)", "Scanning the world... :D", "Zoom zoom zoom...", "Going into the Food Cerebro... B-)", "Believe me, I'm a foodie, not an engineer..."]
# END random response sets



def removePunctuation(inp_str):
    return inp_str.translate(None, string.punctuation)

def isGreetings(inp_str):
    string = inp_str.lower().split(" ")
    if len(string) > 5:
        return False
    greetings = ['hi','hey','hello', 'greetings', 'good morning', 'good afternoon', 'good evening']
    for word in greetings:
        if word in string[:3]:
            return True
    return False

def isGoodbye(inp_str):
    string = inp_str.lower().split(" ")
    byes = ['bye', 'see you']
    for word in byes:
        if word in string:
            return True
    return False

def isMemoCommandOnly(inp_str):
    s = inp_str.lower().split(" ")
    if s[0] in ['memorize','memorized'] and len(s) < 6:
        return True
    regEx = "(memorize)( this)?([\w\d ]{0,15}(?<!except)for me)?"
    command = re.search(regEx, inp_str)
    if command != None:
        remaining = inp_str.replace(command.group(0), "").strip()
        if remaining == "":
            return True
    return False

def isMemo(inp_str):
    regEx = "memorize( this)?([\w\d ]{0,15}(?<!except)for me)?"
    command = re.search(regEx, inp_str.lower())
    if command != None:
        return True
    return False

def get_memo_content(inp_str):
    regEx = "memorize( this)?([\w\d ]{0,15}(?<!except)for me)?"
    command = re.search(regEx, inp_str.lower())
    if command == None:
        return inp_str
    return inp_str.replace(command.group(0), "").strip() # strip trailing space

# input: g.user, i.e. mongodb user object
def sayHiTimeZone(user):
    user_now = getUserTime(user)
    if recentChat(user):
        response = ["Hi again", "Hey hey hey again", "What's up", "Hey there again"]
        if user_now.hour > 5 and user_now.hour < 12:
            response.extend(["Shiny day isn't it", "What a morning", "Morningggg"])
        elif user_now.hour < 19:
            response.extend(["How's your afternoon", "Afternoooooon", "What a day"])
        elif user_now.hour < 4 or user_now.hour > 22:
            response.extend(["Hmm... you're a night owl", "Long night hah", "You know, science has shown that sleeping early is good for you health", "The night is still young, I'm here"])
        else:
            response.extend(["Good evening", "What's rolling for dinner"])
        return oneOf(response)
    if user_now.hour > 5 and user_now.hour <= 12:
        return "Good morning"
    elif user_now.hour > 12 and user_now.hour < 19:
        return "Good afternoon"
    else:
        return "Good evening"

# input: g.user
def sayByeTimeZone(user):
    user_now = getUserTime(user)
    goodnights = ["Good night", "Have a good night", "Bye now", "See you later"]
    byes = ["Goodbye", "Bye then", "See you later", "Bye, have a good day"]
    
    if user_now.hour > 20:
        return "%s :)"%oneOf(goodnights)
    else:
        return "%s :)"%oneOf(byes)

# input: g.user
def recentChat(user):
    last_seen = user['last_seen'] 
    timestamp = datetime.strptime(last_seen,"%Y-%m-%d %H:%M:%S")
    time_since_chat = datetime.now() - timestamp
    recent60min = timedelta(minutes=60)
    if time_since_chat < recent60min:
        return True
    else:
        return False

# input: g.user
def getUserTime(user):
    user_tz = user['timezone']
    offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
    server_tz = offset / 60 / 60 * -1
    time_diff = user_tz - server_tz
    server_now = datetime.now()
    return server_now + timedelta(hours=time_diff)

# input: pattern.en sentence object
def findVerb(sentence):
    result = []
    for chunk in sentence.chunks:
        if chunk.type in ['VP']:
            strings = [w.string for w in chunk.words if w.type in ['VB','VBP']]
            result.extend(strings)
        # print chunk.type, [(w.string, w.type) for w in chunk.words ]
    return result

# input: pattern.en sentence object
def findNounPhrase(sentence):
    res = ""
    for chunk in sentence.chunks:
        if chunk.type == 'NP':
            res += " ".join([w.string for w in chunk.words if w.type not in ['PRP', 'DT']])
            res += " "
    return res

# input: pattern.en sentence object
def findProperNoun(sentence):
    for chunk in sentence.chunks:
        if chunk.type == 'NP':
            for w in chunk.words:
                if w.type == 'NNP':
                    return w.string
    return None

# input: pattern.en sentence object
def isYelp(sentence):
    verbs = findVerb(sentence)
    # If match key verbs
    yelpVerbs = ['eat', 'drink', 'find', 'display', 'get']
    for verb in verbs:
        if verb.lower() in yelpVerbs:
            noun_phrases = findNounPhrase(sentence)
            if "news" in noun_phrases or "information" in noun_phrases and "news stand" not in noun_phrases and "newsstand" not in noun_phrases:
                return False

            yelpNouns = ['restaurant', 'food', 'drink', 'shop', 'store', 'bar', 'pub']
            for noun in yelpNouns:
                if noun in noun_phrases:
                    return True

    # If match question/command structure
    # "is there" + noun phrase 
    if "is there" in sentence.string \
        or "are there" in sentence.string \
        and noun_phrases != "":
        return True
    # noun phrase + "near by"
    nearby = nearBy(sentence)
    if noun_phrases != "" and nearby:
        return True
    return False

# input: pattern.en sentence object, unless specified otherwise in inp_type
def dismissPreviousRequest(string, inp_type='sentence'):
    if inp_type == 'sentence':
        string = string.string.lower()
    stop_signals = ["never mind", "stop", "dismiss", "cancel", "dont want", "dont need", "do not"]
    if string == "no":
        return True
    for signal in stop_signals:
        if signal in string:
            return True
    return False

# input: pattern.en sentence object
def nearBy(sentence):
    res = ""
    for chunk in sentence.chunks:
        if chunk.type in ['PP', 'ADVP']:
            res += " ".join([w.string for w in chunk.words if w.type in ['RB', 'PRP', 'IN']])
            res += " "
    res = res.strip()
    if res in ['near me', 'around here', 'around', 'here', 'near here', 'nearby', 'near by', 'close by', 'close']:
        return True
    return False

# input: pattern.en sentence object
def fullQuery(sentence):
    new_str = ""
    for word in sentence.words:
        if word.string in ['places', 'locations', 'spots']:
            continue
        new_word = singularize(word.string) if word.type == "NNS" else word.string
        new_str += new_word + " "
    singularized_sentence = parsetree(new_str, relations=True, lemmata=True)

    
    m = search('{JJ? NN+} IN {JJ? NN+}', singularized_sentence)
    query = {}
    if len(m) > 0:
        query["term"] = m[0].group(1).string
        query["location"] = m[0].group(2).string
    return query


def oneOf(arr):
    rand_idx = random.randint(0,len(arr) - 1)
    return arr[rand_idx]

def randOneIn(chance):
    i = random.randint(1,chance)
    if i == chance:
        return True
    return False

def badWords(string):
    for word in string.split(" "):
        if word in BAD_WORDS:
            return True
    return False

def openNow(sentence):
    if "open now" in sentence.string or "opens now" in sentence.string:
        return True
    return False

def hasWifi(sentence):
    string = removePunctuation(sentence.string.lower())
    if "wifi" in string:
        return True
    return False

def isGetNews(sentence):
    m = search('{VP} {VBG+? JJ+?} {news | information} about {NP+}', sentence)
    if len(m) > 0:
        if m[0].group(1).string in ['get', 'find', 'tell', 'show', 'fetch', 'search']:
            return True
    return False

def getNewsQuery(sentence):
    m = search('{NN+} about {NP+}', sentence)
    if len(m) > 0:
        return m[0].group(2).string