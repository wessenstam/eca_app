import pika, sys, os

aws_port=os.environ['aws_port']
aws_url=os.environ['aws_url']
local_port=os.environ['local_port']
local_url=os.environ['local_url']


def send_msq_msg(msg):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=local_url,port=local_port))
    channel = connection.channel()
    channel.queue_declare(queue='request')
    channel.basic_publish(exchange='', routing_key='request', body=msg)
    connection.close()
    print("Transporter Send message: "+msg.decode())

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=aws_url,port=aws_port))
    channel = connection.channel()

    channel.queue_declare(queue='request')

    def callback(ch, method, properties, body):
        send_msq_msg(body)

    channel.basic_consume(queue='request', on_message_callback=callback, auto_ack=True)

    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)