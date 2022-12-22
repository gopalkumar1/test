import json
import fuzzywuzzy
import re
import copy
import numpy
import pandas
import requests
from dateutil import parser

'''
import json
mapping_file = "/home/akshatha/standard_demo_forms/generic_form_parser_configs/SJN_without_post.json"
with open(mapping_file) as json_file:
    pvi_json = json.load(json_file)
'''
    
def update_products_table(pvi_json):
    unique_prod_names = set()
    updated_products = []
    for product in pvi_json['products']:
        unique_prod_names.add(product['license_value'])

    for unique_prod in unique_prod_names:
        for product in pvi_json["products"]:
            if product["license_value"] == unique_prod:
                updated_products.append(copy.deepcopy(product))
                break

    # for prod_name in unique_prod_names:
    #
    #     for product in pvi_json['products']:
    #         if product['license_value'] == prod_name:
    #             for updated_prod in updated_products:
    #                 if updated_prod['license_value'] == product['license_value']:
    #                     updated_prod["doseInformations"].extend(product["doseInformations"])
    #                     break
    #
    #         else:
    #             updated_products.append(product)

    for updated_product in updated_products:
        for product in pvi_json['products']:
            if product['license_value'] == updated_product["license_value"] and \
                    unique_prod["doseInformations"] != product["doseInformations"]:
                unique_prod["doseInformations"].extend(product["doseInformations"])

    pvi_json['products'] = updated_products

    # print(unique_prod_names)
    return pvi_json


def riskfactor(pvi_json):
    senderComments = pvi_json["summary"]["senderComments"]
    if senderComments not in [None, "", "null"]:
        senderComments = senderComments.replace("-- (DD-MMM-YYYY or ongoing)", "").replace("(DD-MMM-YYYY or ongoing) --", "").replace("-- \n(DD-MMM-YYYY)", "").replace("(DD-MMM-YYYY)", "").replace("Conditions: Conditions:", "Conditions: ")

        page_no_ptn = re.compile(r"Page \d{1} of \d{1}")
        if re.findall(page_no_ptn, senderComments):
            print(re.split(page_no_ptn, senderComments))
            pvi_json["summary"]["senderComments"] = re.split(page_no_ptn, senderComments)[0]
        else:
            pvi_json["summary"]["senderComments"] = senderComments
    return pvi_json


def process_hcp_reporter(pvi_json):
    drop = True
    for key in pvi_json['reporters'][1]:
        if pvi_json['reporters'][1][key] not in [None, ''] and key != 'qualification':
            drop = False
    if drop:
        pvi_json['reporters'].pop(1)
    return pvi_json


"""method which will be called from outside by generic for post processing the json"""

def receipt_date(pvi_json):
    pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
    if pvi_json["senderCaseVersion"]:
        sender_version = int(pvi_json["senderCaseVersion"])
        if sender_version > 1:
            pvi_json["receiptDate"] = None
    return pvi_json

def get_suspect_prods(pvi_json):
    suspect_prod = []
    for every_prod in pvi_json["products"]:
        if every_prod["license_value"] and every_prod["role_value"] == "suspect":
            suspect_prod.append(every_prod)
    return suspect_prod

def get_concom_prods(pvi_json):
    concom_prod = []
    for every_prod in pvi_json["products"]:
        if every_prod["license_value"] and every_prod["role_value"] == "concomitant":
            concom_prod.append(every_prod)
    return concom_prod
            
def get_unique_suspect_pords(suspect_prod):
    unique_suspect_dict = {}
    for every_suspect in range(len(suspect_prod)):
        if suspect_prod[every_suspect]["license_value"] in unique_suspect_dict:
            unique_suspect_dict[suspect_prod[every_suspect]["license_value"]].append(every_suspect)
        else:
            unique_suspect_dict[suspect_prod[every_suspect]["license_value"]] = [every_suspect]
    return unique_suspect_dict

def get_unique_concom_prods(concom_prods):
    unique_concom_dict = {}
    for every_concom in range(len(concom_prods)):
        if concom_prods[every_concom]["license_value"] in unique_concom_dict:
            unique_concom_dict[concom_prods[every_concom]["license_value"]].append(every_concom)
        else:
            unique_concom_dict[concom_prods[every_concom]["license_value"]] = [every_concom]
    return unique_concom_dict
    
def merged_suspect_prods(suspect_prod, unique_suspect_dict):
    suspect_prod_updated = []
    for every_suspect in unique_suspect_dict.keys():
        suspect_same = []
        val = unique_suspect_dict[every_suspect]
        if len(val) == 1:
            suspect_same.append(suspect_prod[val[0]])
        else:
            num = len(val)
            suspect_same.append(suspect_prod[val[0]])
            for each in range(1,num):
                suspect_same[0]["doseInformations"].extend(suspect_prod[each]["doseInformations"])
        suspect_prod_updated.extend(suspect_same)
    return suspect_prod_updated
        
