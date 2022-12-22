import json
import fuzzywuzzy
import re
import copy
import numpy
import pandas
import boto3
import requests
from dateutil import parser


date_ptn = re.compile("\d{2}-\w*-\d{4}")   # DD-MMM-YYYY
MM_YYYY_ptn = re.compile("\w*-\d{4}")  # MMM-YYYY
DD_MM_YYYY_ptn = re.compile("\d{2}-\d{2}-\d{4}")  # MM-DD-YYYY


def receipt_date(pvi_json):
    pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
    if pvi_json["senderCaseVersion"] not in [None, ""]:
        sender_version = pvi_json["senderCaseVersion"].strip()       
        if sender_version.lower() in ["f", "follow-up", "followup"]:
            pvi_json["receiptDate"] = None

    if pvi_json["mostRecentReceiptDate"] not in [None, ""]:
        pvi_json["mostRecentReceiptDate"] = pvi_json["mostRecentReceiptDate"].replace(" 00:00:00", "").strip()
    if pvi_json["receiptDate"] not in [None, ""]:
        pvi_json["receiptDate"] = pvi_json["receiptDate"].replace(" 00:00:00", "").strip()

    return pvi_json


def clean_sendercomments(pvi_json):
    summ = pvi_json["summary"]["senderComments"]
    if summ:
        summ = re.sub("COMMENTLINE\d{1,2}", "", summ)
        pvi_json["summary"]["senderComments"] = summ
    return pvi_json


# this will be removed in next deployment
def repo_type(text):
    type = ""
    if text:
        text = text.lower()
        if "physician" in text or "doctor" in text or "reporter" in text:
            type = "Physician"
        if "pharmacist" in text:
            type = "Pharmacist"
        if "other hcp" in text or "other health professional" in text or "nurse" in text:
            type = " Other health professional"
        if "patient" in text or "consumer" in text or "relative/friend of patient" in text or "did not ask" in text:
            type = "Consumer"

    return type


# splitting name into first/middle/last names
def name_breaker(givenname):
    middleName = ""
    lastName = ""
    firstName = ""
    repo_title = ""
    if givenname:
        strings_to_remove = ["Ms.", "Mr.", "Dr.", "Ms ", "Mr ", "Dr ", "Miss"]

        repo_title = repo_type(givenname)
        for rm_str in strings_to_remove:
            givenname = givenname.replace(rm_str, "").strip()

        splitted_givenname = givenname.strip().split(" ")
        firstName = splitted_givenname[0].strip(",")
        if len(splitted_givenname) == 2:
            lastName = splitted_givenname[1]
        elif len(splitted_givenname) >= 3:
            middleName = splitted_givenname[1]
            lastName = " ".join(splitted_givenname[2:]).strip()

    name_split = {"firstName": firstName, "middleName": middleName, "lastName": lastName, "reporter_title": repo_title}

    return name_split


def set_names(pvi_json):
    repo_index = 0
    for reporter in pvi_json["reporters"]:
        if reporter["givenName"]:
            name_split = name_breaker(reporter["givenName"])
            nameacc = name_breaker(reporter["givenName_acc"])
            if nameacc:
                pvi_json["reporters"][repo_index]["firstName"] = name_split["lastName"]
                pvi_json["reporters"][repo_index]["middleName"] = name_split["middleName"]
                pvi_json["reporters"][repo_index]["lastName"] = name_split["firstName"]
                pvi_json["reporters"][repo_index]["givenName"] = ""
                pvi_json["reporters"][repo_index]["givenName_acc"] = ""
            else:
                pvi_json["reporters"][repo_index]["firstName"] = name_split["firstName"]
                pvi_json["reporters"][repo_index]["middleName"] = name_split["middleName"]
                pvi_json["reporters"][repo_index]["lastName"] = name_split["lastName"]
                pvi_json["reporters"][repo_index]["givenName"] = ""
        repo_index += 1

    return pvi_json


