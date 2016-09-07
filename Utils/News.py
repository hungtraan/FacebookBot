import requests, time, re
from datetime import datetime, timedelta

def get_trending_news(keyword):
    print keyword
    score = 8
    ranking = 10000
    r = request_news(keyword, score, ranking)
    num_results = r.json()['totalResults']
    retry = 0

    while num_results < 10 and score > 0:
        score -= 2
        ranking *= 4
        retry += 1
        print "News about: %s - Retry %d"%(keyword, retry)

        r = request_news(keyword, score, ranking)
        num_results = r.json()['totalResults']
            
    posts = r.json()['posts']

    results = []

    # Prune excess data in posts
    for post in posts:
        obj = {}
        obj['url'] = post['url']
        obj['title'] = post['thread']['title_full']
        obj['image_url'] = ""
        if 'main_image' in post['thread']:
            img = post['thread']['main_image']
            if img is not None and isValidImgUrl(img):
                obj['image_url'] = img
        
        try:
            if 'social' in post['thread']:
                if post['thread']['social']['facebook']['likes'] < 50:
                    obj['subtitle'] = post['text'][:77] + "..."
                else:
                    obj['subtitle'] = post['text'][:50] + "... \n"
                    obj['subtitle'] += "%d Likes, %d Shares"%(post['thread']['social']['facebook']['likes'], post['thread']['social']['facebook']['shares'])
            else:
                obj['subtitle'] = post['text'][:77] + "..."

        except Exception, e:
            print e
            continue
        
        results.append(obj)
    return results

def request_news(keyword, score, ranking):
    q = "%s performance_score:>%d domain_rank:<%d"%(keyword, score, ranking)
    params = {
        'token':'2cc0a4a7-aea5-447f-9d21-f8edc80c32ed',
        'format':'json',
        'size':10,
        'site_type':'news',
        'language': 'english',
        'q': q,
    }

    if score == 6:
        q = "%s performance_score:>%d domain_rank:<%d"%(keyword, score, ranking)

        target = datetime.now() - timedelta(days=7)
        timestamp = time.mktime(target.timetuple())
        params['site_type'] = 'news'
        params['ts'] = timestamp

    if score == 4:
        target = datetime.now() - timedelta(days=14)
        timestamp = time.mktime(target.timetuple())
        params['site_type'] = 'news,blogs'
        params['ts'] = timestamp

    if score == 2:
        target = datetime.now() - timedelta(days=28)
        timestamp = time.mktime(target.timetuple())
        params['q'] = keyword
        del params['site_type']
        params['ts'] = timestamp

    return requests.get('https://webhose.io/search', params=params)

def isValidImgUrl(url):
    urlRegex = "(http|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?(.png|.jpg|.jpeg|.gif)"
    img = re.search(urlRegex, url)
    if img == None:
        return False
    return True