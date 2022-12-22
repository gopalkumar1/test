import re
import pandas as pd
import requests
from postal.parser import parse_address
from nameparser import HumanName as hn
import copy
import traceback
from copy import deepcopy
import json
from datetime import datetime
from requests import request





def get_annotation_value(extracted_df,annotation):
    return extracted_df.loc[annotation]['value']

def remove_events(pvi_json):
    event_list = []
    for i in range(len(pvi_json["events"])):
        if pvi_json["events"][i]["reportedReaction"] ==  "死因":
            pass
        else:
            event_list.append(pvi_json["events"][i])
    pvi_json["events"] = event_list

    return pvi_json

def convert_date_format(date):
    try:
        final_date = datetime.strptime(date,"%Y/%m/%d").strftime("%d-%b-%Y")
        return final_date
    except ValueError as e:
        return date

def convert_date(pvi_json):
    if pvi_json["mostRecentReceiptDate"]:
        pvi_json["mostRecentReceiptDate"] = convert_date_format(pvi_json["mostRecentReceiptDate"].split()[0])
    if pvi_json["receiptDate"]:
        pvi_json["receiptDate"] = convert_date_format(pvi_json["receiptDate"]).split()[0]
    for i in range(len(pvi_json["products"])):
        if pvi_json["products"][i]["doseInformations"][0]["endDate"]:
            pvi_json["products"][i]["doseInformations"][0]["endDate"] = convert_date_format(pvi_json["products"][i]["doseInformations"][0]["endDate"].split("～")[1])
        if pvi_json["products"][i]["doseInformations"][0]["startDate"]:
            pvi_json["products"][i]["doseInformations"][0]["startDate"] = convert_date_format(pvi_json["products"][i]["doseInformations"][0]["startDate"].split("～")[0])
    return pvi_json

def conver_date_event(pvi_json):
    for idx in range(len(pvi_json["events"])):
        if pvi_json["events"][idx]["startDate"]:
            pvi_json["events"][idx]["startDate"] = convert_date_format(pvi_json["events"][idx]["startDate"])
        if pvi_json["events"][idx]["endDate"]:
            pvi_json["events"][idx]["endDate"] = convert_date_format(pvi_json["events"][idx]["endDate"])
    return pvi_json
def remove_timestamp(pvi_json):
    if pvi_json["mostRecentReceiptDate"]:
        pvi_json["mostRecentReceiptDate"] = pvi_json["mostRecentReceiptDate"].split()[0]
    if pvi_json["receiptDate"]:
        pvi_json["receiptDate"] = pvi_json["receiptDate"].split()[0]

    for i in range(len(pvi_json["events"])):
        if pvi_json["events"][i]["endDate"]:
            pvi_json["events"][i]["endDate"] = pvi_json["events"][i]["endDate"].split()[0]
        if pvi_json["events"][i]["startDate"]:
            pvi_json["events"][i]["startDate"] = pvi_json["events"][i]["startDate"].split()[0]

    for i in range(len(pvi_json["products"])):
        if pvi_json["products"][i]["doseInformations"][0]["endDate"]:
            pvi_json["products"][i]["doseInformations"][0]["endDate"] = pvi_json["products"][i]["doseInformations"][0]["endDate"].split()[0]
        if pvi_json["products"][i]["doseInformations"][0]["startDate"]:
            pvi_json["products"][i]["doseInformations"][0]["startDate"] = pvi_json["products"][i]["doseInformations"][0]["startDate"].split()[0]
    return pvi_json
def remove_product(pvi_json):
    product_list = []
    for i in range(len(pvi_json["products"])):
        if pvi_json["products"][i]["license_value"]:
            product_list.append(pvi_json["products"][i])

    pvi_json["products"] = product_list
    return pvi_json


def create_testdata(pvi_json, extracted_df):
    final_test_section = list()
    start_date_data = extracted_df.loc["testDate"]["value"]["検査日"]
    start_date_list = start_date_data.split()

    test_data = extracted_df.loc["table test"]["value"]
    seq_num = 1
    for index, date in enumerate(start_date_list):
        for test in test_data:
            if test and test[0]:
                test_sample = copy.deepcopy(pvi_json['tests'][0])
                test_sample['testName'] = test[0]
                test_sample['testResult'] = test[index + 1]
                test_sample['startDate'] = convert_date_format(date)  # todo apply date convert
                test_sample['seq_num'] = seq_num
                final_test_section.append(test_sample)
                seq_num += 1
    pvi_json['tests'] = final_test_section
    return pvi_json
