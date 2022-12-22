from sqlite3 import Timestamp
import pandas as pd 
import json
import requests
import traceback
import regex as re
import pycountry


def patient_key_add(pvi_json):
    
    inputValue_acc_val=pvi_json['patient']['age']['inputValue_acc']
    pvi_json['patient']['patientDOB'] =inputValue_acc_val
    pvi_json['patient']['age']['inputValue_acc']=None
    pvi_json['events'][0]['reportedReaction']='No Adverse Event'
    license_value=pvi_json['products'][0]['license_value']
    license_value=license_value.split('\n')
    license_value=license_value[1]
    license_value=license_value.split()
    for i in license_value:
        i.strip()
        if i[0].isdigit():
            license_value=i
            break
        
    pvi_json['products'][0]['doseInformations'][0]['dose_inputValue']=license_value
    pvi_json['products'][0]['doseInformations'][0]['description']="Dose:" + license_value  
    timestamp_date=pvi_json['mostRecentReceiptDate']
    timestamp_date.replace('04-APR-2022 00:00:00','')

    
    
    return pvi_json
    
    
def admin_to_additional(pvi_json):
    additionalNotes=pvi_json['summary']['adminNotes']
    pvi_json['summary']['adminNotes']=None
    pvi_json['summary']['additionalNotes']=additionalNotes
    return pvi_json
    
def transl_case_desc(pvi_json):
    caseDescription=pvi_json['summary']['caseDescription']
    url = "http://52.22.208.74:9898/language_translator/live"    
    payload = {"caseDescription":caseDescription} 
    payload=json.dumps(payload)
    headers = {'content-type': "application/json"}
    response = requests.request("POST", url, data=payload, headers=headers)
    output = response.json()
    pvi_json['summary']['caseDescription']=output['caseDescription'].strip()
    
    return pvi_json

def remove_timestamp(pvi_json):
    if pvi_json['mostRecentReceiptDate']:
        pvi_json['mostRecentReceiptDate']=pvi_json['mostRecentReceiptDate'].split()[0]
    if pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate']:
        pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate']=pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate'].split()[0]
        pvi_json["summary"]["additionalNotes"] = pvi_json["summary"]["additionalNotes"] + "\n" + "Expiry Date: " + pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate']
        pvi_json['products'][0]['doseInformations'][0]['customProperty_expiryDate'] = None
    if pvi_json['receiptDate']:
        pvi_json['receiptDate']=pvi_json['receiptDate'].split()[0]
    return pvi_json

def get_country_code(pvi_json):
    country_code=pvi_json['events'][0]['country']
    country = pycountry.countries.get(alpha_2=country_code)
    country_name = country.name
    pvi_json['events'][0]['country']=country_name
    for i in range(len(pvi_json['reporters'])):
        pvi_json['reporters'][i]['country']=country_name


def get_postprocessed_json(pvi_json,key_val_json):
    extracted_df = pd.DataFrame(key_val_json)
    extracted_df.set_index("class", inplace=True)
    try:
        pvi_json=patient_key_add(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json=admin_to_additional(pvi_json)
    except:
        traceback.print_exc()
        
    try:
        pvi_json=transl_case_desc(pvi_json)
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
    return pvi_json


