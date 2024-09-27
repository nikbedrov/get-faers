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


# df = pd.DataFrame(call_api({"count": "patient.drug.activesubstance.activesubstancename.exact"}))
# df.plot.line('term', 'count', figsize=(5,3))
# plt.xlabel("drugs")
# plt.ylabel("reports")
# plt.gca().axes.get_xaxis().set_ticks([])
# plt.gca().get_legend().remove()
# plt.show()

# df[0:10].plot.barh('term', 'count')
# plt.ylabel("drugs")
# plt.xlabel("reports")

# plt.show()


# from wordcloud import WordCloud

# def show_wordcount(words, background="black", color="viridis"):
#     wc = WordCloud(
#         background_color=background,
#         max_words=50,
#         max_font_size=30,colormap=color
#     )
#     image = wc.generate_from_frequencies(words)

#     plt.figure(figsize=(10,6))
#     plt.imshow(image, interpolation="bilinear")
#     plt.axis("off")
#     plt.show()


# counts = call_api({
#     "count": "patient.drug.activesubstance.activesubstancename.exact"})
# words = { d['term'].capitalize(): d['count'] for d in counts }
# show_wordcount(words)


# def get_trend_for_reaction(reaction):
#     df = pd.DataFrame(
#         call_api({
#             'count':'receivedate',
#             'search': "receivedate:[20040101 TO 20240630] AND patient.reaction.reactionmeddrapt.exact: {}".format(reaction.upper()
#             )}))
#     df.index = pd.to_datetime(df.time)
#     df = df.drop('time', axis=1).resample("y").sum().rename(
#         columns={"count": reaction.capitalize()}
#     )
#     return df

# reactions = ['death', 'pain', 'dyspnoea']
# df = pd.concat([get_trend_for_reaction(x) for x in reactions], axis=1)
# df.plot(style='o-', figsize=(5,3))
# plt.show()



# df = pd.DataFrame(call_api({"count":"serious"}))
# meta = pd.Series(api_meta().serious.possible_values.value).to_frame("Seriousness")

# meta["term"] = meta.index.astype(int)
# meta["Seriousness"] = list(map(lambda x: x[0:55], meta["Seriousness"]))

# df.merge(meta, on='term').plot.barh('Seriousness', 'count')
# plt.xlabel("reports")
# plt.gca().get_legend().remove()
# plt.show()

# #Reported drug role - suspect, concomitant etc.
# df = pd.DataFrame(call_api({
#     "count": "patient.drug.drugcharacterization",
#     }))

# meta = pd.Series(
#             api_meta().patient.properties.drug['items'].properties.drugcharacterization.possible_values.value
#        ).to_frame('reported drug role')
# meta['term'] = meta.index.astype(int)

# df.merge(meta, on='term').plot.barh('reported drug role', 'count')
# plt.xlabel("reports")
# plt.gca().get_legend().remove()
# plt.show()

#"search": "patient.drug.medicinalproduct:NEXLETOL"


