import requests

QUERY_URL = 'https://en.wikipedia.org/w/api.php'
PROP = ['snippet', 'redirectsnippet', 'redirecttitle',
        'sectionsnippet', 'sectiontitle']
GENERATOR_SEARCH_PARAMS = {
    'format': 'json',
    'action': 'query',
    'generator': 'search',
    'gsrlimit': 50,
    'gsrnamespace': 0,  # articles
    'gsrprop': '|'.join(PROP),
    'prop': 'revisions|info',
    'rvprop': 'content',
    'continue': '',
    'formatversion': 2,
}

SEARCH_PARAMS = {
    'format': 'json',
    'action': 'query',
    'list': 'search',
    'srlimit': 50,
    'srnamespace': 0,  # articles
    'formatversion': 2,
}

class SearchResults(object):
    def __init__(self, query_json, total_hits=None):
        query = query_json['query']
        if total_hits:
            self.total_hits = total_hits
        self.docs = [{'title': doc['title'], 'text': doc['revisions'][0]['content']}
                     for doc in query['pages']]

        if 'continue' in query_json:
            self.next_offset = query_json['continue']['gsroffset']
        else:
            self.next_offset = None

def hit_count(q):
    params = dict(SEARCH_PARAMS)
    params['srsearch'] = q
    params['srprop'] = ''

    r = requests.get(QUERY_URL, params=params)
    query_json = r.json()
    return query_json['query']['searchinfo']['totalhits']

def wiki_search(q, offset=None, prop=None):
    params = dict(GENERATOR_SEARCH_PARAMS)
    params['gsrsearch'] = q
    if offset:
        params['gsroffset'] = offset
    if prop:
        if 'title' in prop:
            prop.remove('title')
        params['srprop'] = '|'.join(prop)

    r = requests.get(QUERY_URL, params=params)
    return SearchResults(r.json(), total_hits=hit_count(q))

def find_matching_titles(q):
    params = dict(SEARCH_PARAMS)
    params['srsearch'] = 'intitle:"{}"'.format(q)
    params['srprop'] = ''

    r = requests.get(QUERY_URL, params=params)
    query_json = r.json()
    return [doc['title'] for doc in query_json['query']['search']]

def term_search(q):
    params = dict(SEARCH_PARAMS)
    params['srsearch'] = 'insource:"{}"'.format(q)
    params['srprop'] = ''

    r = requests.get(QUERY_URL, params=params)
    query_json = r.json()
    print(r.url)
    return [doc['title'] for doc in query_json['query']['search']]

def get_content(titles):
    params = {
        'format': 'json',
        'action': 'query',
        'formatversion': 2,
        'prop': 'revisions|info',
        'rvprop': 'content|timestamp',
        'titles': '|'.join(titles)
    }

    r = requests.get(QUERY_URL, params=params)
    return r.json()['query']['pages']
