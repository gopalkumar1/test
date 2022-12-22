import json
import traceback
import pandas as pd
import requests
from datetime import datetime

def response_from_external_ws_events(url, request_type,pvi_json):
    obj = {'text':pvi_json["summary"]["reporterComments"]}
    if request_type == "post":
        response = requests.post(url,data=obj)
    elif request_type == "get":
        response = requests.get(url)

    return response.json()


def response_from_external_ws_products(url, request_type,pvi_json):
    obj = {'text':pvi_json["message"]}
    if request_type == "post":
        response = requests.post(url,data=obj)
    elif request_type == "get":
        response = requests.get(url)

    return response.json()


def response_from_external_ws_patient(url, request_type,pvi_json):
    obj = {'text':pvi_json["summary"]["senderComments"]}
    if request_type == "post":
        response = requests.post(url,data=obj)
    elif request_type == "get":
        response = requests.get(url)

    return response.json()




def populate_events(unstruct_json_events,pvi_json):
    event_list = []

    for idx in range(len(unstruct_json_events["events"])):
        if unstruct_json_events["events"][idx]["reportedReaction"]:
            event_list.append(unstruct_json_events["events"][idx])

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
            pvi_json["events"].append(unstruct_json_events["events"][idx])

    return pvi_json


def populate_products(unstruct_json_products,pvi_json):
    prod_list = []
    for idx in range(len(unstruct_json_products["products"])):
        if unstruct_json_products["products"][idx]["license_value"]:
            prod_list.append(unstruct_json_products["products"][idx])


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
            pvi_json["products"].append(unstruct_json_products["products"][idx])

    return pvi_json

def populate_patient(unstruct_json_patient,pvi_json):
    pvi_json["patient"] = unstruct_json_patient["patient"]
    return pvi_json


def event_startDate(pvi_json):
    for idx in range(len(pvi_json["events"])):
        if pvi_json["events"][idx]["startDate"]:
            obj1 = datetime.strptime(pvi_json["events"][idx]["startDate"],"%d-%b-%Y %H:%M:%S")
            obj2 = datetime.strptime(pvi_json["events"][idx]["startDate"],"%b-%Y %H:%M:%S")
            obj3 = datetime.strptime(pvi_json["events"][idx]["startDate"], "%Y %H:%M:%S")
            if obj1 or obj2 or obj3:
                pass
            else:
                pvi_json["summary"]["caseDescription"] = pvi_json["events"][idx]["startDate"]
                pvi_json["events"][idx]["startDate"] = None
    return pvi_json


def reporter_qualification(pvi_json):
    code_list = ["Auto_Test","Company Representative","Consumer","Consumer or other non health professional","Doctor","feb_agrp","Hospital","Investigator","Lawyer","Nurse","Other health professional","Patient","professor","Test Qualification"]
    for idx in range(len(pvi_json["reporters"])):
        for idx_code_list in range(len(code_list)):
            if code_list[idx_code_list].lower() in pvi_json["reporters"][idx]["qualification"].lower():
                pvi_json["reporters"][idx]["qualification"] = code_list[idx_code_list]
            elif "psychiatrist" in pvi_json["reporters"][idx]["qualification"].lower():
                pvi_json["reporters"][idx]["qualification"] = "Doctor"
    return pvi_json

def get_postprocessed_json(pvi_json,w1_json):
    extracted_df = pd.DataFrame(w1_json)
    extracted_df.set_index('class', inplace=True)
    print(extracted_df)
    print("inside postprocessing...")
    url = "http://34.232.178.27:9888/unstruct/live"
    try:
        unstruct_json_events = response_from_external_ws_events(url, "post",pvi_json)
    except:
        traceback.print_exc()
    try:
        unstruct_json_products = response_from_external_ws_products(url, "post",pvi_json)
    except:
        traceback.print_exc()
    try:
        unstruct_json_patient = response_from_external_ws_patient(url, "post",pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_events(unstruct_json_events,pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_products(unstruct_json_products,pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_patient(unstruct_json_patient,pvi_json)
    except:
        traceback.print_exc()
    pvi_json["summary"]["reporterComments"] = None
    pvi_json["message"] = None
    pvi_json["summary"]["senderComments"] = None

    try:
        pvi_json = reporter_qualification(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = event_startDate(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json


# pvi_json = json.load(open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/sample-outer.json'))
# print(json.dumps(get_postprocessed_json(pvi_json)))
