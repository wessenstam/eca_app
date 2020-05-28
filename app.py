# Python Flask server for attendee look up
# Willem Essenstam - Nutanix - 25 May 2020



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

# Grabbing the initial data from gsheet
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)
wks = gc.open("ECA-Athena - EMEA").sheet1  # get the Gsheet
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
    wks = gc.open("ECA-Athena - EMEA").sheet1  # get the Gsheet
    data = wks.get_all_values()
    headers = data.pop(0)
    # Drop all data in a dataframe
    df.update(pd.DataFrame(data, columns=headers))
    return render_template('web_update.html', title='HP Nutanix Field Day - Cluster lookup')

@app.route("/", methods=['GET', 'POST'])
def show_form_data():
    # Show the form
    error=''
    form = LoginForm()
    user_data=''

    #
    if form.validate_on_submit():
        # Change the email to a list so we can lowercase and search Case insensitive in the DataFrame
        search_email = [form.email.data.lower()]
        df_user_info = df[df['Email'].str.lower().isin(search_email)]
        # Change the df into a dict so we can grab the data
        if str(df_user_info):
            user_info = df_user_info.to_dict('records')
            try:
                # Assigning the user data to variables that we need to show
                user_data = {'attendee_name': user_info[0]['First Name'] + ' ' + user_info[0]['Last Name'],
                             'password': user_info[0]['Password'],
                             'cluster_name': user_info[0]['Cluster Name'],
                             'pe_vip': user_info[0]['Prism Element VIP'],
                             'pc_vip': user_info[0]['Prism Central IP'],
                             'data_service_ip': user_info[0]['Data Services IP'],
                             'cvm1':user_info[0]['CVM 1'],
                             'cvm2': user_info[0]['CVM 2'],
                             'cvm3': user_info[0]['CVM 3'],
                             'cvm4': user_info[0]['CVM 4'],
                             'ipmi1':user_info[0]['IPMI 1'],
                             'ipmi2': user_info[0]['IPMI 2'],
                             'ipmi3': user_info[0]['IPMI 3'],
                             'ipmi4': user_info[0]['IPMI 4'],
                             'vlan_id': user_info[0]['VLAN ID'],
                             'user_nw_sub': user_info[0]['Network Address/Prefix'],
                             'gw_ip': user_info[0]['Gateway IP'],
                             'dhcp_strt': user_info[0]['DHCP Start'],
                             'dhcp_end': user_info[0]['DHCP End'],
                             'move_vm': user_info[0]['Move VM'],
                             'frame_user': user_info[0]['Frame Username']
                             }

                form.email.data=""
            except IndexError:
                error = {'message' : 'Unknown email address', 'email' : form.email.data }

    # Send the output to the webbrowser
    return render_template('web_form.html', title='HP Nutanix Field Day - Cluster lookup', user=user_data, form=form, error=error)


if __name__ == "main":
    # start the app
    app.run()