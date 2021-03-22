import pika, sys, os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ****************************************************************************************************************
# Area for definition of variables
lab_type_lst=["snow","leap","cmdb","xplay","aav","dam","mssql","ultimate","prov","calm","flow","cont","use","era","k8s","fiesta","day2"]

# ****************************************************************************************************************
# Set the needed GSheet credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)

# ****************************************************************************************************************
# Grabbing the initial data from gsheet for the attendees
wks = gc.open("GTS Clusters-Assignments").sheet1

# ****************************************************************************************************************
# Functions area
# ****************************************************************************************************************

def send_msq_msg(msg):
    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='update')
    channel.basic_publish(exchange='', routing_key='update', body=msg)
    connection.close()


def update_gsheet(msg):
    json_var=str(msg.decode().replace("'","\""))
    json_dict=eval(json_var)
    usernr=json_dict['usernr']
    lab=json_dict['lab']
    progress=json_dict['progress']
    if progress=="Req Validation":
        progress="Pending"
    row = int(usernr) + 1
    col = 16
    if "iaas" in lab:  # Enter the IAAS labs
        type_lab = lab[8:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr

    elif "db" in lab:  # Enter the DB labs
        type_lab = lab[6:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr

    elif "euc" in lab:  # Enter the EUC labs
        type_lab = lab[7:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr

    elif "cicd" in lab:  # Enter the CICD labs
        type_lab = lab[5:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
        web_templ = "web_cicd.html"
    else:
        type_lab = lab[6:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr  # Column AC

    # Update Attendee Gsheet
    wks.update_cell(row, col, progress) 
    json_dict['progress']=progress
    send_msq_msg(json.dumps(json_dict))


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='request')
    def callback(ch, method, properties, body):
        update_gsheet(body)
    channel.basic_consume(queue='request', on_message_callback=callback, auto_ack=True)
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

