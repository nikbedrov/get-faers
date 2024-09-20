import pandas as pd
from pprint import pprint
import matplotlib.pyplot as plt
plt.style.use('fivethirtyeight')
plt.rcParams["figure.figsize"] = (4, 3)
import requests

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


df = pd.DataFrame(call_api({"count": "patient.drug.activesubstance.activesubstancename.exact"}))
df.plot.line('term', 'count', figsize=(5,3))
plt.xlabel("drugs")
plt.ylabel("reports")
plt.gca().axes.get_xaxis().set_ticks([])
plt.gca().get_legend().remove()
plt.show()

df[0:10].plot.barh('term', 'count')
plt.ylabel("drugs")
plt.xlabel("reports")

plt.show()


from wordcloud import WordCloud

def show_wordcount(words, background="black", color="viridis"):
    wc = WordCloud(
        background_color=background,
        max_words=50,
        max_font_size=30,colormap=color
    )
    image = wc.generate_from_frequencies(words)

    plt.figure(figsize=(10,6))
    plt.imshow(image, interpolation="bilinear")
    plt.axis("off")
    plt.show()


counts = call_api({
    "count": "patient.drug.activesubstance.activesubstancename.exact"})
words = { d['term'].capitalize(): d['count'] for d in counts }
show_wordcount(words)


def get_trend_for_reaction(reaction):
    df = pd.DataFrame(
        call_api({
            'count':'receivedate',
            'search': "receivedate:[20040101 TO 20240630] AND patient.reaction.reactionmeddrapt.exact: {}".format(reaction.upper()
            )}))
    df.index = pd.to_datetime(df.time)
    df = df.drop('time', axis=1).resample("y").sum().rename(
        columns={"count": reaction.capitalize()}
    )
    return df

reactions = ['death', 'pain', 'dyspnoea']
df = pd.concat([get_trend_for_reaction(x) for x in reactions], axis=1)
df.plot(style='o-', figsize=(5,3))
plt.show()





print("debug")