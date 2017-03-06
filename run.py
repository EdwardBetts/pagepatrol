#!/usr/bin/python3
from pagepatrol import create_app

if __name__ == "__main__":
    app = create_app('config.default')
    app.run('0.0.0.0', debug=True)