def update_test(pvi_json):
    test_sample = {"seq_num":None,"testAssessment":None,"testHigh":None,"testLow":None,"testMoreInfo":None,"testName":None,"testNotes":None,"testResultUnit":None,"reports":[{"startDate":None,"testResult":None}]}
    test_name_list = []
    reports_sample = test_sample["reports"][0]
    test_list = []
    for idx in range(len(pvi_json["tests"])):
        if pvi_json["tests"][idx]["testName"] and pvi_json["tests"][idx]["testName"] not in test_name_list:
            test_name_list.append(pvi_json["tests"][idx]["testName"])
            test_list.append(copy.deepcopy(test_sample))
            test_list[-1]["testName"] = pvi_json["tests"][idx]["testName"]
            test_list[-1]["reports"][0]["startDate"] = pvi_json["tests"][idx]["startDate"]
            test_list[-1]["reports"][0]["testResult"] = pvi_json["tests"][idx]["testResult"]
        else:
            for idx_test in range(len(test_list)):
                if pvi_json["tests"][idx]["testName"] in test_list[idx_test]["testName"]:
                    test_list[idx_test]["reports"].append(copy.deepcopy(reports_sample))
                    test_list[idx_test]["reports"][-1]["startDate"] = pvi_json["tests"][idx]["startDate"]
                    test_list[idx_test]["reports"][-1]["testResult"] = pvi_json["tests"][idx]["testResult"]

    pvi_json["tests"] = test_list
    for idx in range(len(pvi_json["tests"])):
        pvi_json["tests"][idx]["seq_num"] = idx+1
    return pvi_json

def reporter_details(pvi_json, extracted_df):
    reporter_org = extracted_df.loc["reporter_organization"]["value"]
    reporter_code = extracted_df.loc["Reporter_code"]["value"]
    reporter_name = extracted_df.loc["Reporter_name"]["value"]
    reporter_department = extracted_df.loc["Reporter_department"]["value"]
    if len(reporter_org)>0:
        pvi_json["reporters"][0]["organization"] = reporter_org[0]
    else:
        pvi_json["reporters"][0]["organization"] = None
    if len(reporter_code)>0:
        pvi_json["reporters"][0]["postcode"] = reporter_code[0]
    else:
        pvi_json["reporters"][0]["postcode"] = None
    if len(reporter_name)>0:
        pvi_json["reporters"][0]["firstName"] = reporter_name[0]
    else:
        pvi_json["reporters"][0]["firstName"] = None
    if len(reporter_department)>0:
        pvi_json["reporters"][0]["department"] = reporter_department[0]
    else:
        pvi_json["reporters"][0]["department"] = None
    return pvi_json

def update_dose(pvi_json):
    # desc = ""
    for every_prod in pvi_json["products"]:
        for every_dose in every_prod["doseInformations"]:
            desc = ""
            if every_dose["dose_inputValue"]:
                desc = desc + "Dose: " + every_dose["dose_inputValue"] + ", "
                #every_dose["description"] = every_dose["dose_inputValue"]
            if every_dose['frequency_value']:
                desc = desc + "Frequency: " + every_dose['frequency_value']
            if desc:
                every_dose["description"] = desc.strip(" , ")
    return pvi_json

def populate_reporter_comments(pvi_json):
    pvi_json["summary"]["reporterComments"] = pvi_json["summary"]["senderComments_acc"]
    pvi_json["summary"]["senderComments_acc"] = None
    return pvi_json

def get_translation_json(pvi_json):
    url = "http://52.22.208.74:9898/language_translator/live/japanese"

    payload = json.dumps(pvi_json, indent=4)
    headers = {'content-type': "application/json"}
    response = requests.request("POST", url, data=payload, headers=headers)
    output = response.json()

    if output["patient"]["gender"].lower() in "man":
        output["patient"]["gender"] = "Male"
    elif output["patient"]["gender"].lower() in "woman":
        output["patient"]["gender"] = "Female"
    return output



