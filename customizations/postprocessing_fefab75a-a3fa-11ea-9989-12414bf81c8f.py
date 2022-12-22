import json
import fuzzywuzzy
import re
import copy
import numpy
import pandas
import requests
from dateutil import parser


def date_format(date):
    date = date.strip()
    date_output = date
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    date = date.replace("_", "")
    date_pattern = re.compile(r'^\_*\d{1,2}\_*\/\_*\d{1,2}\_*\/\_*\d{4}\_*$|^\d{1,2}\s*\w{3}\s*\d{4}$')

    date_pattern_partial = re.compile(r'^\s*\w{3}\s*\d{4}$')
    # time pattern
    time_pattern = re.compile(r'\d{1,2}\s*\:\s*\d{1,2}\s*(PM){0,1}(AM){0,1}')

    try:
        date = re.sub(time_pattern, "", date)
        date = date.strip()
    except:
        pass

    try:
        if len(date_pattern.findall(date)) > 0:
            date_segments = parser.parse(date_pattern.findall(date)[0])
            day = date_segments.day
            mon = months[date_segments.month - 1]
            yr = date_segments.year

            if int(day) < 10:
                day = "0" + str(day)
            '''
            if int(mon) < 10:
                mon = "0" + str(mon)            '''
            date_output = str(day) + "-" + str(mon) + "-" + str(yr)


        elif len(date_pattern_partial.findall(date)) > 0:

            day = ''
            mon = re.sub("\d", "", date).upper()
            yr = re.sub("[a-zA-Z]", "", date)

            for month in months:
                if mon.lower() == month.lower():
                    mon = month
                    break
            date_output = str(mon) + "-" + str(yr)

    except:
        pass
    if date_output == date:
        return date
    else:
        return date_output.upper()


def reading_json(config_json_path):
    with open(config_json_path) as json_file:
        config_data = json.load(json_file)
        return config_data


# for post prcessing and manipulating the json by calling a web service outside this file
def get_postprocessed_json_ws(url, formdata):
    response = requests.post(url, data=formdata)
    response = json.loads(response)

    return response


def modify_caseDesc(pvi_json):
    if pvi_json["patient"]["patientId"] :
        if pvi_json["patient"]["patientId"].lower() not in ["caucasian", "black","asian"]:
            ethnic_origin = pvi_json["patient"]["patientId"].lower().split("other")[-1].replace("_", "").strip().title()
        else:
            ethnic_origin = pvi_json["patient"]["patientId"]
        pvi_json["patient"]["race"] = ethnic_origin
        # pvi_json["summary"]["caseDescription"] = pvi_json["summary"][
        #                                              "caseDescription"] + "\nPatient Ethnic Origin: " + ethnic_origin
        pvi_json["patient"]["patientId"] = None

    treatment_prod_list = []
    for event in pvi_json['events']:
        if event['continuing']:
            event['continuing'] = event['continuing'].lower().replace("_","").replace("\n","")
            event['continuing'] = re.sub(r'\s+',' ',event['continuing'])
            occurences = [x.start() for x in re.finditer(r'date\:', event['continuing'])]
            occurences_format = [x.start() for x in re.finditer(r'dd\/mmm\/yyyy', event['continuing'])]
            event_endDate = event['continuing'][occurences[0] + 5:occurences_format[0]].strip()

            if event['outcome'].lower() in ("recovered","recovered with sequelae"):
                if event_endDate in ("",None):
                    event_endDate = event['continuing'][occurences[1] + 5:occurences_format[1]].strip()
                if event_endDate:
                    event_endDate = date_format(event_endDate)
                    event['endDate'] = event_endDate
            event['continuing'] = None



        if event['medicallyConfirmed']:
            treatment_value = event['medicallyConfirmed'].replace("\n", "")
            if "x No" in treatment_value or "X No" in treatment_value:
                treatment_value = 'Was treatment received for event ? No'
            elif "x Yes" in treatment_value or "X Yes" in treatment_value:
                treatment_prod = treatment_value.split("Please specify:")[-1].replace("_", "")
                if treatment_prod:
                    treatment_prod_list.append(treatment_prod)
                    treatment_value = 'Was treatment received for this event?: Yes,' + treatment_prod
                else:
                    treatment_value = 'Was treatment received for this event?: Yes'
            else:
                treatment_value = ''
            pvi_json["summary"]["caseDescription"] = pvi_json["summary"]["caseDescription"] + "\n" + treatment_value
            event['medicallyConfirmed'] = None
    if treatment_prod_list:
        for treatment_prod in treatment_prod_list:
            prod_copy = copy.deepcopy(pvi_json['products'][-1])
            prod_copy['license_value'] = treatment_prod
            prod_copy['role_value'] = "Treatment"
            pvi_json['products'].append(prod_copy)

    # regexp = re.compile(r'Was treatment recieved for event \?')
    # occurences = [x.start() for x in re.finditer(regexp, pvi_json["summary"]["caseDescription"])]
    # caseDesc = re.split(regexp, pvi_json["summary"]["caseDescription"])[0].strip()
    # treatment_prod_list = []
    # if len(occurences[0:len(pvi_json["events"])]) > 0:
    #     for occurence_indx in range(len(pvi_json["events"])):
    #         treatment_value = pvi_json["summary"]["caseDescription"][
    #                           occurences[occurence_indx]:occurences[occurence_indx + 1]].replace("\n", "")
    #         if "x No" in treatment_value or "X No" in treatment_value:
    #             treatment_value = 'Was treatment received for event ? No'
    #         elif "x Yes" in treatment_value or "X Yes" in treatment_value:
    #             if treatment_value.split("Please specify:")[-1].replace("_", ""):
    #                 treatment_prod_list.append(treatment_value.split("Please specify:")[-1].replace("_", "").strip())
    #                 treatment_value = 'Was treatment received for event ? Yes,' + treatment_prod_list[occurence_indx]
    #
    #             else:
    #                 treatment_value = 'Was treatment received for event ? Yes'
    #         caseDesc = caseDesc + "\n" + treatment_value
    #     pvi_json["summary"]["caseDescription"] = caseDesc

    return pvi_json

