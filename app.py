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

# ****************************************************************************************************************
# We are not pre-time?
pre_time="No"
# ****************************************************************************************************************
# Geting the Forms ready to be used
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    submit = SubmitField('Lookup...')

# Function for updating the underlaying GSheet so we can always grab back to the updated version
def update_gsheet_df(usernr, lab,progress):
    # Based on the information we got we need to set some variables to the correct values.
    row = int(usernr) + 1
    # If the progress is empty, this means people are just getting the data from their lookup page
    if lab == "":
        # We seem to have received no progress so we are to color col 0 (NR) green so we know they tried to get some data
        # Update the GSheet row of the user and col 0
        if pre_time != "No":
            fmt = cellFormat(backgroundColor=color(0, 1,0),textFormat=textFormat(foregroundColor=color(0, 0, 0)))
            format_cell_range(wks, "A"+str(row),  fmt)
    else:
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

        # Update Attendee Gsheet
        wks.update_cell(row, col, progress)
        # Update the DF
        df.at[int(usernr)-1 , lab] = progress
        if progress == "Validated":
            # Update the Validator GSheet and DF_SME if there has been a validated received
            col=col - 14
            col_df=col - 1
            row_sme=int(df_sme[df_sme['Name'] == session['validator']].index[0])
            # Read the value from the DF_SME for the validator
            value=df_sme.iloc[row_sme,col_df]
            if value=="":
                value=0
            value=int(value)+1
            df_sme.iat[row_sme,col_df] = int(value)
            wks_sme.update_cell(row_sme+2, col, value)
        return web_templ


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
wks = gc.open("Clusters-Assignments").sheet1
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

@app.route("/update")
def update_df():
    # Reload the data from the Gsheet
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json', scope)  # Change location as soon as it comes into prod
    gc = gspread.authorize(credentials)
    wks = gc.open("Clusters-Assignments").sheet1  # get the Gsheet
    data = wks.get_all_values()
    headers = data.pop(0)
    # Drop all data in a dataframe for the attendees
    global df
    df = pd.DataFrame(data, columns=headers)
    # Clean up the lines with no email address
    df.drop(df[df['Email'] == ""].index, inplace=True)

    
    return render_template('web_update.html', title='Cluster lookup')

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
                # Assigning the user data to variables that we need to show
                update_gsheet_df(user_info[0]['Nr'],"","")
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
                             'pretime':pre_time
                             }
                form.email.data=""
            except IndexError:
                error = {'message' : 'Unknown email address', 'email' : form.email.data }

    # Send the output to the webbrowser
    return render_template('web_form.html', title='Cluster lookup', user=user_data, form=form, error=error)

if __name__ == "main":
    # start the app
    session.pop('email',None)
    app.run()