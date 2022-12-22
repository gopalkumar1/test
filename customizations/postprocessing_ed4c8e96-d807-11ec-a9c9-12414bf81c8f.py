from sqlite3 import Timestamp
import pandas as pd
import json
import requests
import traceback
import regex as re
import pycountry

def patient_key_add(pvi_json):
    inputValue_acc_val = pvi_json['patient']['age']['inputValue_acc']
    pvi_json['patient']['patientDOB'] = inputValue_acc_val
    pvi_json['patient']['age']['inputValue_acc'] = None
    pvi_json['events'][0]['reportedReaction'] = None
    license_value = pvi_json['products'][0]['license_value']

    license_value = license_value.split('\n')

    pvi_json['products'][0]['license_value'] = license_value[0]
    license_value = license_value[1]
    if pvi_json['products'][0]['license_value'] == 'HUMALOG KWIKPEN':
        pvi_json['products'][0]['strength'] = license_value

    license_value = license_value.split()
    for i in license_value:
        i.strip()
        if i[0].isdigit():
            license_value = i
            break

    pvi_json['products'][0]['doseInformations'][0]['dose_inputValue'] = license_value
    pvi_json['products'][0]['doseInformations'][0]['description'] = "Dose:" + license_value
    timestamp_date = pvi_json['mostRecentReceiptDate']
    timestamp_date.replace('04-APR-2022 00:00:00', '')

    return pvi_json

def admin_to_additional(pvi_json):
    additionalNotes = pvi_json['summary']['adminNotes']
    pvi_json['summary']['adminNotes'] = None
    pvi_json['summary']['additionalNotes'] = additionalNotes
    return pvi_json


def transl_case_desc(pvi_json):
    caseDescription = pvi_json['summary']['caseDescription']
    url = "http://52.22.208.74:9898/language_translator/live"
    payload = {"caseDescription": caseDescription}
    payload = json.dumps(payload)
    headers = {'content-type': "application/json"}
    response = requests.request("POST", url, data=payload, headers=headers)
    output = response.json()
    pvi_json['summary']['caseDescription'] = output['caseDescription'].strip()

    return pvi_json


def remove_timestamp(pvi_json):
    if pvi_json['mostRecentReceiptDate']:
        pvi_json['mostRecentReceiptDate'] = pvi_json['mostRecentReceiptDate'].split()[0]
    if pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate']:
        pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate'] = \
        pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate'].split()[0]
        pvi_json["summary"]["additionalNotes"] = pvi_json["summary"]["additionalNotes"] + "\n" + "Expiry Date: " + \
                                                 pvi_json['products'][0]['doseInformations'][0][
                                                     'customProperty_expiryDate']
        pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate'] = None
    if pvi_json['receiptDate']:
        pvi_json['receiptDate'] = pvi_json['receiptDate'].split()[0]
    return pvi_json


def get_country_code(pvi_json):
    country_code = pvi_json['events'][0]['country']
    country = pycountry.countries.get(alpha_2=country_code)
    country_name = country.name
    pvi_json['events'][0]['country'] = country_name
    for i in range(len(pvi_json['reporters'])):
        pvi_json['reporters'][i]['country'] = country_name
    return pvi_json

def references_value(pvi_json):
    find_index=pvi_json['summary']['additionalNotes'].split('\n')

    str_search = 'Request Number'
    index=0

    #request_number= pvi_json['summary']['additionalNotes'].split("\n")[3]
    #print("request number :",request_number)
    for i in find_index:
        if str_search in i:
            break
        index+=1

    request_number= find_index[index].split(':')[1].strip()
    pvi_json['references'][0]['value'] = request_number
    find_index.pop(index)
    additional_notes = ''
    for i in find_index:
        additional_notes += i + "\n"

    pvi_json['summary']['additionalNotes'] = additional_notes


    return pvi_json


def add_categories(pvi_json):
    find_index=pvi_json['summary']['additionalNotes'].split('\n')
    str_search='Event Type'
    index=0
    for i in find_index:
        if str_search in i:
            break
        index+=1
    event_type=find_index[index]
    if 'PC' in event_type.split('-')[1]:
        pvi_json['categories'].append('PQC')
    return pvi_json

