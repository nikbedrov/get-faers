import pandas as pd
from pprint import pprint
import matplotlib.pyplot as plt
plt.style.use('fivethirtyeight')
plt.rcParams["figure.figsize"] = (4, 3)
import requests
from urllib.parse import quote
# rate limiting is important to avoid accidental service abuse of the OpenFDA API provider
from ratelimit import limits, sleep_and_retry

OPENFDA_API = "https://api.fda.gov/drug/event.json"

@sleep_and_retry
@limits(calls=40, period=60)
def call_api(params):
    """
    OpenFDA API call. Respects rate limit. Overrides default data limit
    Input: dictionary with API parameters {search: '...', count: '...'}
    Output: nested dictionary representation of the JSON results section
    
    OpenFDA API rate limits:
         With no API key: 40 requests per minute, per IP address. 1000 requests per day, per IP address.
         With an API key: 240 requests per minute, per key. 120000 requests per day, per key.
    """
    if not params:
        params = {}
    params['limit'] = params.get('limit', 1000)
    response = requests.get(OPENFDA_API, params=params)

    if response.status_code != 200:
        raise Exception('API response: {}'.format(response.status_code))
    return response.json()['results']


OPENFDA_METADATA_YAML = "https://open.fda.gov/fields/drugevent.yaml"

from munch import Munch

def api_meta():
    """
    YAML file with field description and other metadata retrieved from the OpenFDA website
    Parses YAML file and provides syntactic sugar for accessing nested dictionaries
    Example: .patient.properties.patientagegroup.possible_values.value
    Note: reserved words, such as count and items still have to be accessed via ['count'], ['items']
    """
    response = requests.get(OPENFDA_METADATA_YAML)
    if response.status_code != 200:
        raise Exception('Could not retrieve YAML file with drug event API fields')
    y = Munch.fromYAML(response.text)
    return y['properties']


drugname = "Nexletol"



#GET A - all cases for drug + event 
df = pd.DataFrame(call_api({
    "count": "patient.drug.medicinalproduct.exact",
    'search':"patient.drug.medicinalproduct:{}".format(drugname)
    }))
df.plot.line('term', 'count', figsize=(5,3))
plt.xlabel("drugs")
plt.ylabel("reports")
plt.gca().axes.get_xaxis().set_ticks([])
plt.gca().get_legend().remove()
plt.show()

df[0:10].plot.barh('term', 'count')
plt.ylabel("drugs")
plt.xlabel("reports")

for index, value in enumerate(df[0:10]['count']):
    plt.text(value, index,
             str(value))

plt.show()

drug_event_A = df

#GET AB - all cases for drug
df = pd.DataFrame(call_api({
    "count": "patient.reaction.reactionmeddrapt.exact",
    'search':"patient.drug.medicinalproduct:{}".format("Nexletol")
    }))
df.plot.line('term', 'count', figsize=(5,3))
plt.xlabel("drugs")
plt.ylabel("reports")
plt.gca().axes.get_xaxis().set_ticks([])
plt.gca().get_legend().remove()
plt.show()

df[0:10].plot.barh('term', 'count')
plt.ylabel("drugs")
plt.xlabel("reports")

for index, value in enumerate(df[0:10]['count']):
    plt.text(value, index,
             str(value))

plt.show()

drug_AB = df

reactions = df['term'].values
reactions_counts = []

def get_counts_for_reaction(reaction):
    """Returns dataframe with yearly tally of event reports for a given reaction"""
    aes_df = pd.DataFrame(call_api({
            "count": "patient.reaction.reactionmeddrapt.exact",
            'search':"patient.reaction.reactionmeddrapt.exact:{}".format(reaction)
    }))
 
    for item in aes_df.iterrows():
        if item[1]["term"].lower() == reaction.lower():
            reactions_counts.append([reaction, item[1]["count"]])
    
    return aes_df

for reaction in reactions:
    reaction = reaction.replace("^", "").replace("/", " ") 
    get_counts_for_reaction(reaction)
    

drug_AC = reactions_counts


print("debug")