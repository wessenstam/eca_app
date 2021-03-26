# Python Flask server for attendee look up
# Willem Essenstam - Nutanix - 25 May 2020
# Willem Essenstam - Nutanix - 6 Feb 2021
#           Adding the possibility to use validation via the field



import json
from flask import *
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
import gspread
from gspread_formatting  import *
import pandas as pd
import os
from datetime import timedelta
from oauth2client.service_account import ServiceAccountCredentials
import pika
import numpy as np
from natsort import index_natsorted

# ****************************************************************************************************************
# Get the needed password for the vlidator pages from the OS envionment
validator_password=os.environ['validator_password']
local_port=os.environ['local_port']
local_url=os.environ['local_url']
# ****************************************************************************************************************
# Geting the Forms ready to be used
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    submit = SubmitField('Lookup...')

def get_templ_send_msq(usernr, lab,progress):
    # Based on the information we got we need to set some variables to the correct values.
    row = int(usernr) + 1
    col = 16
    if "iaas" in lab:  # Enter the IAAS labs
        type_lab = lab[8:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
        web_templ="web_hybrid_cloud.html"
    elif "db" in lab:  # Enter the DB labs
        type_lab = lab[6:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
        web_templ = "web_database.html"
    elif "euc" in lab:  # Enter the EUC labs
        type_lab = lab[7:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
        web_templ = "web_euc.html"
    elif "cicd" in lab:  # Enter the CICD labs
        type_lab = lab[5:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
        web_templ = "web_cicd.html"
    else:
        type_lab = lab[6:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr  # Column AC
        web_templ = "web_cloud.html"

    # Send the to be updated info to the MSQ for further processing
    data='{"usernr":"'+str(usernr)+'","lab":"'+lab+'","progress":"'+progress+'"}'
    json_data=json.dumps(data)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=local_url,port=local_port))
    channel = connection.channel()
    channel.queue_declare(queue='request')
    channel.basic_publish(exchange='', routing_key='request', body=data)
    connection.close()
    print("Transporter Send message: "+data)

    return web_templ

# Function for sending the update message to the MSQ so we can update the GSheet
def send_msg_update(usernr,lab,progress,queue):
    data=data='{"usernr":"'+str(usernr)+'","lab":"'+lab+'","progress":"'+progress+'"}'
    json_data=json.dumps(data)

    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=local_url,port=local_port))
    channel = connection.channel()
    channel.queue_declare(queue=queue)
    channel.basic_publish(exchange='', routing_key=queue, body=json_data)
    print(" [x] Sent "+json_data)
    connection.close()


# ****************************************************************************************************************
# Some Flask settings
app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'

# ****************************************************************************************************************
# Set the needed GSheet credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)

# ****************************************************************************************************************
# Grabbing the initial data from gsheet for the attendees
wks = gc.open("GTS Clusters-Assignments").sheet1
data = wks.get_all_values()
headers = data.pop(0)
# Drop all data in a dataframe for the attendees
df = pd.DataFrame(data, columns=headers)
# Clean up the lines with no email address
df.drop(df[df['Email'] == ""].index, inplace=True)
df.set_index('Nr')

# ****************************************************************************************************************
# Grab the data from the SME Gsheet
wks_sme = gc.open("GTS SME Validations").sheet1
data = wks_sme.get_all_values()
headers = data.pop(0)
# Drop all data in a dataframe for the attendees
df_sme = pd.DataFrame(data, columns=headers)
# Cleaning up the lines that have no name
df_sme.drop(df_sme[df_sme['Name'] == ""].index, inplace=True)

# ****************************************************************************************************************
# Grab the data from the GTS 2021 Docker VM IP Gsheet
wks_sme = gc.open("GTS IP addresses").sheet1
data = wks_sme.get_all_values()
headers = data.pop(0)
# Drop all data in a dataframe for the attendees
df_docker_ip = pd.DataFrame(data, columns=headers)
# Cleaning up the lines that have no name
df_docker_ip.drop(df_docker_ip[df_docker_ip['Cluster IP'] == ""].index, inplace=True)



# ****************************************************************************************************************
# Area for definition of variables
lab_type_lst=["snow","leap","cmdb","xplay","aav","dam","mssql","ultimate","prov","calm","flow","cont","use","era","k8s","fiesta","day2"]


# Build the routing fo the pages
@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=8)