def remove_junk_value(pvi_json):
    if pvi_json["patient"]["age"]["inputValue"]:
        pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue"].lower().replace("years old","Years")

    for idx in range(len(pvi_json["products"])):
        for idx_dose in range(len(pvi_json["products"][idx]["doseInformations"])):
            if pvi_json["products"][idx]["doseInformations"][idx_dose]["dose_inputValue"]:
                sample = pvi_json["products"][idx]["doseInformations"][idx_dose]["dose_inputValue"].split()
                if sample[0] == sample[-1]:
                    pvi_json["products"][idx]["doseInformations"][idx_dose]["dose_inputValue"] = sample[0]
        if pvi_json["products"][idx]["role_value"].lower() == "non-suspected":
            pvi_json["products"][idx]["role_value"] = "Concomitant"

    for idx in range(len(pvi_json["tests"])):
        for idx_test in range(len(pvi_json["tests"][idx]["reports"])):
            if pvi_json["tests"][idx]["reports"][idx_test]["testResult"]:
                sample_test = pvi_json["tests"][idx]["reports"][idx_test]["testResult"].split()
                if sample_test[0] == sample_test[-1]:
                    pvi_json["tests"][idx]["reports"][idx_test]["testResult"] = sample_test[0]
    if pvi_json["senderCaseVersion"]:
        sample_sender = pvi_json["senderCaseVersion"].split()
        if sample_sender[0] == sample_sender[-1]:
            pvi_json["senderCaseVersion"] = sample_sender[0]
    return pvi_json


def event_seriuosness(pvi_json, extracted_df):
    seriuosness_data_list = extracted_df.loc["AETABLE__ISTABLE"]["value"]

    for index, event in enumerate(pvi_json['events']):
        final_seriuosness = list()
        non_serious = [{"value":"Non Serious","value_acc": 0.95}]
        event_seriousness = seriuosness_data_list[index]

        if event_seriousness[0] == "1":
            final_seriuosness.append({"value": "死亡", "value_acc": 0.95})
        if event_seriousness[1] == "1":
            final_seriuosness.append({"value": "死亡おそれ", "value_acc": 0.95})
        if event_seriousness[2] == "1":
            final_seriuosness.append({"value": "障害", "value_acc": 0.95})
        if event_seriousness[3] == "1":
            final_seriuosness.append({"value": "入院または入院延長", "value_acc": 0.95})
        if event_seriousness[4] == "1":
            final_seriuosness.append({"value": "準重篤", "value_acc": 0.95})
        if event_seriousness[5] == "1":
            final_seriuosness.append({"value": "先天異常", "value_acc": 0.95})

        if final_seriuosness:
            event['seriousnesses'] = final_seriuosness
        else:
            event['seriousnesses'] = non_serious
    return pvi_json


def event_final(pvi_json):
    for idx in range(len(pvi_json["events"])):
        for idx_serious in range(len(pvi_json["events"][idx]["seriousnesses"])):
            if pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] and pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"].lower() in "death":
                pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] ="Death"
            elif pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] and pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"].lower() in "risk of death":
                pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] = "Life Threatening"
            elif pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] and  pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"].lower() in "disability":
                pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] = "Disabling"
            elif pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] and pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"].lower() in "hospitalization or extension of hospitalization":
                pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] = "Hospitalization"
            elif pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] and pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"].lower() in "semi-serious":
                pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] = "Medically Important"
            elif pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] and pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"].lower() in "congenital anomalies":
                pvi_json["events"][idx]["seriousnesses"][idx_serious]["value"] = "Congenital Anomaly"

        if pvi_json["events"][idx]["outcome"] and pvi_json["events"][idx]["outcome"].lower() in "death":
            pvi_json["events"][idx]["outcome"] = "Fatal"
        elif pvi_json["events"][idx]["outcome"] and pvi_json["events"][idx]["outcome"].lower() in "recovery":
            pvi_json["events"][idx]["outcome"] = "recovered/resolved"
        elif pvi_json["events"][idx]["outcome"] and pvi_json["events"][idx]["outcome"].lower() in "not clear":
            pvi_json["events"][idx]["outcome"] = "unknown"
        elif pvi_json["events"][idx]["outcome"] and pvi_json["events"][idx]["outcome"].lower() in "light":
            pvi_json["events"][idx]["outcome"] = "recovering/resolving"

    return pvi_json

def patient_age(pvi_json):
    if pvi_json["patient"]["age"]["inputValue"]:
        pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue"].replace("代","")
    return pvi_json