def patient_dob(pvi_json):
    mon = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    dob = pvi_json["patient"]["age"]["inputValue"]
    if dob:
        dob = dob.replace("/", "-").replace(r"\n", "").replace(r"\\r\\n", "").replace(r"\\r", "").replace(r"\r", "")
        dob = dob.strip(r"\\r").strip("\\r")
        if dob not in ["", None]:
            ptn1 = DD_MM_YYYY_ptn.findall(dob)
            ptn2 = date_ptn.findall(dob)
            ptn3 = MM_YYYY_ptn.findall(dob)
            if len(ptn1) > 0:
                ptn1 = ptn1[0].split("-")
                if str(ptn1[0]).startswith("0"):
                   month = mon[int(ptn1[0][1:])-1]
                pvi_json["patient"]["age"]["inputValue"] = str(ptn1[1]) + "-" + month + "-" + str(ptn1[2])
            elif len(ptn2) > 0:
                pvi_json["patient"]["age"]["inputValue"] = ptn2[0]
            elif len(ptn3) > 0:
                ptn3 = ptn3.split("-")
                if ptn3[0].startswith("0"):
                   month = mon[int(ptn3[0][1:])]
                pvi_json["patient"]["age"]["inputValue"] = month + "-" + ptn3[1]
        else:
            pvi_json["patient"]["age"]["inputValue"] = None
    return pvi_json


def products(pvi_json):
    prod_index = 0
    for prod in pvi_json["products"]:
        dose_index = 0
        for doseinfo in prod["doseInformations"]:
            dose_inputValue = pvi_json["products"][prod_index]["doseInformations"][dose_index]["dose_inputValue"]
            if dose_inputValue not in [None, ""]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["description"] = dose_inputValue

            startdate = pvi_json["products"][prod_index]["doseInformations"][dose_index]["startDate"]
            if startdate not in ["", None]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["startDate"] = startdate.replace(
                    " 00:00:00", "")
            enddate = pvi_json["products"][prod_index]["doseInformations"][dose_index]["endDate"]
            if enddate not in ["", None]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["endDate"] = enddate.replace(
                    " 00:00:00", "")

            continuing = doseinfo["continuing"]
            if continuing not in [None, ""]:
                cont = re.sub("MED\d{1,2}", "", continuing)
                cont = cont.replace("\\r", "").replace('\\"', "").strip("\"").strip()
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["continuing"] = cont

            dose_index += 1
        prod_index += 1
    return pvi_json


def get_ws1_data(ws1_json, id):
    data_index = 0
    for data in ws1_json:
        if data["AnnotID"] == id:
            break
        data_index += 1

    return ws1_json[data_index]["value"]


def get_ws1_all_data(ws1_json, id):
    data_index = 0
    for data in ws1_json:
        if data["AnnotID"] == id:
            break
        data_index += 1

    return ws1_json[data_index]["value"]


def referenceid(pvi_json, extracted_json):
    ref_list = []
    pmm_patient_id = get_ws1_data(extracted_json, "10002")[0]["PMMPATIENT"].split("|")[0]
    if pmm_patient_id not in [None, ""]:
        pvi_json["senderCaseUid"] = pmm_patient_id
        pvi_json["references"][0]["referenceId"] = pmm_patient_id.strip()
        pvi_json["references"][0]["referenceType"] = "PMM ID"

    # there is no reference section in UI json so jpc and rmr are taken form ws1 results
    jpc_no = get_ws1_data(extracted_json, "10003")
    RMR_no = get_ws1_data(extracted_json, "10020")
    rmr_index = 1
    RMR_all = ""
    for no in range(len(RMR_no)):
        input = RMR_no[no]['regex::RMR\\d+'].split("|")[0].replace("\n", "").replace("\\r\\n", "")
        input = re.sub("RMR\\d+", "", input).strip()
        input = re.sub("MED\\d+", "", input).strip()
        input = re.sub("COMMENTLINE\\d", "", input).strip()
        ref_list.append({"referenceId": input, "referenceType": None})

        if input not in [None, ""]:
            RMR_all = RMR_all + "\nRMR" + str(rmr_index) + ": " + input
        else:
            RMR_all = RMR_all + "\nRMR" + str(rmr_index) + ": "
        rmr_index += 1

    jpc_index = 1
    jpc_all = ""
    for no in range(len(jpc_no)):
        op = jpc_no[no]['regex::JPC\\d+'].split("|")[0].replace("\n", "").replace("\\r\\n", "")
        if op not in ["", None]:
            op = re.sub("JPC\\d", "", op).strip()
            op = re.sub("CONDITION\\d", "", op).strip()
            op = re.sub("COMMENTLINE\\d", "", op).strip()
            op = re.sub("MED\\d", "", op).strip()
            jpc_all = jpc_all + "\nJPC" + str(jpc_index) + ": " + op
            jpc_index += 1
            ref_list.append({"referenceId": op, "referenceType": None})

    ref = pvi_json["references"]
    ref.extend(ref_list)
    pvi_json["references"] = ref

    decrp = ""
    casedesc = pvi_json["summary"]["caseDescription"]
    if casedesc not in [None, ""]:
        decrp = decrp + casedesc + "\n"

    if RMR_all not in [None, ""]:
        decrp = decrp + RMR_all + "\n"

    if jpc_all not in [None, ""]:
        decrp = decrp + jpc_all

    pvi_json["summary"]["caseDescription"] = decrp

    return pvi_json