@app.route('/logout')  
def logout():  
    error = ""
    form = LoginForm()
    user_data = ""
    session.pop('validator', None)
    session.pop('validated', None)
    if 'email' in session:  
        session.pop('email',None)
        return render_template('web_loged_out.html',org="attendee")
    else:  
        return render_template('web_loged_out.html',org="validator")

@app.route('/horse_race')
def graph():
    df_sme.sort_values(by=['Total','Name'], key=lambda x: np.argsort(index_natsorted(df_sme['Total'])), ascending=[False,True], inplace=True)
    labels = df_sme['Name'].head(10).to_list()
    values = df_sme['Total'].head(10).to_list()
    max_val=int(values[0])*1.5
    if max_val < 10:
        max_val=10

    colors = [
        "#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA",
        "#ABCDEF", "#DDDDDD", "#ABCABC", "#4169E1",
        "#C71585", "#FF4500"]

    bar_labels=labels
    bar_values=values
    return render_template('bar_chart.html', title='Validators Horse Race', max=max_val, labels=bar_labels, values=bar_values)


@app.route("/update")
def update_df():
    # Reload the data from the Gsheet
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json', scope)  # Change location as soon as it comes into prod
    gc = gspread.authorize(credentials)
    wks = gc.open("GTS Clusters-Assignments").sheet1  # get the Gsheet
    data = wks.get_all_values()
    headers = data.pop(0)
    # Drop all data in a dataframe for the attendees
    df.update(pd.DataFrame(data, columns=headers))
    # Clean up the lines with no email address
    df.drop(df[df['Email'] == ""].index, inplace=True)
    # ****************************************************************************************************************
    # Grab the data from the SME Gsheet
    wks_sme = gc.open("GTS SME Validations").sheet1
    data = wks_sme.get_all_values()
    headers = data.pop(0)
    # Drop all data in a dataframe for the SMEs
    df_sme.update(pd.DataFrame(data, columns=headers))
    # Cleaning up the lines that have no name
    df_sme.drop(df_sme[df_sme['Name'] == ""].index, inplace=True)
    
    return render_template('web_update.html', title='vGTS2021 - Cluster lookup')

@app.route("/update_api", methods=['POST'])
def update_api_df():
    print(request.get_data().decode())
    send_post_dict=eval(json.loads(request.get_data().decode()))
    usernr=send_post_dict['usernr']
    lab=send_post_dict['lab']
    progress=send_post_dict['progress']
    # Update the DF so the user sees the data
    df.at[int(usernr)-1 , lab] = progress

    return "Received"


