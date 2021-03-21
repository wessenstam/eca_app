import pika, sys, os
import json
import requests


# ****************************************************************************************************************
# Functions area
# ****************************************************************************************************************

def update_client(payload):
    url="http://localhost:4999/update_api"
    payload=json.dumps(payload)
    reply=requests.post(url, data=payload)
    print("Updater has given the update command. Answer from server was :"+reply.text)
    


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='update')

    def callback(ch, method, properties, body):
        update_client(body.decode())

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

