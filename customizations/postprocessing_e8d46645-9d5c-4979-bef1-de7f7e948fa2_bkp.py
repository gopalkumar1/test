import json
import fuzzywuzzy
import re
import copy
import numpy
import pandas
import boto3
import requests
from dateutil import parser
from datetime import date

date_ptn = re.compile("\d{2}-\w*-\d{4}")   # DD-MMM-YYYY
MM_YYYY_ptn = re.compile("\w*-\d{4}")  # MMM-YYYY
DD_MM_YYYY_ptn = re.compile("\d{2}-\d{2}-\d{4}")  # DD-MM-YYYY

months = ['JAN', "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def date_format_update(given_date):
    given_date = re.sub("/", "-", given_date).strip()
    if given_date.lower() not in ["unk", "un"]:
        for str_rm in [" 00:00:00", "UN-UNK-", "un-unk-", "unk-", "UNK-", "^UN-", "^un-", "\n"]:
            given_date = re.sub(str_rm, "", given_date).strip()

        dd_mmm_yyyy = re.compile(r"^\d{2}-\w{3}-20\d{2}")  # 04-JAN-2021
        d_mmm_yyyy = re.compile(r"^\d{1}-\w{3}-20\d{2}")  # 4-JAN-2021
        mmm_yyyy = re.compile(r"^\w{3}-20\d{2}$")  # JAN/2021
        yyyy = re.compile(r"^20\d{2}$")  # 2021

        dd_mmm_yyyy_ptn = re.findall(dd_mmm_yyyy, given_date)
        d_mmm_yyyy_ptn = re.findall(d_mmm_yyyy, given_date)
        mmm_yyyy_ptn = re.findall(mmm_yyyy, given_date)
        yyyy_ptn = re.findall(yyyy, given_date)

        if len(dd_mmm_yyyy_ptn) > 0:
            given_date = dd_mmm_yyyy_ptn[0]
        elif len(d_mmm_yyyy_ptn) > 0:
            given_date = "0" + d_mmm_yyyy_ptn[0]
        elif len(mmm_yyyy_ptn) > 0:
            given_date = mmm_yyyy_ptn[0]
        elif len(yyyy_ptn) > 0:
            given_date = yyyy_ptn[0]

    return given_date


def empty_medhistory():
    medhis = {"continuing": null,
		"endDate": null,
		"familyHistory": null,
		"historyConditionType": null,
		"historyNote": null,
		"reactionCoded": null,
		"reportedReaction": null,
		"startDate": null
	}
    return medhis


def concom_procedures_surgeries(pvi_json):
    event_onset_date = pvi_json["events"][0]["startDate"]
    if event_onset_date.lower() not in ['unk', 'un', None, ""]:
        tests_list = []
        medhis_list = []
        for indx in range(len(pvi_json["tests"])):
            startdate = pvi_json["tests"][indx]["startDate"]
            if startdate:
                startdate = date_format_update(startdate)
            val = compare_dates_tests_section(event_onset_date, startdate)
            note = pvi_json["tests"][indx]["testNotes"]
            if pvi_json["tests"][indx]["testNotes"] in [None, ""]:
                tests_list.append(pvi_json["tests"][indx])
            elif "Diagnostic" in pvi_json["tests"][indx]["testNotes"]:
                tests_list.append(pvi_json["tests"][indx])
            elif "Other" in note and val == "negative":
                med = copy.deepcopy(empty_medhistory())
                med["startDate"] = pvi_json["tests"][indx]["startDate"]
                med["reportedReaction"] = pvi_json["tests"][indx]["testName"]
                med["historyNote"] = pvi_json["tests"][indx]["testNotes"]
                medhis_list.append(med)
            elif "Other" in note and val == "positive":
                tests_list.append(pvi_json["tests"][indx])
            elif note and val == "positive":
                tests_list.append(pvi_json["tests"][indx])
            elif note and val == "negative":
                med = copy.deepcopy(empty_medhistory())
                med["startDate"] = pvi_json["tests"][indx]["startDate"]
                med["reportedReaction"] = pvi_json["tests"][indx]["testName"]
                med["historyNote"] = pvi_json["tests"][indx]["testNotes"]
                medhis_list.append(med)

    pvi_json["tests"] = tests_list
    medhis = pvi_json["patient"]["medicalHistories"]
    medhis.extend(medhis_list)
    pvi_json["patient"]["medicalHistories"] = medhis
    return pvi_json


def receipt_date(pvi_json):
    pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
    if pvi_json["senderCaseVersion"] not in [None, ""]:
        sender_version = pvi_json["senderCaseVersion"].strip()
        if sender_version == "I":
            pvi_json["senderCaseVersion"] = "Initial"
        elif sender_version == "F":
            pvi_json["senderCaseVersion"] = "Follow-up"
        if sender_version.lower() in ["f", "follow-up", "followup"]:
            pvi_json["receiptDate"] = None

    if pvi_json["mostRecentReceiptDate"] not in [None, ""]:
        pvi_json["mostRecentReceiptDate"] = pvi_json["mostRecentReceiptDate"].replace(" 00:00:00", "").strip()
    if pvi_json["receiptDate"] not in [None, ""]:
        pvi_json["receiptDate"] = pvi_json["receiptDate"].replace(" 00:00:00", "").strip()

    return pvi_json


# this will be removed in next deployment
def repo_type(text):
    type = ""
    if text:
        text = text.lower()
        if "physician" in text or "doctor" in text or "Reporter" in text:
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


def products_date_formating(pvi_json):
    prod_index = 0
    for prod in pvi_json["products"]:
        dose_index = 0
        for doseinfo in prod["doseInformations"]:
            dose_inputValue = pvi_json["products"][prod_index]["doseInformations"][dose_index]["dose_inputValue"]
            if dose_inputValue not in [None, ""]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["description"] = dose_inputValue

            startdate = pvi_json["products"][prod_index]["doseInformations"][dose_index]["startDate"]
            if startdate not in ["", None]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["startDate"] = date_format_update(startdate)
            enddate = pvi_json["products"][prod_index]["doseInformations"][dose_index]["endDate"]
            if enddate not in ["", None]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["endDate"] = date_format_update(enddate)

            continuing = doseinfo["continuing"]
            if continuing not in [None, ""]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["continuing"] = continuing.strip()

            dose_index += 1
        prod_index += 1
    return pvi_json


def get_ws1_all_data(ws1_json, id):
    data_index = 0
    for data in ws1_json:
        if data["AnnotID"] == id:
            break
        data_index += 1

    return ws1_json[data_index]["value"]


def find_data_existance(data):
    data_present = False
    for indx in range(1, len(data)):
        for list_indx in range(1, len(data[indx])):
            if data[indx][list_indx] not in ["", None]:
                data_present = True
                break
    return data_present


def study_number(pvi_json, extracted_json):
    studynum = pvi_json["study"]["studyNumber"]
    part1_1st_table = get_ws1_all_data(extracted_json, "10043")
    part1_2nd_table = get_ws1_all_data(extracted_json, "10044")
    part2 = get_ws1_all_data(extracted_json, "10045")

    part1_1st_table_data_present = find_data_existance(part1_1st_table)
    part1_2nd_table_data_present = find_data_existance(part1_2nd_table)
    part2_data_present = find_data_existance(part2)

    if studynum in [None]:
        studynum = ""
    if part1_1st_table_data_present and part1_2nd_table_data_present and part2_data_present:
        pvi_json["study"]["studyNumber"] = studynum + "-Part2"
    else:
        pvi_json["study"]["studyNumber"] = studynum + "-Part1"

    return pvi_json


def get_date(givendate):
    outputdate = None
    year = None
    day = None
    month = None
    date_yearonly = False
    if givendate not in [None, ""]:
        if len(givendate.split("-")) == 3:
            day, month, year = givendate.split("-")
        elif len(givendate.split("-")) == 2:
            month, year = givendate.split("-")
            day = 0
        elif len(givendate.split("-")) == 1 and len(givendate) == 4:
            date_yearonly = True
        if not date_yearonly:
            if year and month and day:
                outputdate = date(int(year), months.index(month) + 1, int(day))
    return outputdate


def compare_dates(ON_SET_DATE, start_date, end_date):
    ON_SET_DATE = re.sub("/", "-", ON_SET_DATE)
    include_product = True

    if ON_SET_DATE not in [None, ""]:
        day, month, year = ON_SET_DATE.split("-")
        ON_SET_DATE = date(int(year), months.index(month) + 1, int(day))

    d0 = get_date(start_date)
    d1 = get_date(end_date)

    delta1 = None
    delta2 = None
    if d0 not in [None, ""]:
        delta1 = abs(d0 - ON_SET_DATE)
    if d1 not in [None, ""]:
        delta2 = abs(d1 - ON_SET_DATE)

    if delta1 not in [None, ""]:
        if "day" in str(delta1):
            if int(str(delta1).split(" ")[0]) > 30:
                include_product = False

    if not include_product:
        if delta2 not in [None, ""]:
            if "day" in str(delta2):
                if int(str(delta2).split(" ")[0]) > 30:
                    include_product = False

    return include_product



def compare_dates_tests_section(ON_SET_DATE, start_date):
    value = "positive"
    ON_SET_DATE = re.sub("/", "-", ON_SET_DATE)
    if ON_SET_DATE not in [None, ""]:
        if "UN-UNK" not in ON_SET_DATE:
            if ON_SET_DATE.startswith("UN-"):
                ON_SET_DATE = re.sub("UN-", "01-", ON_SET_DATE)
                day, month, year = ON_SET_DATE.split("-")
                ON_SET_DATE = date(int(year), months.index(month) + 1, int(day))
                d0 = get_date(start_date)
                delta1 = None
                if d0 not in [None, ""]:
                    delta1 = ON_SET_DATE - d0
                if delta1 not in [None, ""]:
                    if "day" in str(delta1):
                        if int(str(delta1).split(" ")[0]) < 0:
                            value = "negative"
    return value


def event_date(pvi_json):
    for event_index in range(len(pvi_json["events"])):
        startDate = pvi_json["events"][event_index]["startDate"]

        if startDate not in [None, ""]:
            pvi_json["events"][event_index]["startDate"] = date_format_update(startDate)

        endDate = pvi_json["events"][event_index]["endDate"]
        if endDate not in [None, ""]:
            pvi_json["events"][event_index]["endDate"] = date_format_update(endDate)

    return pvi_json


def medicalhistory_date(pvi_json):
    for indx in range(len(pvi_json["patient"]["medicalHistories"])):
        startDate = pvi_json["patient"]["medicalHistories"][indx]["startDate"]
        if startDate not in [None, ""]:
            pvi_json["patient"]["medicalHistories"][indx]["startDate"] = date_format_update(startDate.replace(" 00:00:00", ""))
        endDate = pvi_json["patient"]["medicalHistories"][indx]["endDate"]
        if endDate not in [None, ""]:
            pvi_json["patient"]["medicalHistories"][indx]["endDate"] = date_format_update(endDate.replace(" 00:00:00", ""))

    return pvi_json


def patient_id(pvi_json):
    id = pvi_json["patient"]["patientId"]
    if id not in ["", None]:
        id = re.sub(",", "", id)
        pvi_json["patient"]["patientId"] = id[0:-3] + "-" + id[-3:]

    return pvi_json


def concom_products_filtering_basedon_date(pvi_json):
    required_indx = []
    event_onset_date = pvi_json["events"][0]["startDate"]
    if event_onset_date.lower() not in ['unk', 'un']:
        prod_index = 0
        for prod in pvi_json["products"]:
            doseinfo_index = 0
            for doseinfo in prod["doseInformations"]:
                required_prod = compare_dates(event_onset_date, doseinfo["startDate"], doseinfo["endDate"])
                print(required_prod, event_onset_date, doseinfo["startDate"], doseinfo["endDate"])
                if required_prod:
                    required_indx.append(prod_index)
                doseinfo_index += 1
            prod_index += 1
        #print("required_indx = ", required_indx)
        if len(required_indx) > 0:
            pvi_json["products"] = [pvi_json["products"][indx] for indx in range(len(pvi_json["products"])) if indx in required_indx]

    return pvi_json


def test_date(pvi_json):
    test_indx = 0
    for test in pvi_json["tests"]:
        date = test["startDate"]
        if date not in ["", None]:
            pvi_json["tests"][test_indx]["startDate"] = date_format_update(date)
        test_indx += 1
    return pvi_json


def get_events_data_dict(adverse_event):
    event_dict = {}
    for row in adverse_event:
        if row[0] not in ["", None]:
            event_dict[row[0]] = row[1]
    return event_dict


def populate_adverse_event_data(pvi_json, extracted_datajson):
    adverse_event = get_ws1_all_data(extracted_datajson, "10047")
    adverse_event_dict = get_events_data_dict(adverse_event)

    pvi_json["events"][0]["reportedReaction"] = adverse_event_dict["Main Adverse Event Description (Term)"]
    pvi_json["events"][0]["startDate"] = adverse_event_dict["Start Date"]
    pvi_json["events"][0]["outcome"] = adverse_event_dict["Outcome of AE"]
    pvi_json["events"][0]["endDate"] = adverse_event_dict["Resolution date"]
    pvi_json["products"][0]["actionTaken"]["value"] = adverse_event_dict["Action taken with study treatment"]

    event_seriousness_dict_list = [{"value": None, "value_acc": 0.95}]
    death = adverse_event_dict["It resulted in death"]
    if death not in [None, ""]:
        death_all = re.findall("^checked", death.lower())
        if len(death_all) == 1:
            event_seriousness_dict_list = [{"value": "Death", "value_acc": 0.95}]

    lt = adverse_event_dict["It was life-threatening"]
    if lt not in [None, ""]:
        lt_all = re.findall("^checked", lt.lower())
        if len(lt_all) == 1:
            event_seriousness_dict_list.append({"value": "Life Threatening", "value_acc": 0.95})

    hospitalized = adverse_event_dict["It required or prolonged inpatient hospitalization"]
    if hospitalized not in [None, ""]:
        hospitalized_all = re.findall("^checked", hospitalized.lower())
        if len(hospitalized_all) == 1:
            event_seriousness_dict_list.append({"value": "Hospitalization", "value_acc": 0.95})

    Disability = adverse_event_dict["Persistent or significant disability / incapacity"]
    if Disability not in [None, ""]:
        Disability_all = re.findall("^checked", Disability.lower())
        if len(Disability_all) == 1:
            event_seriousness_dict_list.append({"value": "Disability", "value_acc": 0.95})

    omic = adverse_event_dict["Other important medical event (It does not meet\nany of the above serious criteria, but may\njeopardize the Patient, and may require medical\nor surgical intervention to prevent one of the\noutcomes listed above)."]
    if omic not in [None, ""]:
        omic_all = re.findall("^checked", omic.lower())
        if len(omic_all) == 1:
            event_seriousness_dict_list.append({"value": "Other Medically Important Condition", "value_acc": 0.95})

    if adverse_event_dict["If Other, specify:"] not in [None, ""]:
        event_seriousness_dict_list.append({"value": "Other Medically Important Condition", "value_acc": 0.95})

    pvi_json["events"][0]["seriousnesses"] = event_seriousness_dict_list

    return pvi_json


def populate_serious_adverse_event_data(pvi_json, extracted_datajson):
    serious_adverse_event = get_ws1_all_data(extracted_datajson, "10042")
    serious_adverse_event_dict = get_events_data_dict(serious_adverse_event)
    val = serious_adverse_event_dict.get("Specify the rationale for causality to study\ntreatment:", None)
    if val not in [None, ""]:
        pvi_json["productEventMatrix"][0]["relatednessAssessments"][0]["result"]["value"] = val
    summary = ""
    treatement_adm = serious_adverse_event_dict.get("Specify the rationale for causality to study\ntreatment administration:", None)
    if treatement_adm not in [None, ""]:
        summary = "Specify the rationale for causality to study treatment administration: " + treatement_adm

    for key in serious_adverse_event_dict.keys():
        if "Narrative" in key:
            if serious_adverse_event_dict[key] not in [None, ""]:
                summary = summary + "\n" + key + ": " + serious_adverse_event_dict[key]

    pvi_json["summary"]["caseDescription"] = summary

    return pvi_json


def empty_event_section():
    events = {"continuing": null,
            "country": null,
            "endDate": null,
            "hospitalizationEndDate": null,
            "hospitalizationEndDate_acc": null,
            "hospitalizationStartDate": null,
            "hospitalizationStartDate_acc": null,
            "medicallyConfirmed": null,
            "outcome": null,
            "reactionCoded": null,
            "reportedReaction": null,
            "seq_num": 1,
            "seriousnesses": [{"value": null, "value_acc": 0.95}],
            "startDate": null}
    return events


def concom_dose_unit_freq_indication_filtering(pvi_json):
    for prod_index in range(len(pvi_json["products"])):
        for doseinfo_index in range(len(pvi_json["products"][prod_index]["doseInformations"])):
            unit = pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["description"]
            pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["dose_inputValue"] = unit
            if unit not in [None, ""]:
                if "other" in unit.lower():
                    dose_val = re.sub("other", "", unit).strip()
                    pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["description"] = dose_val

            frequency_value = pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["frequency_value"]
            if "Other" in frequency_value:
                pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["frequency_value"] = re.sub("Other", "", frequency_value).strip()

            route_value = pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["route_value"]
            if "Other" in route_value:
                pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["route_value"] = re.sub("Other", "", route_value).strip()

        #  indication value filtering   #############3
        for indication_indx in range(len(pvi_json["products"][prod_index]["indications"])):
            indication = pvi_json["products"][prod_index]["indications"][indication_indx]["reportedReaction"]
            if indication not in [None, ""]:
                pvi_json["products"][prod_index]["indications"][indication_indx]["reportedReaction"] = re.sub("\n", " ", indication).strip()

    return pvi_json


def tests_seqnum(pvi_json):
    for test_indx in range(len(pvi_json["tests"])):
        pvi_json["tests"][test_indx]["seq_num"] = str(test_indx+1)
    return pvi_json

def get_postprocessed_json(pvi_json, extracted_json):
    try:
        pvi_json = study_number(pvi_json, extracted_json)
    except:
        print("issue at study_number")
    try:
        pvi_json = set_names(pvi_json)
    except:
        print("issue at setting names")
    try:
        pvi_json = patient_id(pvi_json)
    except:
        print("issue at patient id")
    #try:
    pvi_json = populate_adverse_event_data(pvi_json, extracted_json)
    #except:
        #print("issue at populate_adverse_event_data")
    try:
        pvi_json = receipt_date(pvi_json)
    except:
        print("issue at receipt date")
    try:
        pvi_json = patient_dob(pvi_json)
    except:
        print("issue at patient dob")
    #try:
    pvi_json = event_date(pvi_json)
    #except:
        #print("issue at event date")
    try:
        pvi_json = populate_serious_adverse_event_data(pvi_json, extracted_json)
    except:
        print("issue at populate_serious_adverse_event_data")

    try:
        # only date formating happens here
        pvi_json = products_date_formating(pvi_json)
    except:
        print("issue at product")
    try:
        pvi_json = test_date(pvi_json)
    except:
        print("issue at test date")

    #try:

    pvi_json = concom_products_filtering_basedon_date(pvi_json)
    #except:
    #    print("issue at concom_products")

    pvi_json = concom_dose_unit_freq_indication_filtering(pvi_json)

    pvi_json = concom_procedures_surgeries(pvi_json)

    #try:
    pvi_json = medicalhistory_date(pvi_json)
    #except:
    #    print("issue at medicalhistory_date")'''

    try:
        pvi_json = tests_seqnum(pvi_json)
    except:
        print("issue at test seq num method")

    return pvi_json
