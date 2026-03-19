import pandas as pd
from pprint import pprint
# import matplotlib.pyplot as plt
# plt.style.use('fivethirtyeight')
# plt.rcParams["figure.figsize"] = (4, 3)
import requests
from urllib.parse import quote
# rate limiting is important to avoid accidental service abuse of the OpenFDA API provider
from ratelimit import limits, sleep_and_retry
from munch import Munch
from enum import Enum
from collections import defaultdict

#FDA API constants
OPENFDA_API = "https://api.fda.gov/drug/event.json"
OPENFDA_METADATA_YAML = "https://open.fda.gov/fields/drugevent.yaml"

#FDA API functions
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

    if response.status_code == 404:
        print('API response: {}'.format(response.status_code))
        print(f'No results found for the given search term:\n {params}')
        return []
    if response.status_code != 200:
        raise Exception('API response: {}'.format(response.status_code))
    return response.json()['results']

#Exact copy of above without the last part ['results']
@sleep_and_retry
@limits(calls=40, period=60)
def call_api_raw_result(params):
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

    return response.json()

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

class DrugNameType(Enum):
    """
    Enum for drug name type
    """
    MEDICINAL_PRODUCT = 1
    GENERIC_NAME = 2

api_cache = {}

#FDA API Calls

def get_all_cases_for_drug_per_year(drugname, year, drugname_type=DrugNameType.MEDICINAL_PRODUCT):
    drugname = drugname.replace(" ", "+")
    if drugname_type == DrugNameType.MEDICINAL_PRODUCT:
        return call_api({
            "count": "patient.drug.medicinalproduct.exact",
            'search':f'patient.drug.medicinalproduct:"{drugname}" AND receivedate:[{year}0101 TO {year}1231]'
        })
    elif drugname_type == DrugNameType.GENERIC_NAME:
        return call_api({
            "count": "patient.drug.openfda.generic_name.exact",
            'search':f'patient.drug.openfda.generic_name:"{drugname}" AND receivedate:[{year}0101 TO {year}1231]'
        })
    else:
        raise ValueError('Invalid drug name type')


def get_drug_event_count_A_per_year(drugname, year, drugname_type=DrugNameType.MEDICINAL_PRODUCT):   
    drugname = drugname.replace(" ", "+")
    if drugname_type == DrugNameType.MEDICINAL_PRODUCT:
        return call_api({
            "count": "patient.reaction.reactionmeddrapt.exact",
            'search':f'patient.drug.medicinalproduct:"{drugname}" AND receivedate:[{year}0101 TO {year}1231]'
        })
    elif drugname_type == DrugNameType.GENERIC_NAME:
        return call_api({
            "count": "patient.reaction.reactionmeddrapt.exact",
            'search':f'patient.drug.openfda.generic_name:"{drugname}" AND receivedate:[{year}0101 TO {year}1231]'
        })
    else:
        raise ValueError('Invalid drug name type')
    

def add_items(new_items, combined):

    term_to_index = {item['term']: idx for idx, item in enumerate(combined)}
    for item in new_items:
        term = item['term']
        count = item['count']
        if term in term_to_index:
            combined[term_to_index[term]]['count'] += count
        else:
            combined.append({'term': term, 'count': count})


def get_all_cases_for_drug_A(drugname, start_year, end_year, drugname_type=DrugNameType.MEDICINAL_PRODUCT):
    
    all_years_data = []

    for year in range(start_year, end_year + 1):
        data = get_drug_event_count_A_per_year(drugname, year, drugname_type)

        add_items(data, all_years_data)

    df = pd.DataFrame(all_years_data)
    #count = df[df['term'].str.contains(drugname, case=False, na=False)]['count'].sum()
    
    return df


def get_all_cases_for_drug_AB(drugname, start_year, end_year, drugname_type=DrugNameType.MEDICINAL_PRODUCT):
    
    all_years_data = []

    for year in range(start_year, end_year + 1):
        data = get_all_cases_for_drug_per_year(drugname, year, drugname_type)
        all_years_data.extend(data)

    df = pd.DataFrame(all_years_data)
    count = df[df['term'].str.contains(drugname, case=False, na=False)]['count'].sum()
    
    return count




