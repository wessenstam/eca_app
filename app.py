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
import os
from datetime import timedelta

validator_password=os.environ['validator_password']

# Geting the Forms ready to be used
class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired()])
    submit = SubmitField('Lookup...')

def update_gsheet_df(usernr, lab,progress):
    # Based o the information we got we need to set some variables to the correct values.
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

    # Update Gsheet
    wks.update_cell(row, col, progress)
    # Update the DF
    df.iat[int(usernr) - 1, int(col) - 1] = progress

    return web_templ

# Some Flask settings
app = Flask(__name__)
app.config['SECRET_KEY'] = 'you-will-never-guess'

# Grabbing the initial data from gsheet
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)
wks = gc.open("GTS Clusters-Assignments").sheet1  # get the Gsheet
data = wks.get_all_values()
headers = data.pop(0)
# Drop all data in a dataframe
df = pd.DataFrame(data, columns=headers)

# Area for definition of variables
lab_type_lst=["snow","leap","cmdb","xplay","aav","dam","mssql","ultimate","prov","calm","flow","cont","use","era","k8s","fiesta","day2"]

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=8)

@app.route('/logout')  
def logout():  
    error = ""
    form = LoginForm()
    user_data = ""
    if 'email' in session:  
        session.pop('email',None)  
        return render_template('web_loged_out.html')
    else:  
        return render_template('web_loged_out.html')

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
                             'pretime':'no'
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
    df.iat[int(usernr)-1,int(col)-1]="Pending"


    return render_template('web_validation.html', title='vGTS 2021 - Validation', info=info_data)

@app.route("/validator", methods=['GET','POST'])
def show_form_validator():

    if "validated" in session:

        if request.method =="POST":
            reply_post = request.form
            webdata={'username':reply_post['username'],
                     'labname':reply_post['labname']
                     }

            # Have the data updated
            update_gsheet_df(int(reply_post['usernr']),reply_post['labname'],"Validated")

            return render_template('web_validation_received.html',info=webdata, title='vGTS2021 - Validator area')
        else:
            # Do we have a usernr where we need to get the correct info from??
            if str(request.args.get('lab')) != 'None':
                usernr=str(request.args.get('usernr'))
                labname=str(request.args.get('lab'))
                
                # Have the data updated and get the returned info for the webpage
                web_templ=update_gsheet_df(int(usernr), labname, "In progress")

                # Get all information from the DF for the user
                dict_user = df.iloc[int(usernr)-1].to_dict()

                # Are we lloking for SNOW validation?
                if str(request.args.get('snow_instance')):
                    snow_instance=str(request.args.get('lab'))
                    user_values={'username':dict_user['First Name']+" "+dict_user['Last Name'],
                                'clustername': dict_user['Cluster Name'],
                                'clusterip': dict_user['IP address VIP'],
                                'pc_ip':dict_user['IP address PC'],
                                'usernr':dict_user['Nr'],
                                'userx': dict_user['UserX'],
                                'snow_instance': dict_user['SNOW'],
                                'labname': labname
                                }

                else:
                    user_values={'username':dict_user['First Name']+" "+dict_user['Last Name'],
                                'clustername': dict_user['Cluster Name'],
                                'clusterip': dict_user['IP address VIP'],
                                'pc_ip':dict_user['IP address PC'],
                                'usernr':dict_user['Nr'],
                                'userx': dict_user['UserX'],
                                'labname': labname
                                }

                return render_template(web_templ, title='vGTS2021 - Validator area', user=user_values)

            else:
                # Get all users info: usernr, First Name, Last Name and Pending status lab validation, but they must not be empty!
                # Make copies of the existing big DF
                df_val_hc_iaas=df[['Nr','UserX','First Name','Last Name','hc-iaas-snow','hc-iaas-leap','hc-iaas-cmdb','hc-iaas-xplay','SNOW']].copy()
                df_val_db=df[['Nr','UserX','First Name','Last Name','hc-db-aav','hc-db-dam','hc-db-mssql','hc-db-ultimate']].copy()
                df_val_euc=df[['Nr','UserX','First Name','Last Name','hc-euc-prov','hc-euc-calm','hc-euc-flow']].copy()
                df_val_cicd = df[['Nr','UserX', 'First Name', 'Last Name', 'cicd-cont', 'cicd-use', 'cicd-era']].copy()
                df_val_cloud=df[['Nr','UserX','First Name','Last Name','cloud-k8s','cloud-fiesta','cloud-day2']].copy()


                # Clean out the unneeded rows
                df_val_hc_iaas=df_val_hc_iaas[(df_val_hc_iaas['hc-iaas-snow'] !="") | (df_val_hc_iaas['hc-iaas-leap'] !="") | (df_val_hc_iaas['hc-iaas-cmdb'] !="") | (df_val_hc_iaas['hc-iaas-xplay'] !="")]
                df_val_db=df_val_db[(df_val_db['hc-db-aav'] != "")| (df_val_db['hc-db-dam'] != "") | (df_val_db['hc-db-mssql'] != "") | (df_val_db['hc-db-ultimate'] != "")]
                df_val_euc=df_val_euc[(df_val_euc['hc-euc-prov']!="") | (df_val_euc['hc-euc-calm']!="") | (df_val_euc['hc-euc-flow']!="")]
                df_val_cicd=df_val_cicd[(df_val_cicd['cicd-cont'] != "") | (df_val_cicd['cicd-use'] != "") | (df_val_cicd['cicd-era'] != "")]
                df_val_cloud = df_val_cloud[(df_val_cloud['cloud-k8s'] != "") | (df_val_cloud['cloud-fiesta'] != "") | (df_val_cloud['cloud-day2'] != "")]

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
                return render_template('web_validator.html', iaaslist=iaas_lst,dblist=db_lst,euclist=euc_lst,cicdlist=cicd_lst,cloudlist=cloud_lst)
    else: # We don;t have a validated user
        return render_template('web_validateme.html', info="No", title='vGTS2021 - Validator area')


@app.route("/validateme", methods=['GET','POST'])
def show_form_validateme():
    if request.method == "POST":
        reply_post = request.form
        print(reply_post['val_password'])
        if reply_post['val_password'] == validator_password:
            session['validated'] = "Yes"
            return render_template('web_validateme.html', info="Yes", title='vGTS2021 - Validator area')

        else:
            return render_template('web_validateme.html', info="No", title='vGTS2021 - Validator area')

    else:
        return render_template('web_validateme.html', info="No", title='vGTS2021 - Validator area')



if __name__ == "main":
    # start the app
    session.pop('email',None)
    app.run()

