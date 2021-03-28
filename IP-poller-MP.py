# Call the Ip addresses from the Cluster of the Docker VM
# Willem Essenstam - Initial version

import concurrent.futures
import requests
import json
import time
import gspread
import pandas as pd
import time
from oauth2client.service_account import ServiceAccountCredentials
from random import randrange
from df2gspread import df2gspread as d2g

# No warnings should be displayed on SSL certificates
requests.packages.urllib3.disable_warnings()

def cluster_info(cluster):
    user=8
    print(cluster)
    #Sleep a random number of Secs before moving on, due to Google API Rate Limit
    for nr in range(1,user):
        url='https://'+cluster+':9440/api/nutanix/v3/vms/list'
        payload='{"kind": "vm","filter": "vm_name==User0'+str(nr)+'-docker_VM"}'
        method="POST"
        json_data=CheckURL(url,'admin','ntnxGTS2021!',payload,method)
        if 'ERROR' not in str(json_data):
            if len(json_data['entities']) >0:
                docker_vmip=json_data['entities'][0]['spec']['resources']['nic_list'][0]['ip_endpoint_list'][0]['ip']
            else:
                docker_vmip="Not Found"
                update_gsheet_df(cluster,nr,docker_vmip)
                continue
        else:
            docker_vmip="NO CON"
            update_gsheet_df(cluster,nr,docker_vmip)
            break
        update_gsheet_df(cluster,nr,docker_vmip)

# Function for updating the underlaying GSheet so we can always grab back to the updated version
def update_gsheet_df(cluster,nr,docker_vmip):
    # Based on the information we got we need to set some variables to the correct values.
    row_cluster = int(df[df['Cluster IP'] == cluster].index[0])
    df.iat[row_cluster, nr] = docker_vmip
    #row = int(row_cluster)+2
    # Update Attendee Gsheet
    #wks.update_cell(row, nr+1, docker_vmip)


# Function for checking URLs
def CheckURL(URL,username,passwd,payload,method):
    if method=="GET":
        # Get the anwser from the URL
        headers = {"Content-Type": "application/json"}
        try:
            anwser=requests.get(URL,verify=False,auth=(username,passwd),timeout=15,headers=headers)
        except:
            return "{'state':'ERROR'}"
    else:
        headers={"Content-Type": "application/json"}
        try:
            anwser = requests.post(URL, verify=False, auth=(username, passwd), timeout=15,data=payload,headers=headers)
        except:
            return "{'state':'ERROR'}"
    try:
        json_data = json.loads(anwser.text)[0]
        return json_data
    except KeyError:
        json_data=json.loads(anwser.text)
        return json_data
    except:
    
        return "{'state':'ERROR'}"

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
clusters=df['Cluster IP'].to_list()

# Drop all found IPs in the DF
with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
    executor.map(cluster_info, clusters)

# Dump DF to Gsheet
spreadsheet_key='1HIwvPkKvrLx1IwYtwTsvpKQS6RdkuTAOQBL9-5Diw-8'
wks_name='Master'
d2g.upload(df, spreadsheet_key, wks_name, credentials=credentials, row_names=True)