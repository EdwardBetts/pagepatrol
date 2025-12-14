#!/usr/bin/python3
from pagepatrol.database import session
from pagepatrol.model import Term, SafePhraseArtcle, TermNotInArticle
from pagepatrol import wikipedia, create_app
import re

create_app('config.default')

skip = None
for t in Term.query:
    print(t.term)
    if skip:
        if t.term == skip:
            skip = None
        continue
    old = t.total_hits
    q = t.get_query()
    results = wikipedia.wiki_search(t.get_query())
    t.total_hits = results.total_hits
    lc_term = t.term.lower()

    hits = set()
    while True:
        safe_articles = {doc.title for doc in t.safe_articles}
        pattern = '|'.join(re.escape(safe.phrase) for safe in t.safe_phrases)
        re_phrase = re.compile('(' + pattern + ')')

        for doc in results.docs:
            title = doc['title']
            if title in safe_articles:
                continue
            if lc_term not in doc['text'].lower():
                i = TermNotInArticle(title=title, term=t.term)
                print('  ', (title, t.term))
                session.merge(i)
                continue
            if pattern:
                m = re_phrase.search(doc['text'])
                if m:
                    phrase = m.group(1)
                    i = SafePhraseArtcle(phrase=phrase, title=title, term=t.term)
                    print('  ', (phrase, title, t.term))
                    session.merge(i)
                    continue
            hits.add(doc['title'])
        if not results.next_offset:
            break
        results = wikipedia.wiki_search(t.get_query(), offset=results.next_offset)
    t.total_hits = len(hits)
    print(hits)

    print('{:14s} {:5} -> {:5d}'.format(t.term, (old if old is not None else ''), t.total_hits))
    session.add(t)
    session.commit()