#GET A - all cases for drug + event 
df = pd.DataFrame(call_api({
    "count": "patient.drug.medicinalproduct.exact",
    'search':
                # "patient.drug.drugcharacterization: {} AND "
                # "patient.drug.drugadditional: {} AND "
                # "patient.drug.drugrecurreadministration: {} "
                "patient.drug.medicinalproduct:{}"
                #"serious: {}"
                #"reporttype: {} "
                "".format("Nexletol")#, 2)
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




#GET AB - all cases for drug
df = pd.DataFrame(call_api({
    "count": "patient.reaction.reactionmeddrapt.exact",#"patient.drug.medicinalproduct.exact",
    'search':
                # "patient.drug.drugcharacterization: {} AND "
                # "patient.drug.drugadditional: {} AND "
                # "patient.drug.drugrecurreadministration: {} "
                "patient.drug.medicinalproduct:{}"
                #"serious: {}"
                #"reporttype: {} "
                "".format("Nexletol")#, 2)
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




reactions = df['term'].values
reactions_counts = []


def get_counts_for_reaction(reaction):
    """Returns dataframe with yearly tally of event reports for a given reaction"""
    aes_df = pd.DataFrame(call_api({
            "count": "patient.reaction.reactionmeddrapt.exact",#"patient.drug.medicinalproduct.exact",
            'search':
                # "patient.drug.drugcharacterization: {} AND "
                # "patient.drug.drugadditional: {} AND "
                # "patient.drug.drugrecurreadministration: {} "
                "patient.reaction.reactionmeddrapt.exact:{}"
                #"serious: {}"
                #"reporttype: {} "
                "".format(reaction)#, 2)
    }))
 
    for item in aes_df.iterrows():
        if item[1]["term"].lower() == reaction.lower():
            reactions_counts.append([reaction, item[1]["count"]])
            

    
    return aes_df

#df = pd.concat([get_counts_for_reaction(x) for x in reactions], axis=1)

for reaction in reactions:
    reaction = reaction.replace("^", "").replace("/", " ") 
    get_counts_for_reaction(reaction)
    

print(reactions_counts)


# #GET AC - all cases for event / pt
# df = pd.DataFrame(call_api({
#     "count": "patient.reaction.reactionmeddrapt.exact",#"patient.drug.medicinalproduct.exact",
#     'search':
#                 # "patient.drug.drugcharacterization: {} AND "
#                 # "patient.drug.drugadditional: {} AND "
#                 # "patient.drug.drugrecurreadministration: {} "
#                 "patient.drug.medicinalproduct:{}"
#                 #"serious: {}"
#                 #"reporttype: {} "
#                 "".format("Nexletol")#, 2)
#     }))
# df.plot.line('term', 'count', figsize=(5,3))
# plt.xlabel("drugs")
# plt.ylabel("reports")
# plt.gca().axes.get_xaxis().set_ticks([])
# plt.gca().get_legend().remove()
# plt.show()

# df[0:10].plot.barh('term', 'count')
# plt.ylabel("drugs")
# plt.xlabel("reports")

# for index, value in enumerate(df[0:10]['count']):
#     plt.text(value, index,
#              str(value))

# plt.show()


















# from tqdm import tqdm
# adr = []
# # load only the first 100 pages by 100 reports = 10,000 events
# for page in tqdm(range(100)):
#     try:
#         d = call_api({
#             'count':'patient.drug.medicinalproduct.exact',
#             'search':
#                 # "patient.drug.drugcharacterization: {} AND "
#                 # "patient.drug.drugadditional: {} AND "
#                 # "patient.drug.drugrecurreadministration: {} "
#                 #"patient.drug.drugindication.exact:{} AND "
#                 "patient.drug.medicinalproduct:{}"
#                 #"serious: {} AND "
#                 #"reporttype: {} "
#                 "".format("Nexletol"),
#             'limit': 100,
#             'skip': page
#         })
#     except:
#         raise
#         break
#     adr += d
# print("Total ADR events loaded", len(adr))

# drugs_adr_list = []
# for event in adr:
#     # There is no way to determine what drug caused what reaction from the report
#     # Thus, we consider all combinations
#     for d in event['patient']['drug']:
#         if not d.get('activesubstance'):
#             continue
#         drug = d['activesubstance']['activesubstancename'] 
#         for r in event['patient']['reaction']:
#             reaction = r.get('reactionmeddrapt')
#             drugs_adr_list.append({
#                 'drug': drug,
#                 'adr': reaction,
#             })
# drugs_adr_df = pd.DataFrame(drugs_adr_list)
# print(drugs_adr_df.head())
# drugs_adr = pd.crosstab(drugs_adr_df.drug, drugs_adr_df.adr)
# print(drugs_adr)


# import numpy as np

# def make_contingency_table(drugs_adr, drug, adr):
#     """ 
#         Contingency table:

#         a = Reports with the suspected drug and suspected ADR
#         b = Reports with the suspected drug and without the suspected ADR

#         c = All other reports with the suspected ADR
#         d = All other reports without the suspected ADR    
#     """
#     a = drugs_adr.loc[drug, adr]
#     b = drugs_adr.loc[drug, :].sum() - a
#     c = drugs_adr.loc[:, adr].sum() - a
#     d = drugs_adr.sum().sum() - a - b - c
#     return a, b, c, d



# def ROR_test(contingency_table):
#     """
#     Reporting odds ratio test
    
#     Stricker BHCh, Tijssen JGP. Serum sickness-like reactions to cefaclor. J Clin Epidemiol 1992; 45: 1177–1184.
#     """
#     a, b, c, d = contingency_table
#     # none of the values is allowed to be zero
#     assert a * b * c * d > 0
#     ror = (a*d) / (b*c)
#     se_lnror = np.sqrt(1/a + 1/b + 1/c + 1/d)
#     # 95% CI
#     return np.round(
#         np.exp(np.log(ror) - 1.96*se_lnror), 4)

# def PRR_test(contingency_table):
#     """
#     Proportional ADR reporting ratio (PRR)
    
#     Greenland S, Rothman KJ. Introduction to categorical statistics. Greenland S, Rothman KJ (eds). In Modern Epidemiology (2nd
# edn), Lippincott-Raven: Philadelphia, 2001; 231–252.
#     """
#     a, b, c, d = contingency_table
#     # a or c are not allowed to be zero
#     assert a * c > 0
#     prr = (a / (a + b))  / (c / (c + d)) 
#     se_lnprr = np.sqrt(1/a - 1/(a+b) + 1/c + 1/(c+d))
#     return np.round(
#         np.exp(np.log(prr) - 1.96*se_lnprr), 4)


# contingency_table = make_contingency_table(drugs_adr, "BEMPEDOIC ACID", "Nausea")
# print(contingency_table)
# print("ROR > 1:", ROR_test(contingency_table))
# print("PRR > 1:", PRR_test(contingency_table))

print("debug")