def final_prod_process(suspect_prod, concom_prods, pvi_json):
    products = []
    products.extend(suspect_prod)
    products.extend(concom_prods)
    seq = 1
    for every_prod in products:
        every_prod["seq_num"] = seq
        seq = seq+1
    pvi_json["products"] = products
    return pvi_json
        

def merge_suspect_prods(pvi_json):
    suspect_prod = get_suspect_prods(pvi_json)
    concom_prods = get_concom_prods(pvi_json)
    unique_suspect_dict = get_unique_suspect_pords(suspect_prod)
    #unique_concom_dict = get_unique_concom_prods(concom_prods)
    suspect_prod = merged_suspect_prods(suspect_prod, unique_suspect_dict)
    #concom_prods = merged_concom_prods(concom_prods, unique_concom_dict)
    pvi_json = final_prod_process(suspect_prod, concom_prods, pvi_json)
    return pvi_json
    

def death_date(pvi_json):
    deathDetail = pvi_json["deathDetail"]["deathDate"]["date"]
    if deathDetail:
        pvi_json["deathDetail"]["deathDate"]["date"] = deathDetail.strip("Date of Death: (DD-MMM-YYYY)   --").strip("\n")
    return pvi_json


def patientid(pvi_json):
    if pvi_json["patient"]["name"]:
        if pvi_json["patient"]["name"].isalnum():
            pvi_json["patient"]["patientId"] = pvi_json["patient"]["name"]
            pvi_json["patient"]["name"] = None
    return pvi_json

def cleaning_suspect(pvi_json):
    for every_prod in pvi_json["products"]:
        if every_prod["role_value"] == 'suspect':
            for every_dose in every_prod["doseInformations"]:
                if every_dose["customProperty_batchNumber_value"]:
                    every_dose["customProperty_batchNumber_value"] = every_dose["customProperty_batchNumber_value"].replace("\n","")
                if every_dose["dose_inputValue"]:
                    every_dose["dose_inputValue"] = every_dose["dose_inputValue"].replace("\n","")
                if every_dose["frequency_value"]:
                    every_dose["frequency_value"] = every_dose["frequency_value"].replace("\n","")
            for every_indi in every_prod["indications"]:
                if every_indi["reportedReaction"]:
                    every_indi["reportedReaction"] = every_indi["reportedReaction"].replace("\n","")
                if every_indi["reactionCoded"]:
                    every_indi["reactionCoded"] = every_indi["reactionCoded"].replace("\n","")
            if every_prod["license_value"]:
                every_prod["license_value"] = every_prod["license_value"].replace("\n","")
    return pvi_json

    
def cleaning_concom(pvi_json):
    product_index = 0
    for prod in pvi_json["products"]:
        if "Concomitant meds" in prod["license_value"] or "Relevant Concomitant Drugs" in prod["license_value"]:
            prod_name = prod["license_value"].replace("Concomitant meds :", "").replace("Concomitant medications :", "").replace("Concomitant medications:", "")
            prod_name = prod_name.replace("Relevant Concomitant Drugs and Dates of Administration (exclude those used to treat event)", "")
            if prod_name:
                prod_name = prod_name.strip()
            pvi_json["products"][product_index]["license_value"] = prod_name
        product_index += 1

    return pvi_json

def set_reference_id(pvi_json):
    pvi_json["references"][0]["referenceType"] = "Innomar ID"
    return pvi_json
    

def get_postprocessed_json(pvi_json, extracted_data_json):
    """ for post prcessing and manipulating the json by calling a web service outside this file
    formdata = {'key':value}
    pvi_json = response_from_external_ws(url ,"get" , input_param = pvi_json)
    pvi_json = response_from_external_ws(url ,"post" , input_param = pvi_json)  """
    #pvi_json = update_products_table(pvi_json)

    try:
        pvi_json = riskfactor(pvi_json)
    except:
        pass
    try:
        pvi_json = process_hcp_reporter(pvi_json)
    except:
        pass
    try:
        pvi_json = cleaning_suspect(pvi_json)
    except:
        print("issue in cleaning suspect prods")
    try:
        pvi_json = receipt_date(pvi_json)
    except:
        pass
    try:
        pvi_json = merge_suspect_prods(pvi_json)
    except:
        print("issue in prods merging")
    try:
        pvi_json = death_date(pvi_json)
    except:
        pass
    try:
        pvi_json = patientid(pvi_json)
    except:
        print("issue in setting patient id")
    try:
        pvi_json = cleaning_concom(pvi_json)
    except:
        pass
    try:
        pvi_json = set_reference_id(pvi_json)
    except:
        print("issue in setting reference type")

    return pvi_json

