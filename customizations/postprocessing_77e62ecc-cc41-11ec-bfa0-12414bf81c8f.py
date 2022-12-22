import json
import traceback
import pandas as pd
import requests

def response_from_external_ws(url, request_type,pvi_json):
    obj = {'text':pvi_json["summary"]["reporterComments"].split("Comment Content:")[-1]}
    if request_type == "post":
        response = requests.post(url,data=obj)
    elif request_type == "get":
        response = requests.get(url)

    return response.json()



def populate_events(unstruct_json,pvi_json):
    prod_list = []
    event_list = []

    for idx in range(len(unstruct_json["products"])):
        if unstruct_json["products"][idx]["license_value"]:
            prod_list.append(unstruct_json["products"][idx])
    for idx in range(len(unstruct_json["events"])):
        if unstruct_json["events"][idx]["reportedReaction"]:
            event_list.append(unstruct_json["events"][idx])


    for idx in range(len(prod_list)):
        count = 0
        for idx_final in range(len(pvi_json["products"])):
            if pvi_json["products"][idx_final]["license_value"]:
                if prod_list[idx]["license_value"].lower() == pvi_json["products"][idx_final]["license_value"].lower():
                    pass
                else:
                    count+=1
            else:
                count+=1
        if count == len(pvi_json["products"]):
            pvi_json["products"].append(unstruct_json["products"][idx])


    for idx in range(len(event_list)):
        count = 0
        for idx_final in range(len(pvi_json["events"])):
            if pvi_json["events"][idx_final]["reportedReaction"]:
                if event_list[idx]["reportedReaction"].lower() == pvi_json["events"][idx_final]["reportedReaction"].lower():
                    pass
                else:
                    count+=1
            else:
                count+=1
        if count == len(pvi_json["events"]):
            pvi_json["events"].append(unstruct_json["events"][idx])

    return pvi_json


def get_postprocessed_json(pvi_json,w1_json):
    extracted_df = pd.DataFrame(w1_json)
    extracted_df.set_index('class', inplace=True)
    print(extracted_df)
    print("inside postprocessing...")
    url = "http://34.232.178.27:9888/unstruct/live"
    try:
        unstruct_json = response_from_external_ws(url, "post",pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_events(unstruct_json,pvi_json)
    except:
        traceback.print_exc()
    pvi_json["summary"]["reporterComments"] = None
    return pvi_json


# pvi_json = json.load(open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/sample-outer.json'))
# print(json.dumps(get_postprocessed_json(pvi_json)))