def break_dosedescription(pvi_json):
    for product in pvi_json["products"]:
        for doseinfo in product["doseInformations"]:
            if doseinfo["description"]:
                doseinfo["description"] = doseinfo["description"].replace("\n", " ")
                doseDesc = doseinfo["description"].split(" ")
                if len(doseDesc) > 2:
                    doseinfo["frequency_value"] = " ".join(doseDesc[2:])
                    doseinfo["dose_inputValue"] = doseDesc[0] + " " + doseDesc[1]
    return pvi_json

def convert_dates(pvi_json):
    for product in pvi_json["products"]:
        for doseinfo in product["doseInformations"]:

            if doseinfo["startDate"]:
                doseinfo["startDate"] = date_format(doseinfo["startDate"])
            if doseinfo["endDate"]:
                if doseinfo["endDate"].lower() == "ongoing":
                    if doseinfo["description"]:
                        doseinfo["description"] = doseinfo["description"] + ", Ongoing"
                    else:
                        doseinfo["description"] = "Ongoing"
                else:
                    doseinfo["endDate"] = date_format(doseinfo["endDate"])


    for event in pvi_json["events"]:
        if event["startDate"]:
            event["startDate"] = date_format(event["startDate"])
        if doseinfo["endDate"]:
            event["endDate"] = date_format(event["endDate"])

    return pvi_json

def  modify_pat_med_histories(pvi_json):
    for med_hist in pvi_json['patient']['medicalHistories']:
        if med_hist['historyNote']:
            if med_hist['historyNote'].lower() == "family history":
                med_hist['familyHistory'] = True
                med_hist['historyNote'] = None

    return pvi_json
'''method which will be called from outside by generic for post processing the json'''
def get_postprocessed_json(pvi_json):
    # print("in here")
    ''' for post prcessing and manipulating the json by calling a web service outside this file
    formdata = {'pvi_json':pvi_json}
    pvi_json = get_postprocessed_json_ws(url , data = formdata)
    '''
    pvi_json["patient"]["weight"] = pvi_json["patient"]["weight"].replace("_", "")
    pvi_json["patient"]["height"] = pvi_json["patient"]["height"].replace("_", "")
    if pvi_json["patient"]["age"]["inputValue"]:
        pvi_json["patient"]["age"]["inputValue"] = date_format(pvi_json["patient"]["age"]["inputValue"])
    pvi_json = break_dosedescription(pvi_json)
    pvi_json = convert_dates(pvi_json)

    trimmed_events_list = []
    for event in pvi_json["events"]:
        if event['reportedReaction']:
            trimmed_events_list.append(event)
    pvi_json["events"] = trimmed_events_list
    # pvi_json["form_code"] = 4
    pvi_json = modify_pat_med_histories(pvi_json)
    pvi_json = modify_caseDesc(pvi_json)

    return pvi_json


# pvi_json = reading_json("/home/aditya/generic_poc/inputs/pdf/pfizer/output_3-June.json")
# pvi_json = get_postprocessed_json(pvi_json)
