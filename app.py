# Python Flask server for attendee look up
# Willem Essenstam - Nutanix - 25 May 2020
# Willem Essenstam - Nutanix - 6 Feb 2021
#           Adding the possibility to use validation via the field



from oauth2client.service_account import ServiceAccountCredentials

import json
from flask import *
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
import gspread
import pandas as pd


app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'

# Geting the Forms ready to be used
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    submit = SubmitField('Find me...')

class ValidateForm(FlaskForm):
    # email = StringField('Email Address', validators=[DataRequired()])
    submit = SubmitField('Validate me...')

# Grabbing the initial data from gsheet
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)
wks = gc.open("GTS Clusters-Assignments").sheet1  # get the Gsheet
data = wks.get_all_values()
headers = data.pop(0)
# Drop all data in a dataframe
df = pd.DataFrame(data, columns=headers)

@app.route("/update")
def update_df():
    # Reload the data from the Gsheet
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json', scope)  # Change location as soon as it comes into prod
    gc = gspread.authorize(credentials)
    wks = gc.open("GTS Clusters-Assignments").sheet1  # get the Gsheet
    data = wks.get_all_values()
    headers = data.pop(0)
    # Drop all data in a dataframe
    df.update(pd.DataFrame(data, columns=headers))
    return render_template('web_update.html', title='vGTS2021 - Cluster lookup')

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
                             'user_x': user_info[0]['UserX'],
                             'val_euc': user_info[0]['EUC'],
                             'val_cloud': user_info[0]['CloudNative'],
                             'val_cicd': user_info[0]['CICD'],
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

    # Update the Gsheet in the correct location
    # Write pending in the cell of the workshop vs the usernr
    row=int(usernr)+1
    if "euc" in lab:
        col=27 # Column AA
        df_col="EUC"
    elif "native" in lab:
        col=28 # Column AB
        df_col="Cloud Native"
    else:
        col=29 # Column AC
        df_col="CICD"
    # Update Gsheet
    wks.update_cell(row,col,"Pending")
    # Update the Dataframe, so reread is not needed
    df.at[usernr,df_col]="Pending"

    return render_template('web_validation.html', title='vGTS 2021 - Validation', info=info_data)

@app.route("/validator", methods=['GET','POST'])
def show_form_validator():
    # Do we have a get or a usernr??
    if str(request.args.get('lab')) != 'None':
        usernr=str(request.args.get('usernr'))
        lab=str(request.args.get('lab'))
        if str(request.args.get('validation')) == 'None':
            # Updating the Row to In progress
            row = int(usernr) + 1
            if "euc" in lab:
                col = 27  # Column AA
            elif "native" in lab:
                col = 28  # Column AB
            else:
                col = 29  # Column AC
            wks.update_cell(row, col, "In progress")
            df.at[usernr,'EUC']="In progress"
        return "<H2>" + lab + " validation for usernr "+usernr+"</H2>"

    else:
        # Get all users info: usernr, First Name, Last Name and not completed lab validation, but they must not be empty!
        # Make copies of the existing big DF
        df_val_euc=df[['Nr','First Name','Last Name','EUC']].copy()
        df_val_cloud=df[['Nr','First Name','Last Name','CloudNative']].copy()
        df_val_cicd=df[['Nr','First Name','Last Name','CICD']].copy()

        # Reset the index for the DFs
        df_val_euc=df_val_euc.set_index('Nr')
        df_val_cloud = df_val_cloud.set_index('Nr')
        df_val_cicd = df_val_cicd.set_index('Nr')

        # Clean out the unneeded rows
        df_val_euc=df_val_euc[(df_val_euc.EUC !="")]
        df_val_cloud=df_val_cloud[(df_val_cloud.CloudNative != "")]
        df_val_cicd=df_val_cicd[(df_val_cicd.CICD != "")]

        # Create the data into a list so we can forward them to the renderer
        euc_lst=[]
        for key in df_val_euc.to_dict()['First Name']:
            euc_lst.append(str(key)+","+df_val_euc.to_dict()['First Name'][key]+","+df_val_euc.to_dict()['Last Name'][key]+","+df_val_euc.to_dict()['EUC'][key])

        cloud_lst=[]
        for key in df_val_cloud.to_dict()['First Name']:
            cloud_lst.append(str(key)+","+df_val_cloud.to_dict()['First Name'][key]+","+df_val_cloud.to_dict()['Last Name'][key]+","+df_val_cloud.to_dict()['CloudNative'][key])

        cicd_lst = []
        for key in df_val_cloud.to_dict()['First Name']:
            cicd_lst.append(
                str(key) + "," + df_val_cicd.to_dict()['First Name'][key] + "," + df_val_cicd.to_dict()['Last Name'][
                    key] + "," + df_val_cicd.to_dict()['CICD'][key])

        return render_template('web_validator.html', euclist=euc_lst,cloudlist=cloud_lst,cicdlist=cicd_lst)




if __name__ == "main":
    # start the app
    session.pop('email',None)
    app.run()

