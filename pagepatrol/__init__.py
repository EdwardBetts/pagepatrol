from flask import Flask
from . import database
from . import view

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    database.init_app(app)
    view.init_app(app)

    return app
