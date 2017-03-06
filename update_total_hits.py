#!/usr/bin/python3
from pagepatrol.database import session
from pagepatrol.model import Term
from pagepatrol import wikipedia, create_app

create_app('config.default')

for t in Term.query:
    safe_phrases = ''.join(' -insource:"{}"'.format(safe.phrase) for safe in t.safe_phrases)
    # base_q = '"{}" -intitle:"{}"'.format(t.term, t.term)
    base_q = 'insource:"{}"'.format(t.term)
    if len(base_q) + len(safe_phrases) <= 300:
        q = base_q + safe_phrases
    else:
        q = base_q

    old = t.total_hits
    t.total_hits = wikipedia.hit_count(q)
    print('{:14s} {:5} -> {:5d}  {}'.format(t.term, old or '', t.total_hits, q))
    session.commit()
