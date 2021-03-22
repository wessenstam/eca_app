import pika, sys, os
import json
import requests


local_port=os.environ['local_port']
local_url=os.environ['local_url']
lookup_url=os.environ['lookup_url']
validator_url=os.environ['validator_url']

# ****************************************************************************************************************
# Functions area
# ****************************************************************************************************************

def update_client(payload):
    # Send to Lookup tool
    url="http://"+lookup_url+"/update_api"
    payload=json.dumps(payload)
    reply=requests.post(url, data=payload)
    print("Updater (cient) has given the update command. Answer from server was :"+reply.text)

def update_validator(payload):
    # Sens to validator tool
    url="http://"+validator_url+"/update_api"
    payload=json.dumps(payload)
    reply=requests.post(url, data=payload)
    print("Updater (validator) has given the update command. Answer from server was :"+reply.text)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=local_url,port=local_port))
    channel = connection.channel()

    channel.queue_declare(queue='update')

    def callback(ch, method, properties, body):
        update_client(body.decode())
        update_validator(body.decode())

    channel.basic_consume(queue='update', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()



# ****************************************************************************************************************
# Main Routine
# ****************************************************************************************************************
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

