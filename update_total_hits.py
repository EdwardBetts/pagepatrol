#!/usr/bin/python3
from pagepatrol.database import session
from pagepatrol.model import Term
from pagepatrol import wikipedia, create_app
import re

create_app('config.default')

for t in Term.query:
    old = t.total_hits
    q = t.get_query()
    results = wikipedia.wiki_search(t.get_query())
    t.total_hits = results.total_hits

    if results.total_hits < 500:
        while True:
            safe_articles = {doc.title for doc in t.safe_articles}
            pattern = '|'.join(re.escape(safe.phrase) for safe in t.safe_phrases)
            re_phrase = re.compile('(' + pattern + ')', re.I)

            for doc in results.docs:
                if doc['title'] in safe_articles:
                    t.total_hits -= 1
                if t.term.lower() not in doc['text'].lower():
                    t.total_hits -= 1
                if pattern and re_phrase.search(doc['text']):
                    t.total_hits -= 1
            if not results.next_offset:
                break
            results = wikipedia.wiki_search(t.get_query(), offset=results.next_offset)

    print('{:14s} {:5} -> {:5d}'.format(t.term, old or '', t.total_hits))
    session.add(t)
    session.commit()
