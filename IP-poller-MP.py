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
from df2gspread import df2gspread as d2g


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

df_ip=df.copy()

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
        else:
            docker_vmip="NO CON"
            row_cluster = int(df_ip[df_ip['Cluster IP'] == cluster].index[0])
            df_ip.iat[row_cluster, nr] = docker_vmip
            break
        row_cluster = int(df_ip[df_ip['Cluster IP'] == cluster].index[0])
        df_ip.iat[row_cluster, nr] = docker_vmip
    return df_ip

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



if __name__ == '__main__':
    # Drop all found IPs in the DF
    workers=[]
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for cluster in clusters:
            workers.append(executor.submit(cluster_info,cluster))
        print(workers)

        for f in concurrent.futures.as_completed(workers):
            df_return=f.result()
            df = df.append([df_return], sort=False)
    df_ip=pd.DataFrame(list(df))
    print(df_ip.shape())
    # Dump DF to Gsheet
    spreadsheet_key='1HIwvPkKvrLx1IwYtwTsvpKQS6RdkuTAOQBL9-5Diw-8'
    wks_name='Master_mp'
    d2g.upload(df_ip, spreadsheet_key, wks_name, credentials=credentials, row_names=True)