@app.route("/validation", methods=['POST'])
def show_form_validation():
    # Get the data from the values that where set and create the reply
    reply_post=request.form
    lab=reply_post['lab']
    username=reply_post['username']
    clustername=reply_post['clustername']
    clusterip=reply_post['clusterip']
    pcip=reply_post['pcip']
    usernr=reply_post['usernr']
    info_data= {'lab':lab,
                'username':username,
                'usernr': usernr,
                'clustername':clustername,
                'clusterip':clusterip,
                'pcip': pcip
               }
    # Update the DF in the correct column and row
    row=int(usernr)+1
    col = 16
    if "iaas" in lab: # Enter the IAAS labs
        type_lab=lab[8:]
        item_nr=lab_type_lst.index(type_lab)
        col=col+item_nr
    elif "db" in lab: # Enter the DB labs
        type_lab = lab[6:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
    elif "euc" in lab: # Enter the EUC labs
        type_lab = lab[7:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
    elif "cicd" in lab: # Enter the CICD labs
        type_lab = lab[5:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr
    else:
        type_lab = lab[6:]
        item_nr = lab_type_lst.index(type_lab)
        col = col + item_nr # Column AC

    # Update Gsheet
    wks.update_cell(row,col,"Pending")
    # Update the DF
    df.at[int(usernr)-1 , lab] = "Pending"


    return render_template('web_validation.html', title='vGTS 2021 - Validation', info=info_data)

@app.route("/", methods=['GET','POST'])
def show_form_validator():
    if "validated" in session:

        if request.method =="POST":
            reply_post = request.form
            webdata={'username':reply_post['username'],
                        'labname':reply_post['labname']
                        }

            if reply_post['action'] == "Validate":
                # Have the data updated as we have a valid validation request for the updater to client and validator
                send_msg_update(reply_post['usernr'],reply_post['labname'],"Validated","update")
                # Have the data updated as we have a valid validation request for horserace
                send_msg_update(reply_post['usernr'],reply_post['labname'],"Validated","horserace")

            else:
                # Have the data updated as we have a rejected validation request MSQ Update
                send_msg_update(reply_post['usernr'],reply_post['labname'],"Rejected;"+reply_post['validator'])
                

            return render_template('web_validation_received.html',info=webdata, title='vGTS2021 - Validator area')
        else:
            # Do we have a usernr where we need to get the correct info from??
            if str(request.args.get('lab')) != 'None':
                usernr=str(request.args.get('usernr'))
                labname=str(request.args.get('lab'))
                # Have the data updated and get the returned info for the webpage
                web_templ=get_templ_send_msq(int(usernr), labname, "In progress")
                # Get all information from the DF for the user
                dict_user = df.loc[int(usernr)-1].to_dict()
                
                # Get the Docker IP from the DF_docker_ip using the user's info
                docker_ip= df_docker_ip.loc[df_docker_ip['Cluster IP']==dict_user['IP address VIP'],'User0'+str(dict_user['UserX'])].to_list()
    
                user_values={'username':dict_user['First Name']+" "+dict_user['Last Name'],
                                'clustername': dict_user['Cluster Name'],
                                'clusterip': dict_user['IP address VIP'],
                                'pc_ip':dict_user['IP address PC'],
                                'usernr':dict_user['Nr'],
                                'userx': dict_user['UserX'],
                                'snow_instance': dict_user['SNOW'],
                                'labname': labname,
                                'validator': session['validator'],
                                'aws_ip':dict_user['AWS-IP'],
                                'docker_vm_ip':docker_ip[0]}

                return render_template(web_templ, title='vGTS2021 - Validator area', user=user_values)

            else:
                # Get all users info: usernr, First Name, Last Name and Pending status lab validation, but they must not be empty!
                # Make copies of the existing big DF
                df_val_hc_iaas=df[['Nr','UserX','First Name','Last Name','hc-iaas-snow','hc-iaas-leap','hc-iaas-cmdb','hc-iaas-xplay','SNOW']].copy()
                df_val_db=df[['Nr','UserX','First Name','Last Name','hc-db-aav','hc-db-dam','hc-db-mssql','hc-db-ultimate','AWS-IP']].copy()
                df_val_euc=df[['Nr','UserX','First Name','Last Name','hc-euc-prov','hc-euc-calm','hc-euc-flow']].copy()
                df_val_cicd = df[['Nr','UserX', 'First Name', 'Last Name', 'cicd-cont', 'cicd-use', 'cicd-era']].copy()
                df_val_cloud=df[['Nr','UserX','First Name','Last Name','cloud-k8s','cloud-fiesta','cloud-day2']].copy()


                # Clean out the unneeded rows
                df_val_hc_iaas=df_val_hc_iaas[((df_val_hc_iaas['hc-iaas-snow'] =="Pending") | (df_val_hc_iaas['hc-iaas-snow'] =="In progress")) | ((df_val_hc_iaas['hc-iaas-leap'] =="Pending") | (df_val_hc_iaas['hc-iaas-leap'] =="In progress")) | ((df_val_hc_iaas['hc-iaas-cmdb'] =="Pending") | (df_val_hc_iaas['hc-iaas-cmdb'] =="In progress")) | ((df_val_hc_iaas['hc-iaas-xplay'] =="Pending") | (df_val_hc_iaas['hc-iaas-xplay'] =="In progress"))]
                df_val_db=df_val_db[(df_val_db['hc-db-aav'] == "Pending")| (df_val_db['hc-db-dam'] == "Pending") | (df_val_db['hc-db-mssql'] == "Pending") | (df_val_db['hc-db-ultimate'] == "Pending") | (df_val_db['hc-db-aav'] == "In progress")| (df_val_db['hc-db-dam'] == "In progress") | (df_val_db['hc-db-mssql'] == "In progress") | (df_val_db['hc-db-ultimate'] == "In progress")]
                df_val_euc=df_val_euc[(df_val_euc['hc-euc-prov']=="Pending") | (df_val_euc['hc-euc-calm']=="Pending") | (df_val_euc['hc-euc-flow']=="Pending") | (df_val_euc['hc-euc-prov']=="In progress") | (df_val_euc['hc-euc-calm']=="In progress") | (df_val_euc['hc-euc-flow']=="In progress") ]
                df_val_cicd=df_val_cicd[(df_val_cicd['cicd-cont'] == "Pending") | (df_val_cicd['cicd-use'] == "Pending") | (df_val_cicd['cicd-era'] == "Pending") | (df_val_cicd['cicd-cont'] == "In progress") | (df_val_cicd['cicd-use'] == "In progress") | (df_val_cicd['cicd-era'] == "In progress")]
                df_val_cloud = df_val_cloud[(df_val_cloud['cloud-k8s'] == "Pending") | (df_val_cloud['cloud-fiesta'] == "Pending") | (df_val_cloud['cloud-day2'] == "Pending") | (df_val_cloud['cloud-k8s'] == "In progress") | (df_val_cloud['cloud-fiesta'] == "In progress") | (df_val_cloud['cloud-day2'] == "In progress")]

                # Let's remove the validated and rejected values from the DFs
                df_val_hc_iaas.replace(to_replace='Validated', value="", inplace=True)
                df_val_hc_iaas.replace(to_replace=r'^Rejected.*', value="", regex=True, inplace=True)
                df_val_db.replace(to_replace='Validated', value="", inplace=True)
                df_val_db.replace(to_replace=r'^Rejected.*', value="", regex=True, inplace=True)
                df_val_euc.replace(to_replace='Validated', value="", inplace=True)
                df_val_euc.replace(to_replace=r'^Rejected.*', value="", regex=True, inplace=True)
                df_val_cicd.replace(to_replace='Validated', value="", inplace=True)
                df_val_cicd.replace(to_replace=r'^Rejected.*', value="", regex=True, inplace=True)
                df_val_cloud.replace(to_replace='Validated', value="", inplace=True)
                df_val_cloud.replace(to_replace=r'^Rejected.*', value="", regex=True, inplace=True)

                # Set new indexes on the temp DFs
                df_val_hc_iaas=df_val_hc_iaas.set_index('Nr')
                df_val_db=df_val_db.set_index('Nr')
                df_val_euc=df_val_euc.set_index('Nr')
                df_val_cicd=df_val_cicd.set_index('Nr')
                df_val_cloud=df_val_cloud.set_index('Nr')

                # Create the data into a list so we can forward them to the renderer per lab

                iaas_lst=[]
                if len(df_val_hc_iaas.to_dict()['First Name']) < 1:
                    iaas_lst=[" , , , , , , , "]
                else:
                    for key in df_val_hc_iaas.to_dict()['First Name']:
                        iaas_lst.append(
                                 str(key)+","+str(df_val_hc_iaas.to_dict()['UserX'][key])+","+str(df_val_hc_iaas.to_dict()['First Name'][key])+","+
                                 str(df_val_hc_iaas.to_dict()['Last Name'][key])+","+str(df_val_hc_iaas.to_dict()['hc-iaas-snow'][key])+","+
                                 str(df_val_hc_iaas.to_dict()['hc-iaas-leap'][key])+","+str(df_val_hc_iaas.to_dict()['hc-iaas-cmdb'][key])+","+
                                 str(df_val_hc_iaas.to_dict()['hc-iaas-xplay'][key])+","+str(df_val_hc_iaas.to_dict()['SNOW'][key])
                        )

                db_lst=[]
                if len(df_val_db.to_dict()['First Name']) < 1:
                    db_lst=[" , , , , , , , "]
                else:
                    for key in df_val_db.to_dict()['First Name']:
                        db_lst.append(
                            str(key)+","+str(df_val_db.to_dict()['UserX'][key])+","+str(df_val_db.to_dict()['First Name'][key])+","+
                            str(df_val_db.to_dict()['Last Name'][key])+","+str(df_val_db.to_dict()['hc-db-aav'][key])+","+
                            str(df_val_db.to_dict()['hc-db-dam'][key])+","+str(df_val_db.to_dict()['hc-db-mssql'][key])+","+
                            str(df_val_db.to_dict()['hc-db-ultimate'][key])
                        )

                euc_lst=[]
                if len(df_val_euc.to_dict()['First Name']) < 1:
                    euc_lst = [" , , , , , , , "]
                else:
                    for key in df_val_euc.to_dict()['First Name']:
                        euc_lst.append(
                            str(key)+","+str(df_val_euc.to_dict()['UserX'][key])+","+str(df_val_euc.to_dict()['First Name'][key])+","+
                            str(df_val_euc.to_dict()['Last Name'][key])+","+str(df_val_euc.to_dict()['hc-euc-prov'][key])+","+
                            str(df_val_euc.to_dict()['hc-euc-calm'][key])+","+str(df_val_euc.to_dict()['hc-euc-flow'][key])
                        )


                cicd_lst = []
                if len(df_val_cicd.to_dict()['First Name']) < 1:
                    cicd_lst=[" , , , , , , "]
                else:
                    for key in df_val_cicd.to_dict()['First Name']:
                        cicd_lst.append(
                            str(key) + "," + str(df_val_cicd.to_dict()['UserX'][key])+","+
                            str(df_val_cicd.to_dict()['First Name'][key]) + "," + str(df_val_cicd.to_dict()['Last Name'][key])+","+
                            str(df_val_cicd.to_dict()['cicd-cont'][key])+","+ str(df_val_cicd.to_dict()['cicd-use'][key])+","+
                            str(df_val_cicd.to_dict()['cicd-era'][key])
                        )

                cloud_lst=[]
                if len(df_val_cloud.to_dict()['First Name']) < 1:
                    cloud_lst=[" , , , , , "]
                else:
                    for key in df_val_cloud.to_dict()['First Name']:
                        cloud_lst.append(
                            str(key)+","+str(df_val_cloud['UserX'][key])+","+str(df_val_cloud.to_dict()['First Name'][key])+","+
                            str(df_val_cloud.to_dict()['Last Name'][key])+","+str(df_val_cloud.to_dict()['cloud-k8s'][key])+","+
                            str(df_val_cloud.to_dict()['cloud-fiesta'][key])+","+str(df_val_cloud.to_dict()['cloud-day2'][key])

                        )
                # Render the pages
                return render_template('web_validator.html', iaaslist=iaas_lst,dblist=db_lst,euclist=euc_lst,cicdlist=cicd_lst,cloudlist=cloud_lst,validator=session['validator'])
    else: # We don't have a validated user
        sme_list=df_sme['Name'].tolist()
        info_data={"validated":"No","validator":sme_list}
        return render_template('web_validateme.html', info=info_data, title='vGTS2021 - Validator area')


@app.route("/validateme", methods=['GET','POST'])
def show_form_validateme():
    sme_list = df_sme['Name'].tolist()
    if request.method == "POST":
        reply_post = request.form
        if reply_post['val_password'] == validator_password:
            session['validated'] = "Yes"
            session['validator'] = reply_post['validator']
            info_data ={'validated':'Yes',"validator":sme_list}
            return render_template('web_validateme.html', info=info_data, title='vGTS2021 - Validator area')

        else:
            info_data = {'validated': 'No', "validator":sme_list}
            return render_template('web_validateme.html', info=info_data, title='vGTS2021 - Validator area')

    else:
        info_data = {'validated': 'No', "validator":sme_list}
        return render_template('web_validateme.html', info=info_data, title='vGTS2021 - Validator area')



if __name__ == "main":
    # start the app
    session.pop('email',None)
    app.run()