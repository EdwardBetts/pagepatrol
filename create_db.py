#!/usr/bin/python3

from pagepatrol.model import Base
from pagepatrol.database import init_db, session
from pagepatrol import create_app

app = create_app('config.default')
init_db(app.config['DB_URL'])
Base.metadata.create_all(session.get_bind())
