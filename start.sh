#!/usr/bin/env sh

# Script to pull the latest of the web_server into the container on start

ln -s /json /code/json
cd /code
# Start the application
export FLASK_APP=$script
export FLASK_DEBUG=True
if [ $2 ]; then
    flask run --host=0.0.0.0 -p $port
else
    flask run --host=0.0.0.0
fi