def get_counts_for_reaction(reaction):
        """Returns dataframe with yearly tally of event reports for a given reaction"""
        aes_df = pd.DataFrame(call_api({
                "count": "patient.reaction.reactionmeddrapt.exact",
                'search':'patient.reaction.reactionmeddrapt:"{}"'.format(reaction.replace("^", " ").replace("/", " "))
        }))
    
        for item in aes_df.iterrows():
            if item[1]["term"].lower() == reaction.lower():
                return item[1]["count"]


#Current run parameters
start_year = 2004
end_year = 2026
#drug_names = ["exenatide","liraglutide","lixisenatide","albiglutide","dulaglutide","semaglutide","beinaglutide"]
#drug_names = ["nexletol", "nexlizet"]
#drug_names = ["rezdiffra"]
#drug_names = ["akten"]
#drug_names = ["zunveyl"]
#drug_names = ["soltamox"]
drug_names = ["tamoxifen citrate"]
#drug_names = ["zioptan"]
#drug_names = ["Hydroxyurea"]
drug_type = DrugNameType.MEDICINAL_PRODUCT



#Tests

def deduplicate_by_caseid_fda_dt(df):
    """
    Deduplicate FAERS data:
    - Parse FDA_DT to datetime (latest receive date).
    - Per CASEID, keep row with max FDA_DT (most recent version).
    - Ties broken by max PRIMARYID.
    """
    df['fda_dt_parsed'] = pd.to_datetime(df['fda_dt'], errors='coerce')
    df = df.dropna(subset=['fda_dt_parsed'])  # Drop invalid dates
    
    # Sort descending by FDA_DT then PRIMARYID (numeric)
    df['primaryid_num'] = pd.to_numeric(df['primaryid'], errors='coerce')
    df_sorted = df.sort_values(['caseid', 'fda_dt_parsed', 'primaryid_num'], ascending=[True, False, False])
    
    # Deduplicate: keep first (latest) per CASEID
    dedup_df = df_sorted.drop_duplicates(subset=['caseid'], keep='first')
    
    # Cleanup
    dedup_df.drop(['fda_dt_parsed', 'primaryid_num'], axis=1, inplace=True)
    return dedup_df











if __name__ == "__main__":
    
    all_cases_ABCD = call_api_raw_result({"limit": 1})['meta']['results']['total']

    result = call_api({
            'search':f'patient.drug.medicinalproduct:"soltamox" AND receivedate:[20230101 TO 20231231]'
        })



    demo_df = pd.json_normalize(result)

    dedupe = deduplicate_by_caseid_fda_dt(demo_df)









    

    for drug_name in drug_names:

        all_cases_for_drug_AB_count = get_all_cases_for_drug_AB(drug_name, start_year, end_year, drug_type)

        #GET A - all cases for drug + event 
        drug_event_A = pd.DataFrame(get_all_cases_for_drug_A(drug_name, start_year, end_year, drug_type))

        reactions = drug_event_A['term'].values
        #reactions = drug_event_A['term'].values[:20]

        reactions_counts = []

        for reaction in reactions:

            cache_key = reaction
            if cache_key in api_cache:
                reaction_total_count = api_cache[cache_key]
                reactions_counts.append([reaction, reaction_total_count])
                print("Added from cache", reaction.lower())
            else:
                reaction_total_count = get_counts_for_reaction(reaction)
                reactions_counts.append([reaction, reaction_total_count])
                api_cache[cache_key] = reaction_total_count
                print("Added from API", reaction.lower())

            
        drug_AC = dict(reactions_counts)


        stats_df = pd.DataFrame(columns=["Drug Name", "PT Name", "A", "AB", "AC", "ABCD"])

        for index, drugevent in enumerate(drug_event_A.values):
            ac_count = drug_AC.get(drugevent[0]) 
            row = (drug_name, drugevent[0], drugevent[1], all_cases_for_drug_AB_count, ac_count, all_cases_ABCD )
            stats_df.loc[index] = row

        stats_df.to_csv(f"FAERS_{drug_name}.csv", index=False)


#Sort out this script 
#1. Make the api request type optional - medicinal product or generic name
#2. Make the count for the AB iterate all years.
#3. Cleanup the code and make it reusable.




