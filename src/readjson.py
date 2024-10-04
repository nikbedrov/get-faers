import pandas as pd
import json


ptname = "ARTHRALGIA"
ptcount = 0
casecounter = 0
with open("drug-event-0004-of-0004.json") as f:
    data = json.load(f)
    df = pd.DataFrame(data['results'])

    print(f"MIN receivedate {df["receivedate"].min()}")
    print(f"MAX receivedate {df["receivedate"].max()}")

    for patient in df["patient"]:
        casecounter += 1
        for reaction in patient['reaction']:
            if reaction["reactionmeddrapt"] == ptname:
                ptcount += 1
                print(f"Found {ptcount} occurances of {ptname}")
                print(f"Receipt date {df["receiptdate"][casecounter]}")

        
                
            

print("debug")