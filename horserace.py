import pika, sys, os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

local_port=os.environ['local_port']
local_url=os.environ['local_url']

# ****************************************************************************************************************
# Area for definition of variables
lab_type_lst=["snow","leap","cmdb","xplay","aav","dam","mssql","ultimate","prov","calm","flow","cont","use","era","k8s","fiesta","day2"]

# ****************************************************************************************************************
# Set the needed GSheet credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)

# ****************************************************************************************************************
# Functions area
# ****************************************************************************************************************

def update_gsheet(msg):
    json_var=json.loads(str(msg.decode()))
    json_dict=eval(str(json_var))
    usernr=json_dict['usernr']
    lab=json_dict['lab']
    validator=json_dict['progress']

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

    else:
        type_lab = lab[6:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr  # Column AC

    # Update the Validator GSheet and DF_SME if there has been a validated received
    # ****************************************************************************************************************
    # Grab the data from the SME Gsheet
    wks_sme = gc.open("GTS SME Validations").sheet1
    data = wks_sme.get_all_values()
    headers = data.pop(0)
    # Drop all data in a dataframe for the attendees
    df_sme = pd.DataFrame(data, columns=headers)
    # Cleaning up the lines that have no name
    df_sme.drop(df_sme[df_sme['Name'] == ""].index, inplace=True)
    row_sme=int(df_sme[df_sme['Name'] == validator].index[0])
    col=col - 14
    col_df=col - 1
    # Read the value from the DF_SME for the validator
    value=df_sme.iloc[row_sme,col_df]
    if value=="":
        value=0
    value=int(value)+1
    wks_sme.update_cell(row_sme+2, col, value)
    print("Updated Gsheet...")


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=local_url, port=local_port))
    channel = connection.channel()
    channel.queue_declare(queue='horserace')
    def callback(ch, method, properties, body):
        update_gsheet(body)
    channel.basic_consume(queue='horserace', on_message_callback=callback, auto_ack=True)
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

