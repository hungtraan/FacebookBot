import requests, time
from datetime import datetime, timedelta

def get_trending_news(keyword):
    score = 8
    ranking = 10000
    r = request_news(keyword, score, ranking)
    num_results = r.json()['totalResults']
    retry = 0

    while num_results < 10 and score > 0:
        score -= 2
        ranking *= 4
        retry += 1
        print "News about %s - Retry %d"%(keyword, retry)

        r = request_news(keyword, score, ranking)
        num_results = r.json()['totalResults']
            
    posts = r.json()['posts']

    results = []

    # Prune excess data in posts
    for post in posts:
        obj = {}
        obj['url'] = post['url']
        obj['title'] = post['thread']['title_full']
        obj['image_url'] = post['thread']['main_image']
        if post['social']['facebook']['likes'] < 50:
            obj['subtitle'] = post['text'][:77] + "... \n"

        else:
            obj['subtitle'] = post['text'][:50] + "... \n"
            obj['subtitle'] += "%d Likes, %d Shares"%(post['social']['facebook']['likes'], post['social']['facebook']['shares'])

        results.append(obj)
    return results

def request_news(keyword, score, ranking):
    target = datetime.now() - timedelta(days=7)
    timestamp =  time.mktime(target.timetuple())
    q = "%s performance_score:>%d domain_rank:<%d"%(keyword, score, ranking)
    params = {
        'token':'2cc0a4a7-aea5-447f-9d21-f8edc80c32ed',
        'format':'json',
        'size':10,
        'site_type':'news',
        'language': 'english',
        'q': q,
        'ts': timestamp
    }

    if score < 5:
        target = datetime.now() - timedelta(days=14)
        timestamp =  time.mktime(target.timetuple())
        params['site_type'] = 'news,blogs'
        params['ts'] = timestamp

    if score < 3:
        target = datetime.now() - timedelta(days=30)
        timestamp =  time.mktime(target.timetuple())
        params['q'] = keyword
        del params['site_type']
        params['ts'] = timestamp

    return requests.get('https://webhose.io/search', params=params)