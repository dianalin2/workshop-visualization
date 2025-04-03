from flask import Flask
import pandas as pd
import glob
import ast
import datetime
import environ
import requests
import zipfile
import io

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env()

from libcal.libcalapi import get_RCeventsforAllTimes, timeframe, rds_cal_id, general_rc_category_id, hsl_rc_cal_id, hsl_rc_category_id, unique_ordered, registration_fields, get_multiple_registrations, non_numeric

qualtrics_api_token = env("QUALTRICS_API_TOKEN")
qualtrics_url_base = env("QUALTRICS_URL_BASE")
qualtrics_survey_id = env("QUALTRICS_SURVEY_ID")


def pull_survey_data():
    # Step 1: Creating Data Export
    base_url = f'{qualtrics_url_base}/API/v3/surveys/{qualtrics_survey_id}/export-responses/'
    api_headers = {
        'X-API-TOKEN': qualtrics_api_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.post(
        base_url,
        headers=api_headers,
        data='{"format": "csv"}'
    )
    progress_id = response.json()["result"]["progressId"]

    # Setting static parameters
    progress_status = "inProgress"

    # Step 2: Checking on Data Export Progress and waiting until export is ready
    while progress_status != "complete" and progress_status != "failed":
        response = requests.request("GET", base_url + progress_id, headers=api_headers)
        res = response.json()["result"]
        progress_status = res["status"]

    #step 2.1: Check for error
    if progress_status == "failed":
        raise Exception("Export failed. Check your API token and survey ID.")

    # Step 3: Downloading file
    request_download = requests.request("GET", base_url + res['fileId'] + '/file', headers=api_headers, stream=True)

    # Step 4: Unzipping the file
    zipfile.ZipFile(io.BytesIO(request_download.content)).extractall("data/surveys/")

    # Step 5: Reading the CSV file
    csv_files = glob.glob("data/surveys/*.csv")

    if len(csv_files) == 0:
        raise Exception("No CSV file found in the unzipped folder.")

    survey_data = pd.read_csv(csv_files[0])

    return survey_data

app = Flask(__name__)

def pull_registration_data(begin="2024-01-01"):
    start, end, days = timeframe(begin, datetime.datetime.now().strftime("%Y-%m-%d"))
    evt_fields = ["id", "title", "description","start", "end", "presenter"]
    fields = unique_ordered([], evt_fields, registration_fields)
    
    libcal_df = get_RCeventsforAllTimes(
        cal_type="libcal",
        cal_id=rds_cal_id,
        cat_id=general_rc_category_id,
        start=start,
        days=days,
        fields=fields,
    )

    hsl_df = get_RCeventsforAllTimes(
        cal_type="hsl",
        cal_id=hsl_rc_cal_id,
        cat_id=hsl_rc_category_id,
        start=start,
        days=days,
        fields=fields,
    )
    
    combined_df = pd.concat([libcal_df, hsl_df], ignore_index=True)

    event_ids = list(zip(combined_df["id"].values, combined_df["cal_type"].values))

    # DataFrame with registrations, optional: filter by user
    reg_df = get_multiple_registrations(event_ids, fields=fields)

    non_numeric_df = non_numeric(combined_df)
    reg_df = pd.merge(reg_df, non_numeric_df, left_on="event_id", right_on="id", how="inner", copy=False)

    reg_df.to_csv(f'data/registrations/{begin}-{datetime.datetime.now().strftime("%Y-%m-%d")}.csv')

    return reg_df

def pull_workshop_data(begin="2024-01-01"):
    start, end, days = timeframe(begin, datetime.datetime.now().strftime("%Y-%m-%d"))
    libcal_df = get_RCeventsforAllTimes(
        cal_type="libcal",
        cal_id=rds_cal_id,
        cat_id=general_rc_category_id,
        start=start,
        days=days,
    )

    hsl_df = get_RCeventsforAllTimes(
        cal_type="hsl",
        cal_id=hsl_rc_cal_id,
        cat_id=hsl_rc_category_id,
        start=start,
        days=days,
    )

    combined_df = pd.concat([libcal_df, hsl_df], ignore_index=True)

    # filter out duplicate workshops
    combined_df = combined_df.drop_duplicates(subset='id')

    combined_df.to_csv(f'data/workshops/{begin}-{datetime.datetime.now().strftime("%Y-%m-%d")}.csv')

    return combined_df

def get_registration_data():
    registration_data = pd.DataFrame()
    for file in glob.glob('data/registrations/*.csv'):
        registration_data= pd.concat([registration_data, pd.read_csv(file)])
    return registration_data

def get_workshop_data():
    workshop_data = pd.DataFrame()
    for file in glob.glob('data/workshops/*.csv'):
        workshop_data = pd.concat([workshop_data, pd.read_csv(file)])
    # filter out duplicate workshops
    workshop_data = workshop_data.drop_duplicates(subset='id')
    return workshop_data

def get_survey_data():
    survey_data = pd.DataFrame()

    for file in glob.glob('data/surveys/*.csv'):
        survey_data = pd.concat([survey_data, pd.read_csv(file)])
    
    return survey_data

def process_workshop_data(workshop_data, registration_data):
    # filter out duplicate registrations. if there is a duplicate, keep the one with 1.0 attendance
    registration_data = registration_data.sort_values(by='attendance', ascending=False)
    registration_data = registration_data.drop_duplicates(subset='booking_id')

    workshop_data = workshop_data[workshop_data['start'] >= '2024-01-01']

    # add list of registrations to each workshop
    workshop_data['registrations'] = workshop_data['id'].apply(lambda x: registration_data[registration_data['id'] == x].to_dict(orient='records'))
    workshop_data['attendees'] = workshop_data['registrations'].apply(lambda x: [y for y in x if y['attendance'] == 1])
    workshop_data['attendance'] = workshop_data['attendees'].apply(lambda x: len(x))

    # drop 0 attendance workshops
    # workshop_data = workshop_data[workshop_data['attendance'] > 0]

    # sort by start date
    workshop_data = workshop_data.sort_values(by='start')

    # remove column for status and cal_type
    workshop_data = workshop_data.drop(columns=['has_registration_opened', 'has_registration_closed', 'status', 'cal_type', 'online_join_url', 'online_join_password', 'registration', 'wait_list', 'online_meeting_id'], errors='ignore')

    # create tags manually
    tags = {
        'Python': ['python', 'pandas', 'numpy', 'scipy', 'matplotlib'],
        'Matlab': ['matlab'],
        'SQL': ['sql'],
        'Deep Learning': ['deep learning'],
        'Machine Learning': ['machine learning', 'deep learning', 'scikit-learn', 'tensorflow', 'keras'],
        'Containers': ['docker', 'kubernetes', 'container'],
        'Slurm': ['slurm'],
        'CLI': ['command line', 'cli', 'shell scripting'],
        'HPC Core': ['11890719', '11890924', '12423016', '12423080', '12889799', '13832854', '13838434'],
        'Bioinformatics': ['bioinformatics', 'drug discovery'],
    }


    # add tags to data based on title and description
    workshop_data['tags'] = workshop_data['description'].str.split('Prerequisites:').str[0]
    workshop_data['tags'] = workshop_data['title'].str.lower() + ' ' + workshop_data['tags'].str.lower() + ' ' + workshop_data['id'].astype(str)
    workshop_data['tags'] = workshop_data['tags'].apply(lambda x: [tag for tag, keywords in tags.items() if any(keyword in x for keyword in keywords)])

    workshop_data['category'] = workshop_data['category'].apply(lambda x: [y['name'] for y in ast.literal_eval(str(x))])
    workshop_data['category'] = workshop_data['category'].apply(lambda x: [y for y in x if y not in set(['Data Workshop > Research Computing Data Workshop', 'Data Workshop', 'Workshop'])])

    workshop_data['tags'] = list(workshop_data['tags'] + workshop_data['category'])

    return workshop_data

def process_survey_data(survey_data):

    # drop first row
    survey_data = survey_data.iloc[1:]

    # drop where Q2A is RC
    survey_data = survey_data[survey_data['Q2A'] != 'RC']

    # drop status and ip address
    survey_data = survey_data.drop(columns=['Status', 'IPAddress', 'StartDate', 'EndDate', 'Progress', 'RecordedDate', 'Duration (in seconds)', 'RecipientLastName', 'RecipientFirstName', 'RecipientEmail', 'ExternalReference', 'LocationLatitude', 'LocationLongitude', 'DistributionChannel', 'UserLanguage'])

    # if Q1 = 'Other', set Q1 = Q1A
    survey_data['Q1'] = survey_data.apply(lambda x: x['Q1A'] if x['Q1'] == 'Other' else x['Q1'], axis=1)

    # if Q2 = 'Other', set Q2 = Q2A
    survey_data['Q2'] = survey_data.apply(lambda x: x['Q2A'] if x['Q2'] == 'Other' else x['Q2'], axis=1)

    survey_data = survey_data.drop(columns=['Q1A', 'Q2A'])

    return survey_data

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
    global workshop_data, registration_data
    workshop_data = pull_workshop_data()
    registration_data = pull_registration_data()
    workshop_data = process_workshop_data(workshop_data, registration_data)
    return workshop_data, registration_data

@app.route('/refresh')
def refresh_route():
    global last_refresh
    # if (datetime.datetime.now() - last_refresh).days < 1:
    #     return 'Data was refreshed in the past 24 hours!'

    last_refresh = datetime.datetime.now()

    refresh()
    return 'Refreshed data!'
    # return workshop_data, registration_data
# survey_data = pull_survey_data()
# survey_data = get_survey_data()

# workshop_data, registration_data = refresh()
workshop_data = process_workshop_data(get_workshop_data(), get_registration_data())
survey_data = get_survey_data()

if len(workshop_data) == 0:
    refresh()

if __name__ == '__main__':
    app.run(debug=True)
