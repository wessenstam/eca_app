#!/usr/bin/env sh

# Script to pull the latest of the web_server into the container on start

ln -s /json /code/json
cd /code
# Start the application
python3 $script
