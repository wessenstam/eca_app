# Call the Ip addresses from the Cluster of the Docker VM
# Willem Essenstam - Initial version

import requests
import json
import time
import gspread
import pandas as pd
import time
from oauth2client.service_account import ServiceAccountCredentials

# No warnings should be displayed on SSL certificates
requests.packages.urllib3.disable_warnings()

# Function for updating the underlaying GSheet so we can always grab back to the updated version
def update_gsheet_df(cluster,nr,docker_vmip):
    # Based on the information we got we need to set some variables to the correct values.
    row_cluster = int(df[df['Cluster IP'] == cluster].index[0])
    #df.iat[row_cluster, nr] = docker_vmip
    row = int(row_cluster)+2
    # Update Attendee Gsheet
    wks.update_cell(row, nr+1, docker_vmip)


# Function for checking URLs
def CheckURL(URL,username,passwd,payload,method):
    if method=="GET":
        # Get the anwser from the URL
        headers = {"Content-Type": "application/json"}
        anwser=requests.get(URL,verify=False,auth=(username,passwd),timeout=15,headers=headers)
    else:
        headers={"Content-Type": "application/json"}
        anwser = requests.post(URL, verify=False, auth=(username, passwd), timeout=15,data=payload,headers=headers)

    try:
        json_data = json.loads(anwser.text)[0]
        return json_data
    except KeyError:
        json_data=json.loads(anwser.text)
        return json_data
    except:
        return_val='["Error"]'
        return return_val

# ****************************************************************************************************************
# Set the needed GSheet credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)

# ****************************************************************************************************************
# Grabbing the initial data from gsheet for the attendees
wks = gc.open("GTS IP addresses").sheet1
data = wks.get_all_values()
headers = data.pop(0)
# Drop all data in a dataframe for the attendees
df = pd.DataFrame(data, columns=headers)
user=8
for cluster in df['Cluster IP']:
    if cluster !="":

        for nr in range(1,user):
            url='https://'+cluster+':9440/api/nutanix/v3/vms/list'
            payload='{"kind": "vm","filter": "vm_name==User0'+str(nr)+'-docker_VM"}'
            method="POST"
            json_data=CheckURL(url,'admin','ntnxGTS2021!',payload,method)
            if json_data['metadata']['total_matches'] < 1:
                continue
            else:
                docker_vmip=json_data['entities'][0]['spec']['resources']['nic_list'][0]['ip_endpoint_list'][0]['ip']
                update_gsheet_df(cluster,nr,docker_vmip)
	
	
