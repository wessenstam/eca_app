#!/usr/bin/env sh

# Script to pull the latest of the web_server into the container on start
mkdir -p /github
cd /github
git clone https://github.com/wessenstam/eca_app

ln -s /json /github/eca_app/json
cd /github/eca_app
# Start the application
export FLASK_APP=app.py
export FLASK_DEBUG=True
flask run --host=0.0.0.0
