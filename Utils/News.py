import requests

def get_trending_news(keyword):
    q = "%s performance_score:>7 domain_rank:<10000"%(keyword)
    params = {
        'token':'2cc0a4a7-aea5-447f-9d21-f8edc80c32ed',
        'format':'json',
        'size':10,
        'site_type':'news',
        'language': 'english',
        'q': q,
        'ts': 1470011728652
    }

    r = requests.get('https://webhose.io/search', params=params)
    posts = r.json()['posts']

    results = []
    for post in posts:
        obj = {}
        obj['url'] = post['url']
        obj['title'] = post['thread']['title_full']
        obj['image_url'] = post['thread']['main_image']
        obj['subtitle'] = post['text'][:50] + "... \n"
        obj['subtitle'] += "%d Likes, %d Shares"%(post['social']['facebook']['likes'], post['social']['facebook']['shares'])

        results.append(obj)
    return results
