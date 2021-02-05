#!/usr/bin/env sh

# Script to pull the latest of the web_server into the container on start

ln -s /json /code/json
cd /code
# Start the application
export FLASK_APP=app.py
export FLASK_DEBUG=True
flask run --host=0.0.0.0