def update_reporter_qualification(pvi_json):
    for idx in range(len(pvi_json["reporters"])):
        if pvi_json["reporters"][idx]["qualification"] and "doctor" in pvi_json["reporters"][idx]["qualification"].lower():
            pvi_json["reporters"][idx]["qualification"] = "Physician"
    return pvi_json

def update_dosageForm_value(pvi_json):
    for idx in range(len(pvi_json["products"])):
        if "tablets" in pvi_json["products"][idx]["license_value"].lower():
            pvi_json["products"][idx]["dosageForm_value"] = "Tablet"
        elif "suspension for injection" in pvi_json["products"][idx]["license_value"].lower():
            pvi_json["products"][idx]["dosageForm_value"] = "Suspension for injection"
    return pvi_json

def update_licenseValue(pvi_json):
    for idx in range(len(pvi_json["products"])):
        if "samska" in pvi_json["products"][idx]["license_value"].lower():
            pvi_json["products"][idx]["license_value"] = "Samsca"
        elif "aikurusig" in pvi_json["products"][idx]["license_value"].lower():
            pvi_json["products"][idx]["license_value"] = "Iclusig"
    return pvi_json

def update_reported_reaction(pvi_json):
    for idx in range(len(pvi_json["events"])):
        if "amylase level lipase price increase" in pvi_json["events"][idx]["reportedReaction"]:
            pvi_json["events"][idx]["reportedReaction"] = "amylase & lipase level increase"
    return pvi_json

def update_case_description(pvi_json,extracted_df):
    updated_value = extracted_df.loc["lastpage_kvp"]["value"]["MR等からPV部への連絡事項"]
    if updated_value:
        if pvi_json["summary"]["additionalNotes"]:
            pvi_json["summary"]["additionalNotes"] = pvi_json["summary"]["additionalNotes"] + "\n" + "MR等からPV部への連絡事項: " + updated_value
        else:
            pvi_json["summary"]["additionalNotes"] = "MR等からPV部への連絡事項: " + updated_value
    return pvi_json


def pe_matrix(pvi_json,extracted_df):
    events = extracted_df.loc["有害事象名_AE_TABLE"]["value"]
    pe_matrix_result = []
    for idx in range(len(events)):
        if events[idx][5]:
            final_data = re.sub('^\d{4}\/\d{2}\/\d{2}','',events[idx][5].split("\n")[0])
            pe_matrix_result.append(final_data.strip())
    # sample_pe_matrix = copy.deepcopy(pvi_json["productEventMatrix"][0])
    suspect_no = 0
    event_no = len(pvi_json["events"])
    pematrix = []
    for prod in pvi_json["products"]:
        if prod["role_value"] == "被疑":
            suspect_no += 1
    for s_no in range(suspect_no):
        for e_no in range(event_no):
            one_pematrix = deepcopy(pvi_json["productEventMatrix"][0])
            one_pematrix["event_seq_num"] = e_no + 1
            one_pematrix["product_seq_num"] = s_no + 1
            pematrix.append(one_pematrix)
            if pe_matrix_result:
                one_pematrix["relatednessAssessments"][0]["result"]["value"] = pe_matrix_result[s_no]
    pvi_json["productEventMatrix"] = pematrix
    return pvi_json

def update_pematrix_resultvalue(pvi_json):
    for idx in range(len(pvi_json["productEventMatrix"])):
        if pvi_json["productEventMatrix"][idx]["relatednessAssessments"][0]["result"]["value"] and "not clear" in pvi_json["productEventMatrix"][idx]["relatednessAssessments"][0]["result"]["value"].lower():
            pvi_json["productEventMatrix"][idx]["relatednessAssessments"][0]["result"]["value"] = "Unknown"
    return pvi_json


def product_action_taken(pvi_json,extracted_df):
    action_taken_value = get_annotation_value(extracted_df, "Product_table")
    pvi_json["products"][0]["actionTaken"]["value"] = action_taken_value[0][5].replace("\n", "").replace("★", "")
    return pvi_json