def event_date(pvi_json):
    for event_index in range(len(pvi_json["events"])):
        startDate = pvi_json["events"][event_index]["startDate"]
        if startDate not in [None, ""]:
            pvi_json["events"][event_index]["startDate"] = startDate.replace(" 00:00:00", "")
        endDate = pvi_json["events"][event_index]["endDate"]
        if endDate not in [None, ""]:
            pvi_json["events"][event_index]["endDate"] = endDate.replace(" 00:00:00", "")

    return pvi_json


def medicalhistory_date(pvi_json):
    for indx in range(len(pvi_json["patient"]["medicalHistories"])):
        startDate = pvi_json["patient"]["medicalHistories"][indx]["startDate"]
        if startDate not in [None, ""]:
            pvi_json["patient"]["medicalHistories"][indx]["startDate"] = startDate.replace(" 00:00:00", "")
        endDate = pvi_json["patient"]["medicalHistories"][indx]["endDate"]
        if endDate not in [None, ""]:
            pvi_json["patient"]["medicalHistories"][indx]["endDate"] = endDate.replace(" 00:00:00", "")

    return pvi_json


def patient_name(pvi_json, ws1_json):
    pat_data = get_ws1_all_data(ws1_json, "10002")[0]["PMMPATIENT"]
    name = pvi_json["patient"]["name"]
    if name not in [None, ""]:
        pvi_json["patient"]["name"] = name.strip()
        fullname = ""
        for nm in name.split(" "):
            if nm not in [""]:
                fullname = fullname + nm + " "

        pat_data = re.sub("\n", "", pat_data).strip()
        c = 0
        for txt in pat_data.split("|"):
            if txt not in [None, "", " ", "  "]:
                c += 1
        if c > 0:
            fullname = re.sub("/ unknown", "", fullname)

        if "/ unknown" in fullname:
            fullname = fullname.replace("/ unknown", "/unknown")
        pvi_json["patient"]["name"] = fullname.strip()

    return pvi_json


def faxNum(pvi_json):
    indx = 0
    for repo in pvi_json["reporters"]:
        pvi_json["reporters"][indx].update({"faxNumber": repo["fax"]})
        indx += 1

    return pvi_json


def sendercaseuid(pvi_json):
    pvi_json["senderCaseUid"] = pvi_json["senderCaseUid"].strip()
    return pvi_json


def COMMENTLINE(pvi_json):
    acc = pvi_json["summary"]["caseDescription_acc"]
    desc = pvi_json["summary"]["caseDescription"]
    if acc:
        acc = re.sub("COMMENTLINE\d{1,2}", "", acc)
        pvi_json["summary"]["caseDescription"] = desc + "\nCOMMENTLINE: " + acc
    pvi_json["summary"]["caseDescription_acc"] = ""
    return pvi_json


