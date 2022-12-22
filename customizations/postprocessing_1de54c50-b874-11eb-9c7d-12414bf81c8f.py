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


def recipt_date(pvi_json):
    if pvi_json["senderCaseVersion"]:
        if pvi_json["senderCaseVersion"] in ["I"]:
            pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
            #elseif float(pvi_json["senderCaseVersion"]) > 1:
        else:
            pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
            pvi_json["receiptDate"] = None
    return pvi_json


def clean_sendercomments(pvi_json):
    summ = pvi_json["summary"]["senderComments"]
    if summ:
        summ = summ.replace("COMMENTLINE2", "").replace("COMMENTLINE3", "").replace("COMMENTLINE4", "").replace("COMMENTLINE5", "")
        pvi_json["summary"]["senderComments"] = summ
    return pvi_json


# this will be removed in next deployment
def repo_type(text):
    type = ""
    if text:
        text = text.lower()
        if "physician" in text or "doctor" in text:
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
        firstName = splitted_givenname[0]
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
        name_split = name_breaker(reporter["givenName"])
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
        dob = dob.replace("/", "-")
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

    return pvi_json


def products(pvi_json):
    prod_index = 0
    for prod in pvi_json["products"]:
        dose_index = 0
        for doseinfo in prod["doseInformations"]:
            continuing = doseinfo["continuing"]
            if continuing not in [None, ""]:
                cont = continuing.replace("MED2", "").replace("\\n MED2", "").replace('\\"', "").strip("\"").strip()
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["continuing"] = cont
            dose_index += 1
        prod_index += 1
    return pvi_json


def get_postprocessed_json(pvi_json, extracted_json):
    pvi_json = set_names(pvi_json)
    pvi_json = clean_sendercomments(pvi_json)
    pvi_json = recipt_date(pvi_json)
    pvi_json = patient_dob(pvi_json)
    pvi_json = products(pvi_json)

    return pvi_json