def malfunction_unstruct_pqc(pvi_json):
    pvi_json["products"][0]["product_type"][0]["value"] = "Drug"
    pvi_json["products"][0]["product_type"].append({"value":None})
    pvi_json["products"][0]["product_type"][1]["value"] = "Device"

    transl_resp=pvi_json['summary']['caseDescription']

    url = "http://34.232.178.27:9888/unstruct/live"
    payload = {"text": transl_resp}
    # payload = json.dumps(payload)
    headers = {'PQC_FLAG': "True"}
    response = requests.request("POST", url, data=payload, headers=headers)
    output = response.json()

    pvi_json["products"][0]["devices"][0]["malfunctions"] = output["products"][0]["devices"][0]["malfunctions"]

    return pvi_json

def get_patient_country(pvi_json):

        country_code = pvi_json['mostRecentReceiptDate_acc'].split(':')[1].strip()
        country = pycountry.countries.get(alpha_2=country_code)
        country_name = country.name
        patient_address="Patient Address: "+country_name
        pvi_json['mostRecentReceiptDate_acc'] = "Patient Address: "+country_name
        #pvi_json['summary']['additionalNotes']=pvi_json['summary']['additionalNotes']+patient_address
        pvi_json['patient']['country']=country_name
        pvi_json['mostRecentReceiptDate_acc'] = None

        return pvi_json

def malfunction_unstruct(pvi_json):
    transl_resp=pvi_json['summary']['caseDescription']

    url = "http://34.232.178.27:9888/unstruct/live"
    payload = {"text": transl_resp}
    headers = {'PQC_FLAG': "False"}
    response = requests.request("POST", url, data=payload, headers=headers)
    output = response.json()
    pvi_json["tests"]=output["tests"]

    return pvi_json

def set_addtional_drugs(pvi_json):
    pvi_json['products'][0]['additionalDrugInfoNotes']=pvi_json['senderCaseUid_acc']
    pvi_json['senderCaseUid_acc']=None
    return pvi_json

def set_products_exp_date(pvi_json):
    find_index=pvi_json['summary']['additionalNotes'].split('\n')
    str_search='Expiry Date'.lower()
    index=0
    for i in find_index:
        if str_search in i.lower():
            break
        index+=1
    exp_date=find_index[index].split(':')[1].strip()
    pvi_json['products'][0]['expirationDate']=exp_date
    find_index.pop(index)
    additionalNotes=''
    for i in find_index:
        additionalNotes+= i+ '\n'

    pvi_json['summary']['additionalNotes']=additionalNotes
    return pvi_json

def get_postprocessed_json(pvi_json, key_val_json):
    extracted_df = pd.DataFrame(key_val_json)
    extracted_df.set_index("class", inplace=True)
    try:
        pvi_json = patient_key_add(pvi_json)
    except:
        traceback.print_exc()

        traceback.print_exc()
    try:
        pvi_json = admin_to_additional(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = transl_case_desc(pvi_json)
    except:
        traceback.print_exc()

    try:
        remove_timestamp(pvi_json)
    except:
        traceback.print_exc()
    try:
        get_country_code(pvi_json)
    except:
        traceback.print_exc()
    try:
        references_value(pvi_json)
    except:
        traceback.print_exc()
    try:
        add_categories(pvi_json)
    except:
        traceback.print_exc()
    try:
        malfunction_unstruct_pqc(pvi_json)
    except:
        traceback.print_exc()
    try:
        malfunction_unstruct(pvi_json)
    except:
        traceback.print_exc()
    try:
        get_patient_country(pvi_json)
    except:
        traceback.print_exc()
    try:
        set_addtional_drugs(pvi_json)
    except:
        traceback.print_exc()
    try:
        set_products_exp_date(pvi_json)
    except:
        traceback.print_exc()

    return pvi_json


# pvi_json = json.load(open('/home/lt-gandharvp/Desktop/output.json'))
# extracted_df = json.load(open('/home/lt-gandharvp/Desktop/output.json'))
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_df)))