def sourcetype(pvi_json):
    acc = pvi_json["relevantTests_acc"]
    pvi_json["sourceType"][0]["value"] = acc
    pvi_json["relevantTests_acc"] = ""
    return pvi_json

def valid_date_check(pvi_json):
    for prod in pvi_json['products']:
        for dose in prod['doseInformations']:
            dose['startDate'] = valid_check(dose['startDate'])
            dose['endDate'] = valid_check(dose['endDate'])
            dose['customProperty_expiryDate'] = valid_check(dose['customProperty_expiryDate'])
    for event in pvi_json['events']:
        event['startDate'] = valid_check(event['startDate'])
        #event['hospitalizationStartDate'] = valid_check(event['hospitalizationStartDate'])
        #event['hospitalizationEndDate'] = valid_check(event['hospitalizationEndDate'])
        event['endDate'] = valid_check(event['endDate'])
    for medi_his in pvi_json['patient']['medicalHistories']:
        medi_his['startDate'] = valid_check(medi_his['startDate'])
        medi_his['endDate'] = valid_check(medi_his['endDate'])
    for pastdrug_his in pvi_json['patient']['pastDrugHistories']:
        pastdrug_his['startDate'] = valid_check(pastdrug_his['startDate'])
        pastdrug_his['endDate'] = valid_check(pastdrug_his['endDate'])
    #pvi_json['centralReceiptDate'] = valid_check(pvi_json['centralReceiptDate'])
    pvi_json['deathDetail']['deathDate']['date'] = valid_check(pvi_json['deathDetail']['deathDate']['date'])
    pvi_json['receiptDate'] = valid_check(pvi_json['receiptDate'])
    pvi_json['mostRecentReceiptDate'] = valid_check(pvi_json['mostRecentReceiptDate'])
    for test in pvi_json['tests']:
        test['startDate'] = valid_check(test['startDate'])
    return pvi_json


def valid_check(date):
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul','aug', 'sep', 'oct', 'nov', 'dec']
    valid = True
    if date not in [None, '']:
        if len(date.split('-')) == 3:
            if not re.match('\d\d', date.split('-')[0]):
                valid = False
            if date.split('-')[1].lower() not in months:
                valid = False
            if not re.match('\d\d\d\d', date.split('-')[-1]):
                valid = False
        elif len(date.split('-')) == 2:
            if date.split('-')[0].lower() not in months:
                valid = False
            if not re.match('\d\d\d\d', date.split('-')[-1]):
                valid = False
        elif len(date.split('-')) == 1:
            if not re.match('\d\d\d\d', date.split('-')[-1]):
                valid = False
    if not valid:
        return None
    else:
        return date

def get_postprocessed_json(pvi_json, extracted_json):
    try:
        pvi_json = set_names(pvi_json)
    except:
        print("issue at setting names")
    try:
        pvi_json = clean_sendercomments(pvi_json)
    except:
        print("issue at sender comments")
    try:
        pvi_json = receipt_date(pvi_json)
    except:
        print("issue at receipt date")

    try:
        pvi_json = patient_dob(pvi_json)
    except:
        print("issue at patient dob")
    try:
        pvi_json = products(pvi_json)
    except:
        print("issue at product")
    try:
        pvi_json = referenceid(pvi_json, extracted_json)
    except:
        print("issue at ref id")
    try:
        pvi_json = event_date(pvi_json)
    except:
        print("issue at event date")
    try:
        pvi_json = medicalhistory_date(pvi_json)
    except:
        print("issue at medicalhistory_date")

    try:
        pvi_json = patient_name(pvi_json, extracted_json)
    except:
        print("issue at patient name")

    try:
        pvi_json = faxNum(pvi_json)
    except:
        print("issue at Fax number")

    try:
        pvi_json = sendercaseuid(pvi_json)
    except:
        print("issue at sendercaseuid number")
    try:
        pvi_json = COMMENTLINE(pvi_json)
    except:
        print("issue at sendercaseuid number")
    try:
        pvi_json = sourcetype(pvi_json)
    except:
        print("issue at source type")
    try:
        pvi_json = valid_date_check(pvi_json)
    except:
        print("issue in checking date format")
    return pvi_json
