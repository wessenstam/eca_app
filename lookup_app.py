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

# ****************************************************************************************************************
# Get the needed password for the vlidator pages from the OS envionment
pre_time="No"
aws_port=os.environ['aws_port']
aws_url=os.environ['aws_url']
# ****************************************************************************************************************
# Geting the Forms ready to be used
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    submit = SubmitField('Lookup...')

def send_msq_msg(usernr,lab,progress):
    data="{'usernr':'"+usernr+"','lab':'"+lab+"','progress':'"+progress+"'}"
    json_data=json.dumps(data)
    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=aws_url,port=aws_port))
    channel = connection.channel()
    channel.queue_declare(queue='request')
    channel.basic_publish(exchange='', routing_key='request', body=json_data)
    print(" [x] Sent "+json_data)
    connection.close()

# Function for updating the underlaying GSheet so we can always grab back to the updated version
def update_gsheet_df(usernr):
    # Based on the information we got we need to set some variables to the correct values.
    row = int(usernr) + 1
    fmt = cellFormat(backgroundColor=color(0, 1,0),textFormat=textFormat(foregroundColor=color(0, 0, 0)))
    format_cell_range(wks, "A"+str(row),  fmt)
    # Update Attendee Gsheet
    wks.update_cell(row, col, progress)

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


@app.route("/update_api", methods=['POST'])
def update_api_df():
    send_post_dict=eval(json.loads(request.get_data().decode()))
    usernr=send_post_dict['usernr']
    lab=send_post_dict['lab']
    progress=send_post_dict['progress']
    # Update the DF so the user sees the data
    df.at[int(usernr)-1 , lab] = progress

    return "Received"

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
    df.set_index('Nr')
    
    return render_template('web_update.html', title='vGTS2021 - Cluster lookup')

@app.route("/pre-time", methods=['GET'])
def set_pretime():
    global pre_time
    try:
        request.args['No']
        pre_time="No"
    except:
        pre_time="Yes"

    return render_template('web_pretime.html', pretime=pre_time, title='Pretime changer')

@app.route("/", methods=['GET', 'POST'])
def show_form_data():
    if 'email ' not in session:
        error=''
        form = LoginForm()
        user_data=''

    if form.validate_on_submit() or 'email' in session:
        # We have to make sure that we set the variable of the email address at the right time and way.
        if form.validate_on_submit():
            search_email = [form.email.data.lower()]
            # Set session id
            session['email'] = search_email
        if 'email' in session:
            search_email=session['email']
        # Change the email to a list so we can lowercase and search Case insensitive in the DataFrame
        df_user_info = df[df['Email'].str.lower().isin(search_email)]
        # Change the df into a dict so we can grab the data
        if str(df_user_info):
            user_info = df_user_info.to_dict('records')
            try:
                if pre_time == "Yes":
                    # Green Background on pre-time
                    update_gsheet_df(user_info[0]['Nr'],"","")
                # Assigning the user data to variables that we need to show
                user_data = {'uniq_nr':user_info[0]['Nr'],
                             'attendee_name': user_info[0]['First Name'] + ' ' + user_info[0]['Last Name'],
                             'password': user_info[0]['Password'],
                             'cluster_name': user_info[0]['Cluster Name'],
                             'pe_vip': user_info[0]['IP address VIP'],
                             'pc_vip': user_info[0]['IP address PC'],
                             'prim_network': user_info[0]['Primary Network'],
                             'sec_network':user_info[0]['Secondary Network'],
                             'era_network': user_info[0]['Era Managed network'],
                             'karbon_start': user_info[0]['Karbon IP - Start'],
                             'karbon_stop': user_info[0]['Karbon IP - Stop'],
                             'aws_ip':user_info[0]['AWS-IP'],
                             'snow_instance':user_info[0]['SNOW'],
                             'user_x': user_info[0]['UserX'],
                             'val_hc_snow': user_info[0]['hc-iaas-snow'],
                             'val_hc_leap': user_info[0]['hc-iaas-leap'],
                             'val_hc_cmdb': user_info[0]['hc-iaas-cmdb'],
                             'val_hc_xplay': user_info[0]['hc-iaas-xplay'],
                             'val_hc_db_aav': user_info[0]['hc-db-aav'],
                             'val_hc_db_dam': user_info[0]['hc-db-dam'],
                             'val_hc_db_mssql': user_info[0]['hc-db-mssql'],
                             'val_hc_db_ultimate': user_info[0]['hc-db-ultimate'],
                             'val_hc_euc_prov': user_info[0]['hc-euc-prov'],
                             'val_hc_euc_calm': user_info[0]['hc-euc-calm'],
                             'val_hc_euc_flow': user_info[0]['hc-euc-flow'],
                             'val_cicd_cont': user_info[0]['cicd-cont'],
                             'val_cicd_use': user_info[0]['cicd-use'],
                             'val_cicd_era': user_info[0]['cicd-era'],
                             'val_cloud_k8s': user_info[0]['cloud-k8s'],
                             'val_cloud_fiesta': user_info[0]['cloud-fiesta'],
                             'val_cloud_day2': user_info[0]['cloud-day2'],
                             'pretime':pre_time
                             }           
                form.email.data=""
            except IndexError:
                error = {'message' : 'Unknown email address', 'email' : form.email.data }

    # Send the output to the webbrowser
    return render_template('web_form.html', title='vGTS 2021 - Cluster lookup', user=user_data, form=form, error=error)

@app.route("/validation", methods=['POST'])
def show_form_validation():
    # Get the data from the values that where set and create the reply
    reply_post=request.form
    lab=reply_post['lab']
    username=reply_post['username']
    usernr=reply_post['usernr']
    # Send the message to the message queue for next handling
    send_msq_msg(usernr,lab,"Req Validation")
    # Update the DF so they see the status
    df.at[int(usernr)-1 , lab] = "Requested Validation"

    return render_template('web_validation.html', title='vGTS 2021 - Validation')

if __name__ == "main":
    # start the app
    session.pop('email',None)
    app.run()