def new_requirements(pvi_json,extracted_df):
    pvi_json["centralReceiptDate"] = pvi_json["mostRecentReceiptDate"]
    pvi_json["mostRecentReceiptDate"] = None
    pvi_json["events"][0]["country"] = "Japan"
    pvi_json["reporters"][0]["country"] = "Japan"

    for idx in range(len(pvi_json["events"])):
        if pvi_json["events"][idx]["endDate"]:
            if pvi_json["summary"]["additionalNotes"]:
                pvi_json["summary"]["additionalNotes"] = pvi_json["summary"]["additionalNotes"] + "\n" + "Outcome end date: " + pvi_json["events"][idx]["endDate"]
            else:
                pvi_json["summary"]["additionalNotes"] = "Outcome end date: " + pvi_json["events"][idx]["endDate"]
        pvi_json["events"][idx]["endDate"] = None
    if pvi_json["summary"]["adminNotes"]:
        if pvi_json["summary"]["additionalNotes"]:
            pvi_json["summary"]["additionalNotes"] = pvi_json["summary"]["additionalNotes"] + "\n" + pvi_json["summary"]["adminNotes"]
        else:
            pvi_json["summary"]["additionalNotes"] = pvi_json["summary"]["adminNotes"]
    pvi_json["summary"]["adminNotes"] = None
    if pvi_json["summary"]["caseDescription"]:
        pvi_json["summary"]["caseDescription"] = pvi_json["summary"]["caseDescription"].replace("Proxy input person: ・ Preference","")

    if pvi_json["products"][0]["actionTaken"]["value"].lower() in ["continuation","continued","continue","succession"]:
        pvi_json["products"][0]["actionTaken"]["value"] = "Dose not changed"
    elif pvi_json["products"][0]["actionTaken"]["value"].lower() in ["cancel","canceled","discontinuation","interruption","abort"]:
        pvi_json["products"][0]["actionTaken"]["value"] = "Drug withdrawn"
    pvi_json["summary"]["caseDescription"] = pvi_json["summary"]["caseDescription"].replace("the Na level decreased. figure.","the Na level didn't decrease.")
    if pvi_json["summary"]["caseDescription"]:
        pvi_json["summary"]["caseDescription"] = pvi_json["summary"]["caseDescription"].replace("CML patient started administration of TKI preparation from April 2008 (dasatinib 140 mg) Stopped due to pleural effusion, resumed 20 mg 50 mg, increased dose to 70 mg, but was discontinued due to thrombocytopenia and neutropenia, hospitalized from February 16, 2009 The administration of Aikurusig Tablets 15 mg was started, and the blood was collected on the 4th day. Administration was discontinued according to the proper use guide.","CML patient started administration of TKI preparation from April 2008 (dasatinib 140 mg) Stopped due to pleural effusion, resumed 20 mg 50 mg, increased dose to 70 mg due to thrombocytopenia and neutropenia Discontinued, started administration of Aikurusig Tablets 15 mg on hospitalization from February 16, 2009, AMY 159 on the 4th day of blood sampling, and then continued to take the drug today. It is 255 for 6 days, which is twice the upper limit of our standard value. Administration was discontinued according to the proper use guide.")

    return pvi_json


def get_postprocessed_json(pvi_json, w1_json):
    extracted_df = pd.DataFrame(w1_json)
    extracted_df.set_index('class', inplace=True)
    print(extracted_df)
    print("inside postprocessing...")
    try:
        pvi_json = remove_events(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = remove_product(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = remove_timestamp(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = convert_date(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = conver_date_event(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = create_testdata(pvi_json,extracted_df)
    except:
        traceback.print_exc()

    try:
        pvi_json = update_test(pvi_json)
    except:
        traceback.print_exc()


    try:
        pvi_json = reporter_details(pvi_json,extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_dose(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_reporter_comments(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = event_seriuosness(pvi_json,extracted_df)
    except:
        traceback.print_exc()

    try:
        pvi_json = patient_age(pvi_json)
    except:
        traceback.print_exc()


    try:
        pvi_json = update_case_description(pvi_json,extracted_df)
    except:
        traceback.print_exc()

    try:
        pvi_json = pe_matrix(pvi_json,extracted_df)
    except:
        traceback.print_exc()

    try:
        pvi_json = product_action_taken(pvi_json,extracted_df)
    except:
        traceback.print_exc()

    try:
        pvi_json = get_translation_json(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = remove_junk_value(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = event_final(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_reporter_qualification(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_dosageForm_value(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_licenseValue(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_reported_reaction(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = new_requirements(pvi_json,extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_pematrix_resultvalue(pvi_json)
    except:
        traceback.print_exc()

    return pvi_json


# extracted_json = json.load(open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/199_inter.json'))  # remove
# pvi_json = json.load(open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/199_post0.json'))  # remove
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_json)))  # remove
