#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 14:21:25 2020

@author: aditya
"""
from dateutil import parser
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import json
import copy
import re

'''
date formats supported

date =' 2/Sep/1978 4: 28 PM'
date = '12/Feb/2020'
'''
def date_format(date):
    date = date.strip()
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

    date_pattern = re.compile(r'^\d{1,2}\s*\/+\s*\w{3}\s*\/+\s*\d{4}$')
    # partial dates
    date_pattern_partial = re.compile(r'^\s*\w{3}\s*\/+\s*\d{4}$')
    #time pattern
    time_pattern = re.compile(r'\d{1,2}\s*\:\s*\d{1,2}\s*(PM){0,1}(AM){0,1}')

    try:
        date = re.sub(time_pattern,"",date)
        date = date.strip()
    except:
        pass

    try:
        if len(date_pattern.findall(date)) >0 :
            date_segments = parser.parse(date_pattern.findall(date)[0])
            day = date_segments.day
            mon = months[date_segments.month-1]
            yr = date_segments.year

            if int(day) < 10:
                day = "0" + str(day)
            '''
            if int(mon) < 10:
                mon = "0" + str(mon)            '''
            date_output = str(day) + "-" + str(mon) + "-" + str(yr)


        elif len(date_pattern_partial.findall(date)) > 0 :

            day = ''
            mon = date.split("/")[0]
            yr = date.split("/")[-1]
            for month in months:
                if mon.lower() == month.lower():
                    mon = month
                    break
            date_output = str(mon) + "-" + str(yr)
        else:
            date_output = date

    except:
        pass

    return date_output.upper()

def reading_json(config_json_path):
    with open(config_json_path) as json_file:
        config_data = json.load(json_file)
        return config_data


def remove_extra_reporter_objects(pvi_json):
    new_reporter_list = []
    check_keyword = ["patient","reporter","pt","father"]

    if pvi_json['affiliate_date'] and 'yes' in  pvi_json['affiliate_date'].lower():
        check_keyword = ["patient","reporter","pt","father","prescriber","HCP"]
    if pvi_json['project'] and 'yes' in  pvi_json['project'].lower():
        check_keyword = ["patient","reporter","pt","father","prescriber","HCP"]

    for reporter in pvi_json['reporters']:
        for check in check_keyword:
            if reporter['Intermediary'] and check.lower() in reporter['Intermediary'].lower()  :
                new_reporter_list.append(reporter)
                break


    if len(new_reporter_list) == 0:
        rep_copy = copy.deepcopy(pvi_json['reporters'][0])
        rep_copy = {key: None for key in rep_copy}
        new_reporter_list.append(rep_copy)

    pvi_json['reporters'] = new_reporter_list

    return pvi_json

def split_rep_name(pvi_json):
    for reporter in pvi_json['reporters']:
        if reporter['city']:
            if reporter['city'].lower() in ["patient","reporter","pt","father","prescriber","HCP"]:
                reporter['city'] = None
        if reporter['street']:
            if reporter['street'].lower() in ["patient","reporter","pt","father","prescriber","HCP"]:
                reporter['street'] = None
        if reporter['state']:
            if reporter['state'].lower() in ["patient","reporter","pt","father","prescriber","HCP"]:
                reporter['state'] = None
        rep_name = reporter['givenName']
        if len(rep_name.split()) == 3:
            last_token = rep_name.split()[2]
            if bool(last_token.isupper()):
                rep_name = rep_name.replace(last_token,"")

        if rep_name not in (None,""):
            reporter['firstName'] = rep_name.split()[0]
            reporter['lastName'] = rep_name.split()[-1]
            if len(rep_name.split()) ==3:
                reporter['middleName'] = rep_name.split()[1]
            reporter['givenName'] = None

    return pvi_json

def check_adverse_event_ini_reporter(pvi_json):

    if pvi_json['relevantTests'] not in (None,"") and "," in pvi_json['relevantTests']:
        ini_rep_name = pvi_json['relevantTests'].split(",")
        for reporter in pvi_json['reporters']:
            if reporter['Intermediary'] != None and "reporter" in reporter['Intermediary']:
                if fuzz.WRatio(reporter['firstName'],ini_rep_name[-1].strip()) < 80 or fuzz.WRatio(reporter['lastName'],ini_rep_name[0].strip()) < 80 :
                    # print("hello")
                    new_rep = copy.deepcopy(reporter)
                    new_rep = {key: None for key in new_rep}
                    new_rep['firstName'] = ini_rep_name[-1].strip()
                    new_rep['lastName'] = ini_rep_name[0].strip()
                    pvi_json['reporters'].append(new_rep)


    return pvi_json

def get_patient_gender_events_country(pvi_json):

    event_country = None
    patient_gender = None
    for reporter in pvi_json['reporters']:
        if reporter['Intermediary'] and ("pt" in reporter['Intermediary'].lower() or "patient" in reporter['Intermediary'].lower()):
            patient_gender = reporter['gender']
            event_country = reporter['country']
            break

    if pvi_json['patient']['gender'] in ("null","",None):
        if patient_gender:
            pvi_json['patient']['gender'] = patient_gender

    if event_country:
        for event in pvi_json['events']:
            if event['country'] in ("null","",None):
                event['country'] = event_country

    return pvi_json

def convert_dates_populate_outcome(pvi_json):

    if len(pvi_json['events']) == 1:
        if pvi_json['events'][0]['reportedReaction'] in (None,""):
            pvi_json['events'][0]['reportedReaction'] = "NA"

    for event in pvi_json['events']:
        event['outcome'] = "Unknown"
        if event['startDate']:
            event['startDate'] = date_format(event['startDate'])
        if event['endDate']:
            event['endDate'] =  date_format(event['endDate'])
        if event['endDate'] not in (""," ","null",None):
            event['outcome'] = "Recovered/Resolved"

    for product in pvi_json['products']:
        for doseinfo in product['doseInformations']:
            if doseinfo['startDate']:
                doseinfo['startDate'] =  date_format(doseinfo['startDate'])
            if doseinfo['endDate']:
                doseinfo['endDate'] =  date_format(doseinfo['endDate'])
            if doseinfo['customProperty_batchNumber_value']:
                doseinfo['customProperty_batchNumber_value'] =  date_format(doseinfo['customProperty_batchNumber_value'])

    if pvi_json['patient']['age']['ageType'] == "PATIENT_BIRTH_DATE":
        if pvi_json['patient']['age']['inputValue']:
            pvi_json['patient']['age']['inputValue'] = date_format(pvi_json['patient']['age']['inputValue'])

    if pvi_json['receiptDate']:
        pvi_json['receiptDate'] = date_format(pvi_json['receiptDate'].split()[0])

    return pvi_json


def update_product_name(pvi_json):
    for product in pvi_json['products']:
        if product['license_value']:
            if fuzz.WRatio(product['license_value'],'Acthar_BRA_US')> 45:
            # if "Acthar_BRA_U" in product['license_value'] or product['license_value'].startswith("Acthar_BR") or product['license_value'].startswith("har_BRA_U") or product['license_value'].startswith("thar_BRA_U"):
                product['license_value'] = 'Acthar_BRA_US'
            if fuzz.WRatio(product['license_value'],'Oxycodone TAB_MAL_US')> 45:
            # if "ycodone" in product['license_value'] or "Oxycodone" in product['license_value'] or product['license_value'] == "Oxycodone-\\nTAB_MAL_US":
                product['license_value'] = "Oxycodone TAB_MAL_US"
    return pvi_json

def split_multiproduct_name_to_single(pvi_json):
    new_prod_list = []
    for product in pvi_json['products']:
        if product['role_value'].lower() == "suspect":
            new_prod_list.append(product)

        if product['role_value'].lower() == "concomitant":
            if product['license_value']:
                product['license_value'] =  product['license_value'].replace("Concomitant Product Code Description","")
                concom_prods = product['license_value'].strip().split("\n")
                if len(concom_prods) > 1:
                    seq_num = int(product['seq_num'])
                    for concom_prod in concom_prods:
                        product_copy = copy.deepcopy(product)
                        product_copy['seq_num'] = seq_num
                        product_copy['license_value'] = concom_prod
                        new_prod_list.append(product_copy)
                        seq_num += 1
                else:
                    new_prod_list.append(product)
    pvi_json['products'] = new_prod_list


    return pvi_json

def fill_source_type(pvi_json):
    source_type = "Spontaneous"
    for reporter in pvi_json['reporters']:
        for rep_key , rep_data in reporter.items():
          if rep_data and ("asap" in rep_data.lower()):
              source_type = "Solicited"
              break
    # if flag == False:
    #     if 'asap' in pvi_json['summary']['caseDescription']:
    #         source_type = "Solicited"

    pvi_json['sourceType'][0]['value'] = source_type
    if source_type == "Solicited":
        pvi_json['study']['studyNumber'] = "ActharPACT"

    return pvi_json


def fill_admin_sendercaseUid(pvi_json):

    if pvi_json['senderCaseVersion']:
        report_number = pvi_json['senderCaseVersion'].lower().replace("event","")
        report_number = report_number.split()[0]

        for reporter in pvi_json['reporters']:
            if reporter['Intermediary'] not in (None,"") and "initial" in reporter['Intermediary']:
                reporter['department'] = report_number

    if pvi_json['patient']['age']['inputValue'] not in ("",None) and pvi_json['patient']['gender'] :
        pvi_json['senderCaseUid'] = pvi_json['patient']['age']['inputValue'] +"||" +  pvi_json['patient']['gender']

    elif pvi_json['patient']['age']['inputValue'] in("", None) and pvi_json['patient']['gender']:
        pvi_json['senderCaseUid'] = "||" +  pvi_json['patient']['gender']
    elif pvi_json['patient']['age']['inputValue']  and pvi_json['patient']['gender'] in ("", None):
        pvi_json['senderCaseUid'] = pvi_json['patient']['age']['inputValue'] +"||"

    return pvi_json

def modify_PE_matrix(pvi_json):

    if len(pvi_json['events'])>1:
        PE_matrix_lst = []
        for event in pvi_json['events']:
            PE_matrix_copy = copy.deepcopy(pvi_json['productEventMatrix'][0])
            PE_matrix_copy['event_seq_num'] = event['seq_num']
            PE_matrix_copy['product_seq_num'] = 1
            PE_matrix_lst.append(PE_matrix_copy)

        pvi_json['productEventMatrix'] = PE_matrix_lst

    return pvi_json

'''Format: 5'4'', 5 Feet 4 inches, 180 cms, 72 inches, 5 feet '''
def pat_height_wt(pvi_json):

    if pvi_json['patient']['weightUnit'] not in ("","null",None):
        if 'lbs' in pvi_json['patient']['weightUnit']:
            try:
                weight = float(pvi_json['patient']['weight'])
                weight = weight * 0.453592
                if weight % int(weight) >=0.5:
                    weight = int(weight) +1
                else:
                    weight = int(weight)
                pvi_json['patient']['weight'] = weight
                pvi_json['patient']['weightUnit'] = 'kg'
            except:
                pass
    else:
        pvi_json['patient']['weight'] = None


    if pvi_json['patient']['height'] not in (" ","", None):
        try:
            height = pvi_json['patient']['height'].lower()
            if bool(re.search(r'\d(\\)*\'\d{1,2}(\'\')*(\\)*\"*',height)):
                height_cm = float(re.split(r'\'', height)[0]) * 30.48 + float(re.split(r'\'', height)[1]) * 2.54
            elif 'feet' in height:
                if 'inch' in height:
                    if bool(re.search(r'\d+\s*feet\s*\d+\s*inches',height)):
                        height_cm = float(re.split(r'feet', height)[0]) * 30.48 + float(re.split(r'feet', height)[1]) * 2.54
                    else :
                        height_cm = float(height.split('inches')[0])  * 2.54
                else:
                    height_cm = float(height.split('feet')[0]) *  30.48
            elif 'cm' in height:
                height_cm = height.strip("cm")
            else:
                height_cm = None

            pvi_json['patient']['height'] = height_cm
            pvi_json['patient']['heightUnit'] = "cm"
        except:
            pass

    return pvi_json


def check_multiple(value):
    tokenized_values = []
    temp_tokens = []
    temp_token1 = []


    for delimiter in [',','and']:
        temp_tokens = value.split(delimiter)
        break

    for temp_token in temp_tokens:
        tokenized = False
        for delimiter in [',','and']:
            if delimiter in temp_token:
                temp_tokens1 = temp_token.split(delimiter)
                tokenized_values.extend(temp_tokens1)
                tokenized = True

        if tokenized == False:
            tokenized_values.append(temp_token.strip())

    return tokenized_values

def modify_prod_indications_medical_hist(pvi_json):

    if pvi_json['products'][0]['indications'][0]['reportedReaction']:
        indications = check_multiple(pvi_json['products'][0]['indications'][0]['reportedReaction'])
        if len(indications)>1:
            indi_lst = []
            for indication in indications:
                indi_copy = copy.deepcopy(pvi_json['products'][0]['indications'][0])
                indi_copy['reportedReaction'] = indication
                indi_copy['reactionCoded'] = indication
                indi_lst.append(indi_copy)
            pvi_json['products'][0]['indications'] = indi_lst


        new_med_hist_list = []
        for med_hist in pvi_json['patient']['medicalHistories']:
            if med_hist['reportedReaction']:
                med_histories = check_multiple(med_hist['reportedReaction'])
                if len(med_histories)>1:

                    for med_his1 in med_histories:
                        med_hist_copy = copy.deepcopy(med_hist)
                        med_hist_copy['reportedReaction'] = med_his1
                        med_hist_copy['reactionCoded'] = med_his1
                        new_med_hist_list.append(med_hist_copy)
                    pvi_json['patient']['medicalHistories'].remove(med_hist)
                    break
        if len(new_med_hist_list) > 0:
            pvi_json['patient']['medicalHistories'].extend(new_med_hist_list)

    return pvi_json

def make_extra_fields_none(pvi_json):
    pvi_json['relevantTests'] = None
    pvi_json['affiliate_date'] =None
    pvi_json['project'] = None

    for reporter in pvi_json['reporters']:
        reporter['report_media'] = None
        reporter['Intermediary'] = None

    return pvi_json


def removing_repeated_string(pvi_json):
    product_indx = 0
    for product in pvi_json["products"]:
        dose_indx = 0
        for dose in product["doseInformations"]:
            givenstring = dose["customProperty_batchNumber_value"]            
            givenstring = filter_repeated_words(givenstring)            
            pvi_json["products"][product_indx]["doseInformations"][dose_indx]["customProperty_batchNumber_value"] = givenstring
            dose_indx = dose_indx+1
        product_indx = product_indx+1
        
    return pvi_json


def filter_repeated_words(givenstring):
    REPEATER = re.compile(r"(.+?)\1+$")
    try:
        match = REPEATER.match(givenstring)    
        if match:
            givenstring = match.group(1)        
    except:
        pass
    
    return givenstring

def get_postprocessed_json(pvi_json):
    print("inside Post processing file")
    pvi_json = fill_source_type(pvi_json)

    pvi_json = split_rep_name(pvi_json)

    pvi_json = remove_extra_reporter_objects(pvi_json)

    # pvi_json = check_adverse_event_ini_reporter(pvi_json)

    pvi_json = get_patient_gender_events_country(pvi_json)

    pvi_json = convert_dates_populate_outcome(pvi_json)

    # pvi_json = update_product_name(pvi_json)

    pvi_json = fill_admin_sendercaseUid(pvi_json)

    pvi_json = modify_PE_matrix(pvi_json)

    pvi_json = split_multiproduct_name_to_single(pvi_json)

    pvi_json = pat_height_wt(pvi_json)

    pvi_json = modify_prod_indications_medical_hist(pvi_json)

    pvi_json = make_extra_fields_none(pvi_json)
    
    pvi_json = removing_repeated_string(pvi_json)

    return pvi_json

# pvi_json = reading_json('/home/aditya/generic_poc/inputs/pdf/new_mnk/output_test.json')

# new_pvi_json = get_postprocessed_json(pvi_json)

