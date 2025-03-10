from flask import Flask
import pandas as pd
import glob
import ast

app = Flask(__name__)

workshop_data = pd.DataFrame()
for file in glob.glob('data/workshops/*.csv'):
    workshop_data = pd.concat([workshop_data, pd.read_csv(file)])

registration_data = pd.DataFrame()
for file in glob.glob('data/registrations/*.csv'):
    registration_data = pd.concat([registration_data, pd.read_csv(file)])

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
workshop_data = workshop_data.drop(columns=['has_registration_opened', 'has_registration_closed', 'status', 'cal_type', 'online_join_url', 'online_join_password', 'registration', 'wait_list', 'online_meeting_id'])

# create tags manually
tags = {
    'Python': ['python', 'pandas', 'numpy', 'scipy', 'matplotlib'],
    'MATLAB': ['matlab'],
    'SQL': ['sql'],
    'Deep Learning': ['deep learning'],
    'Machine Learning': ['machine learning', 'deep learning', 'scikit-learn', 'tensorflow', 'keras'],
    'Containers': ['docker', 'kubernetes', 'container'],
    'Slurm': ['slurm'],
    'CLI': ['command line', 'cli', 'shell scripting'],
}


# add tags to data based on title and description
workshop_data['tags'] = workshop_data['description'].str.split('Prerequisites:').str[0]
workshop_data['tags'] = workshop_data['title'].str.lower() + ' ' + workshop_data['tags'].str.lower()
workshop_data['tags'] = workshop_data['tags'].apply(lambda x: [tag for tag, keywords in tags.items() if any(keyword in x for keyword in keywords)])

workshop_data['category'] = workshop_data['category'].apply(lambda x: [y['name'] for y in ast.literal_eval(x)])
workshop_data['category'] = workshop_data['category'].apply(lambda x: [y for y in x if y not in set(['Data Workshop > Research Computing Data Workshop', 'Data Workshop', 'Workshop'])])

workshop_data['tags'] = list(workshop_data['tags'] + workshop_data['category'])

app.static_folder = 'public'

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/data')
def data():
    return workshop_data.to_json(orient='records')

if __name__ == '__main__':
    app.run(debug=True)
