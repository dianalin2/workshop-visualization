from flask import Flask
import pandas as pd
import datetime
from api import pull_workshop_data, pull_registration_data, pull_survey_data, process_workshop_data, process_survey_data, get_workshop_data, get_registration_data, get_survey_data

app = Flask(__name__)

app.static_folder = 'public'

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/survey')
def survey_page():
    return app.send_static_file('survey.html')

@app.route('/data/workshop')
def workshop():
    return workshop_data.to_json(orient='records')

@app.route('/data/survey')
def survey():
    return survey_data.to_json(orient='records')

@app.route('/data/survey/topics')
def topics():
    # print all responses to Q3 where the response is not 'NaN' or 'Other'
    q3 = survey_data['Q3'].dropna()
    q3 = q3[q3 != 'Other']

    # split the responses by commas not proceeded by a space
    q3 = q3.str.split(r',(?!\s)').explode()

    # append all responses to Q3 where the response is not 'NaN'
    q3a = survey_data['Q3A'].dropna()
    q3 = pd.concat([q3, q3a])

    # count the number of occurrences of each response
    return q3.value_counts().to_json()

@app.route('/data/survey/positions')
def positions():
    # print all responses to Q3 where the response is not 'NaN' or 'Other'
    q1 = survey_data['Q1'].dropna()

    return q1.value_counts().to_json()

@app.route('/data/survey/departments')
def departments():
    # print all responses to Q3 where the response is not 'NaN' or 'Other'
    q2 = survey_data['Q2'].dropna()

    return q2.value_counts().to_json()

last_refresh = datetime.datetime.now()

def refresh():
    global workshop_data, survey_data
    workshop_data = process_workshop_data(pull_workshop_data(), pull_registration_data())
    survey_data = pull_survey_data()
    return workshop_data, survey_data

@app.route('/refresh')
def refresh_route():
    global last_refresh
    if (datetime.datetime.now() - last_refresh).days < 1:
        return { 'msg': 'Data was refreshed in the past 24 hours!', 'refreshed': False }

    last_refresh = datetime.datetime.now()

    refresh()
    return { 'msg': 'Refreshed data!', 'refreshed': True }

workshop_data = process_workshop_data(get_workshop_data(), get_registration_data())
survey_data = process_survey_data(get_survey_data())

if len(workshop_data) == 0:
    refresh()

if __name__ == '__main__':
    app.run(debug=True)
