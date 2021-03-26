from flask import Flask, Markup, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from natsort import index_natsorted

app = Flask(__name__)

# ****************************************************************************************************************
# Set the needed GSheet credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gts-gsheet-pandas-flask.json',scope)  # Change location as soon as it comes into prod
gc = gspread.authorize(credentials)


@app.route('/')
def bar():
    # ****************************************************************************************************************
    # Grab the data from the SME Gsheet
    wks_sme = gc.open("GTS SME Validations").sheet1
    data = wks_sme.get_all_values()
    headers = data.pop(0)
    # Drop all data in a dataframe for the attendees
    df_sme = pd.DataFrame(data, columns=headers)
    # Cleaning up the lines that have no name
    df_sme.drop(df_sme[df_sme['Name'] == ""].index, inplace=True)
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

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5000)