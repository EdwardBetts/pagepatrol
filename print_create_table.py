#!/usr/bin/python3

from sqlalchemy.schema import CreateTable
from pagepatrol.model import *
from pagepatrol import create_app
from pagepatrol.database import session
import sys

app = create_app('config.default')
engine = session.get_bind()

for class_name in sys.argv[1:]:
    cls = globals()[class_name]

    sql = str(CreateTable(cls.__table__).compile(engine))
    print(sql.strip() + ';')
