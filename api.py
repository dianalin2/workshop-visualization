import pandas as pd
import glob
import ast
import datetime
import environ
import requests
import zipfile
import io
import os

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

def refresh():
    if not os.path.exists('data/workshops'):
        os.makedirs('data/workshops')
    if not os.path.exists('data/registrations'):
        os.makedirs('data/registrations')
    if not os.path.exists('data/surveys'):
        os.makedirs('data/surveys')

    global workshop_data, survey_data
    workshop_data = process_workshop_data(pull_workshop_data(), pull_registration_data())
    survey_data = pull_survey_data()
    return workshop_data, survey_data
