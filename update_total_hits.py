#!/usr/bin/python3
from pagepatrol.database import session
from pagepatrol.model import Term
from pagepatrol import wikipedia, create_app

create_app('config.default')

for t in Term.query:
    old = t.total_hits
    q = t.get_query()
    t.total_hits = wikipedia.hit_count(q)
    print('{:14s} {:5} -> {:5d}'.format(t.term, old or '', t.total_hits))
    session.add(t)
    session.commit()
