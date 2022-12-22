import datetime
import json
import re
import copy
import traceback

import pandas as pd
from dateutil import parser
from datetime import date


def check_code_list_matching_values_for_dose(dose):
    unit_list_file_location = '/home/ubuntu/backendservice/utility/template/customizations/Dose_Unit.csv'
    unit_list_df = pd.read_csv(unit_list_file_location)
    dose_unit = ' '.join(dose.split(' ')[1:])
    result = unit_list_df['UNIT'].str.lower().isin([dose_unit]).any()
    return result


def check_code_list_matching_values_for_frequency(frequency):
    frequency_list_file_location = '/home/ubuntu/backendservice/utility/template/customizations/Dose_Frequency.csv'
    frequency_list_df = pd.read_csv(frequency_list_file_location)
    result = frequency_list_df['UNIT'].str.lower().isin([frequency]).any()
    return result


date_ptn = re.compile("\d{2}-\w*-\d{4}")  # DD-MMM-YYYY
MM_YYYY_ptn = re.compile("\w*-\d{4}")  # MMM-YYYY
DD_MM_YYYY_ptn = re.compile("\d{2}-\d{2}-\d{4}")  # DD-MM-YYYY

months = ['JAN', "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def date_format_update(given_date):
    given_date = re.sub("/", "-", given_date).strip()
    given_date = given_date.split("-")
    given_date = "".join(given_date[:])
    if given_date.lower() not in ["unk", "un"]:
        given_date = given_date.replace("JUN", "ABC")
        for str_rm in [" 00:00:00", "UN-UNK-", "un-unk-", "unk-", "UNK-", "^UN-", "^un-", "\n", "UN"]:
            given_date = re.sub(str_rm, "", given_date).strip()
        given_date = given_date.replace("ABC", "JUN")
        # dd_mmm_yyyy = re.compile(r"^\d{2}-\w{3}-20\d{2}")  # 04-JAN-2021
        # d_mmm_yyyy = re.compile(r"^\d{1}-\w{3}-20\d{2}")  # 4-JAN-2021
        # mmm_yyyy = re.compile(r"^\w{3}-20\d{2}$")  # JAN/2021
        # yyyy = re.compile(r"^20\d{2}$")  # 2021
        dd_mmm_yyyy = re.compile(r"^\d{2}[A-Z]{3}\d{4}")  # 04-JAN-2021
        d_mmm_yyyy = re.compile(r"^\d{1}[A-Z]{3}\d{4}")  # 4-JAN-2021
        mmm_yyyy = re.compile(r"^[A-Z]{3}\d{4}$")  # JAN/2021
        yyyy = re.compile(r"^\d{4}$")  # 2021

        dd_mmm_yyyy_ptn = re.findall(dd_mmm_yyyy, given_date)
        d_mmm_yyyy_ptn = re.findall(d_mmm_yyyy, given_date)
        mmm_yyyy_ptn = re.findall(mmm_yyyy, given_date)
        yyyy_ptn = re.findall(yyyy, given_date)
        # print(dd_mmm_yyyy_ptn,d_mmm_yyyy_ptn,mmm_yyyy_ptn,yyyy_ptn)
        # if len(dd_mmm_yyyy_ptn) > 0:
        #     given_date = dd_mmm_yyyy_ptn[0]
        #     given_date = given_date[:2] + "-" + given_date[2:5] + "-" + given_date[5:]
        # elif len(d_mmm_yyyy_ptn) > 0:
        #     given_date = "0" + d_mmm_yyyy_ptn[0]
        # elif len(mmm_yyyy_ptn) > 0:
        #     given_date = mmm_yyyy_ptn[0]
        #     given_date = given_date[:3] + "-" + given_date[3:]
        # elif len(yyyy_ptn) > 0:
        #     given_date = yyyy_ptn[0]

        if len(dd_mmm_yyyy_ptn) > 0:
            try:
                given_date = dd_mmm_yyyy_ptn[0]
                given_date = given_date[:2] + "-" + given_date[2:5] + "-" + given_date[5:]
                obj = datetime.datetime.strptime(given_date, "%d-%b-%Y")
            except:
                given_date = None

        elif len(d_mmm_yyyy_ptn) > 0:
            try:
                given_date = "0" + d_mmm_yyyy_ptn[0]
                given_date = given_date[:2] + "-" + given_date[2:5] + "-" + given_date[5:]
                obj = datetime.datetime.strptime(given_date, "%d-%b-%Y")
            # if obj:
            #     pass
            except:
                given_date = None


        elif len(mmm_yyyy_ptn) > 0:
            try:
                given_date = mmm_yyyy_ptn[0]
                given_date = given_date[:3] + "-" + given_date[3:]
                obj = datetime.datetime.strptime(given_date, "%b-%Y")
            # if obj:
            #     pass
            except:
                given_date = None
        elif len(yyyy_ptn) > 0:
            try:
                given_date = yyyy_ptn[0]
                obj = datetime.datetime.strptime(given_date, "%Y")
            # if obj:
            #     pass
            except:
                given_date = None

    return given_date


def empty_medhistory():
    medhis = {"continuing": None,
              "endDate": None,
              "familyHistory": None,
              "historyConditionType": None,
              "historyNote": None,
              "reactionCoded": None,
              "reportedReaction": None,
              "startDate": None
              }
    return medhis


def tests_empty_sec():
    tests_empty = [
        {
            "seq_num": 1,
            "startDate": None,
            "testAssessment": None,
            "testHigh": None,
            "testLow": None,
            "testName": None,
            "testNotes": None,
            "testResult": None,
            "testResultUnit": None
        }
    ]
    return tests_empty


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

                if "Diagnostic" not in note and val == "prior":
                    med = copy.deepcopy(empty_medhistory())
                    start_date = pvi_json["tests"][indx]["startDate"]
                    if "Events (SAE)" not in start_date:
                        med["startDate"] = start_date
                    testname = pvi_json["tests"][indx]["testName"]
                    if "ous Adverse" not in testname:
                        med["reportedReaction"] = testname
                    med["historyNote"] = ""  # no need to populate as per mapping doc
                    medhis_list.append(med)
                else:
                    test_data = pvi_json["tests"][indx]
                    test_data["testNotes"] = ""
                    tests_list.append(test_data)
            else:
                test_data = pvi_json["tests"][indx]
                test_data["testNotes"] = ""
                tests_list.append(test_data)

    if len(tests_list) == 0:
        tests_list = tests_empty_sec
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
    if dob not in [None, ""]:
        dob = re.sub("Male", "", dob)
        dob = re.sub("Female", "", dob)
        dob = re.sub("  ", " ", dob)
        if dob not in ["", None]:
            pvi_json["patient"]["age"]["inputValue"] = dob

    gender = pvi_json["patient"]["gender"]
    if "Female" in gender or "female" in gender:
        pvi_json["patient"]["gender"] = "Female"
    elif "Male" in gender or "male" in gender:
        pvi_json["patient"]["gender"] = "Male"
    return pvi_json


def products_date_formating(pvi_json):
    prod_index = 0
    # print(len(pvi_json["products"]))
    for prod in pvi_json["products"]:
        dose_index = 0
        for doseinfo in prod["doseInformations"]:
            dose_inputValue = pvi_json["products"][prod_index]["doseInformations"][dose_index]["dose_inputValue"]
            if dose_inputValue not in [None, ""]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["description"] = re.sub("\n", " ",
                                                                                                         dose_inputValue)

            frequency_value = pvi_json["products"][prod_index]["doseInformations"][dose_index]["frequency_value"]
            if frequency_value not in [None, ""]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["frequency_value"] = re.sub("\n", " ",
                                                                                                             frequency_value)

            startdate = pvi_json["products"][prod_index]["doseInformations"][dose_index]["startDate"]

            if startdate not in ["", None]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["startDate"] = date_format_update(
                    startdate)

            enddate = pvi_json["products"][prod_index]["doseInformations"][dose_index]["endDate"]
            if enddate not in ["", None]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["endDate"] = date_format_update(
                    enddate)

            continuing = doseinfo["continuing"]
            if continuing not in [None, ""]:
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["doseContinuing"] = continuing.strip()
                pvi_json["products"][prod_index]["doseInformations"][dose_index]["continuing"] = None
            dose_index += 1
        # print(prod_index)
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
        pvi_json["study"]["studyNumber"] = studynum + ".Part2"
    else:
        pvi_json["study"]["studyNumber"] = studynum + ".Part1"

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
            day = 1
        elif len(givendate.split("-")) == 1 and len(givendate) == 4:
            date_yearonly = True

        if not date_yearonly:
            if year and month and day:
                outputdate = date(int(year), months.index(month) + 1, int(day))
    return outputdate


# Function to change all the values to none in any dictionary or List
def change_reference_values_to_none(pvi_json):
    for key, value in pvi_json.items():
        if isinstance(value, dict):
            change_reference_values_to_none(value)
        elif isinstance(value, list):
            for val in value:
                change_reference_values_to_none(val)
        else:
            pvi_json.update({key: None})
    return pvi_json


# Function to process date in DD-MMM-YYYY Format (supported by application)
def process_date(any_date):
    if any_date not in [None, '']:
        if '/' in any_date:
            any_date = any_date.replace('/', ' ')
        if '-' in any_date:
            any_date = any_date.replace('-', ' ')
        if len(any_date.split()) == 3:
            date_day, date_month, date_year = any_date.split()
            if date_month.lower() == 'unk':
                any_date = date_year
            elif date_day.lower() == 'un':
                any_date = date_month + '-' + date_year
            elif len(date_day) == 1:
                date_day = '0' + date_day
                any_date = date_day + '-' + date_month + '-' + date_year
            else:
                any_date = date_day + '-' + date_month + '-' + date_year
        elif len(any_date.split()) == 2:
            date_month, date_year = any_date.split()
            if date_month.lower() == 'unk':
                any_date = date_year
            else:
                any_date = date_month + '-' + date_year
        else:
            any_date = any_date.strip()
    return any_date


def compare_dates(event_date, start_date, end_date):
    result = True
    if event_date not in [None, '']:
        if len(event_date.split('-')) != 3:
            result = True
        else:
            event_date_day, event_date_month, event_date_year = event_date.split('-')
            event_check_date = date(int(event_date_year), months.index(event_date_month) + 1, int(event_date_day))
            result = date_difference_start(start_date, event_check_date)
            if result == 'Not Include':
                result = False
            elif result == 'Check End':
                result = date_difference_end(end_date, event_check_date)
            elif result == 'Include':
                result = True
    return result


def date_difference_start(start_date, compare_date):
    if start_date not in [None, '']:
        result = 'Include'
        if len(start_date.split('-')) == 3:
            start_date_day, start_date_month, start_date_year = start_date.split('-')
            start_check_date = date(int(start_date_year), months.index(start_date_month) + 1, int(start_date_day))
            if start_check_date >= compare_date:
                result = 'Not Include'
            else:
                delta = abs(compare_date - start_check_date)
                if 'day' in str(delta):
                    if int(str(delta).split()[0]) <= 30:
                        result = 'Include'
                    else:
                        result = 'Check End'
        elif len(start_date.split('-')) == 2:
            com_month = compare_date.month
            start_month = months.index(start_date.split('-')[0]) + 1
            if int(start_date.split('-')[-1]) - compare_date.year >= 1:
                result = 'Not Include'
            elif int(start_date.split('-')[-1]) == compare_date.year:
                if start_month > com_month:
                    result = 'Not Include'
                elif start_month == com_month:
                    if compare_date.day == 1:
                        result = 'Not Include'
                    else:
                        result = 'Include'
                elif com_month - start_month == 1:
                    result = 'Include'
                else:
                    result = 'Check End'
            elif int(start_date.split('-')[-1]) - compare_date.year == -1:
                if com_month == 1 and start_month == 12:
                    result = 'Include'
                else:
                    result = 'Check End'
            else:
                result = 'Check End'
        elif len(start_date.split('-')) == 1:
            if int(start_date.split('-')[-1]) - compare_date.year >= 1:
                result = 'Not Include'
            elif int(start_date.split('-')[-1]) == compare_date.year:
                if compare_date.month == 1 and compare_date.day == 1:
                    result = 'Not Include'
                else:
                    result = 'Include'
            else:
                result = 'Check End'
    else:
        result = 'Check End'
    return result


def date_difference_end(end_date, compare_date):
    if end_date not in [None, '']:
        result = True
        if len(end_date.split('-')) == 3:
            end_date_day, end_date_month, end_date_year = end_date.split('-')
            end_check_date = date(int(end_date_year), months.index(end_date_month) + 1, int(end_date_day))
            delta = abs(compare_date - end_check_date)
            if 'day' in str(delta):
                if int(str(delta).split()[0]) > 30:
                    result = False
            elif str(delta) == '0:00:00':
                result = True
        elif len(end_date.split('-')) == 2:
            com_month = compare_date.month
            end_month = months.index(end_date.split('-')[0]) + 1
            if int(end_date.split('-')[-1]) - compare_date.year > 1:
                result = False
            elif int(end_date.split('-')[-1]) - compare_date.year == 1:
                if com_month == 12 and end_month == 1:
                    result = True
                else:
                    result = False
            elif int(end_date.split('-')[-1]) == compare_date.year:
                if com_month == end_month:
                    result = True
                elif abs(end_month - com_month) == 1:
                    result = True
                else:
                    result = False
            elif int(end_date.split('-')[-1]) - compare_date.year == -1:
                if com_month == 1 and end_month == 12:
                    result = True
                else:
                    result = False
            else:
                result = False
        elif len(end_date.split('-')) == 1:
            if int(end_date.split('-')[0]) == compare_date.year:
                result = True
            elif int(end_date.split('-')[0]) - compare_date.year == 1:
                if compare_date.month == 12:
                    result = True
                else:
                    result = False
            elif compare_date.year - int(end_date.split('-')[0]) == 1:
                if compare_date.month == 1:
                    result = True
                else:
                    result = False
            else:
                result = False
    else:
        result = True
    return result


def compare_dates_tests_section(ON_SET_DATE, start_date):
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
                    if int(str(delta1).split(" ")[0]) > 0:
                        value = "prior"
                    elif int(str(delta1).split(" ")[0]) < 0:
                        value = "after"
                    elif int(str(delta1).split(" ")[0]) == 0:
                        value = "sameday"
                elif "day" not in str(delta1):
                    value = "sameday"
    return value


# Function to filter out concomitant products based on date difference with ae onset date
def process_concomitant_products_filtering(pvi_json):
    products_refresh = []
    sample_prod = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    event_onset_date = process_date(pvi_json['events'][0]['startDate'])
    for prod in pvi_json['products']:
        if prod['license_value'] not in [None, '', 'R2810-ONC-1', 'ous Adver']:
            start_date = process_date(prod['doseInformations'][0]['startDate'])
            end_date = process_date(prod['doseInformations'][0]['endDate'])
            compare_date_result = compare_dates(event_onset_date, start_date, end_date)
            if compare_date_result:
                products_refresh.append(prod)
    if len(products_refresh) == 0:
        products_refresh.append(sample_prod)
    pvi_json['products'] = products_refresh
    return pvi_json


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
        reportedReaction = pvi_json["patient"]["medicalHistories"][indx]["reportedReaction"]
        if reportedReaction not in [None, ""]:
            pvi_json["patient"]["medicalHistories"][indx]["reportedReaction"] = re.sub("\n", "  ", reportedReaction)
        startDate = pvi_json["patient"]["medicalHistories"][indx]["startDate"]
        if startDate not in [None, ""]:
            pvi_json["patient"]["medicalHistories"][indx]["startDate"] = process_date(
                startDate.replace(" 00:00:00", ""))
        endDate = pvi_json["patient"]["medicalHistories"][indx]["endDate"]
        if endDate not in [None, ""]:
            pvi_json["patient"]["medicalHistories"][indx]["endDate"] = process_date(endDate.replace(" 00:00:00", ""))

    return pvi_json


def patient_id(pvi_json):
    id = pvi_json["patient"]["patientId"]
    if id not in ["", None]:
        id = re.sub(",", "", id)
        pvi_json["patient"]["patientId"] = id[0:-3] + "-" + id[-3:]

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
    pvi_json["events"][0]["startDate"] = process_date(adverse_event_dict["Start Date"])

    if adverse_event_dict['Outcome of AE'].lower() == 'not recovered/not resolved':
        adverse_event_dict['Outcome of AE'] = 'Not Recovered'
    if adverse_event_dict['Outcome of AE'].lower() == 'recovering/resolving':
        adverse_event_dict['Outcome of AE'] = 'Recovering'
    if adverse_event_dict['Outcome of AE'].lower() == 'recovered/resolved with sequelae':
        adverse_event_dict['Outcome of AE'] = 'Recovered with Sequelae'
    pvi_json['events'][0]['outcome'] = adverse_event_dict['Outcome of AE']
    '''
    if adverse_event_dict["Outcome of AE"] not in ["", None]:
        if adverse_event_dict["Outcome of AE"].lower() in ["not recovered / not resolved", "not recovered/not resolved"]:
            pvi_json["events"][0]["outcome"] = "Not recovered / Not resolved"
        elif adverse_event_dict["Outcome of AE"].lower() in ["recovered / resolved", "recovered/resolved"]:
            pvi_json["events"][0]["outcome"] = "Recovered/Resolved"
    '''
    pvi_json["events"][0]["endDate"] = process_date(adverse_event_dict["Resolution date"])
    pvi_json["events"][0]["eventCategory"][0]["value"] = adverse_event_dict["AE most extreme severity CTCAE grade"]

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

    omic = adverse_event_dict[
        "Other important medical event (It does not meet\nany of the above serious criteria, but may\njeopardize the Patient, and may require medical\nor surgical intervention to prevent one of the\noutcomes listed above)."]
    if omic not in [None, ""]:
        omic_all = re.findall("^checked", omic.lower())
        if len(omic_all) == 1:
            event_seriousness_dict_list.append({"value": "Other Medically Important Condition", "value_acc": 0.95})

    if adverse_event_dict["If Other, specify:"] not in [None, ""]:
        event_seriousness_dict_list.append({"value": "Other Medically Important Condition", "value_acc": 0.95})

    pvi_json["events"][0]["seriousnesses"] = event_seriousness_dict_list

    return pvi_json


def get_relatedness_val(val):
    if val in ["", None]:
        val = "Not Reported"
    if "NOT RELATED" in val.upper() or "NO" in val.upper():
        val = "Not Related"
    elif "RELATED" in val.upper() or "YES" in val.upper():
        val = "Related"
    elif "UNKNOWN" in val.upper():
        val = "Unknown"
    if "not applicable" in val.lower() or "not checked" in val.lower():
        val = ""

    return val


def populate_serious_adverse_event_data(pvi_json, extracted_datajson):
    serious_adverse_event = get_ws1_all_data(extracted_datajson, "10042")
    serious_adverse_event_dict = get_events_data_dict(serious_adverse_event)
    val = serious_adverse_event_dict.get("Specify the rationale for causality to study\ntreatment:", "")
    relatedness = ""
    if val not in [None, ""]:
        relatedness = get_relatedness_val(val)
    elif val in [None, ""]:
        adverse_event_data = get_ws1_all_data(extracted_datajson, "10047")
        adverse_event_data = get_events_data_dict(adverse_event_data)
        relatedness = get_relatedness_val(adverse_event_data["AE suspected to be caused by study treatment?"])
        relatedness = get_relatedness_val(relatedness)
    pvi_json["productEventMatrix"][0]["relatednessAssessments"][0]["result"]["value"] = relatedness

    summary = ""
    treatement_adm = serious_adverse_event_dict.get(
        "Specify the rationale for causality to study\ntreatment administration:", None)
    if treatement_adm not in [None, ""]:
        summary = "Specify the rationale for causality to study treatment administration: " + treatement_adm

    key_indx = 0
    for key in serious_adverse_event_dict.keys():
        if "Narrative" in key:
            if serious_adverse_event_dict[key] not in [None, ""]:
                if key_indx == 6:
                    summary = summary + "\nEvent Narrative/Description:"
                summary = summary + " " + serious_adverse_event_dict[key]
        key_indx += 1
    pvi_json["summary"]["caseDescription"] = summary.strip()

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
            dose_inputValue = pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["dose_inputValue"]
            frequency_value = pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["frequency_value"]
            dose_and_freq = ""
            if dose_inputValue not in [None, ""]:
                dose_and_freq = "Dose: " + dose_inputValue
            if frequency_value not in [None, ""]:
                dose_and_freq = dose_and_freq + " Frequency:" + frequency_value
            pvi_json["products"][prod_index]["doseInformations"][doseinfo_index]["description"] = dose_and_freq

        #  indication value filtering   #############
        for indication_indx in range(len(pvi_json["products"][prod_index]["indications"])):
            indication = pvi_json["products"][prod_index]["indications"][indication_indx]["reportedReaction"]
            if indication not in [None, ""]:
                pvi_json["products"][prod_index]["indications"][indication_indx]["reportedReaction"] = re.sub("\n", " ",
                                                                                                              indication).strip()

    return pvi_json


def tests_seqnum_garbageremoved(pvi_json):
    for test_indx in range(len(pvi_json["tests"])):
        pvi_json["tests"][test_indx]["seq_num"] = str(test_indx + 1)
        testName = pvi_json["tests"][test_indx]["testName"]
        if testName not in [None, ""]:
            pvi_json["tests"][test_indx]["testName"] = re.sub("\n", " ", testName)

    return pvi_json


def get_garbageremoved_concom(pvi_json):
    for indx in range(len(pvi_json["products"])):
        if pvi_json["products"][indx]["license_value"] not in [None, '']:
            prod = pvi_json["products"][indx]["license_value"]
            prod = re.sub("\n", " ", prod)
            prod = re.sub("MH\d{1}:\S*", "", prod)
            pvi_json["products"][indx]["license_value"] = prod
            indication_original = pvi_json["products"][indx]["indications"][0]["reportedReaction"]
            indication_list = []
            for data in indication_original.split("AE:"):
                if data not in [None, ""]:
                    data = data.split("_")
                    if len(data) == 3:
                        data = re.sub("\n", " ", data[1]).strip()
                    else:
                        data = re.sub("\n", " ", data[0]).strip()
                    indication_list.extend([{"reactionCoded": None, "reportedReaction": data}])

            if len(indication_list) > 1:
                if "Medical History" in indication_list[0]["reportedReaction"] or "Adverse Event" in indication_list[0][
                    "reportedReaction"]:
                    indication_list.pop(0)

            if len(indication_list) > 0:
                pvi_json["products"][indx]["indications"] = indication_list
            else:
                pvi_json["products"][indx]["indications"] = [{"reactionCoded": None, "reportedReaction": None}]
    return pvi_json


def emptysectionsremoval(section, section_keys):
    section_list = []
    for indx in range(len(section)):
        for key in section_keys:
            if section[indx][key] not in ["", None]:
                section_list.append(section[indx])
                break

    return section_list


def empty_prod_section():
    prod = {
        "actionTaken": {
            "value": "",
            "value_acc": 0.95
        },
        "concentration": [
            {
                "unit": None,
                "value": None
            }
        ],
        "dosageForm_value": None,
        "doseInformations": [
            {
                "continuing": None,
                "customProperty_batchNumber_value": None,
                "customProperty_expiryDate": None,
                "description": "",
                "doseContinuing": "",
                "dose_inputValue": "",
                "duration": None,
                "endDate": None,
                "frequency_value": "",
                "route_value": "",
                "startDate": ""
            }
        ],
        "indications": [
            {
                "reactionCoded": None,
                "reportedReaction": ""
            }
        ],
        "ingredients": [
            {
                "strength": None,
                "strength_acc": None,
                "unit": None,
                "unit_acc": None,
                "value": None,
                "value_acc": 0.95
            }
        ],
        "license_value": "",
        "regimen": None,
        "role_value": "",
        "seq_num": 1
    }
    return prod


# adding suspect product here in this method as there is no section for suspect product in form
def add_suspect_product(pvi_json, extracted_datajson):
    # products = pvi_json["products"]
    prod = empty_prod_section()
    if pvi_json['study']['studyNumber'] == 'R2810-ONC-1788.Part1':
        prod["license_value"] = "CEMIPLIMAB/PLACEBO"
    else:
        prod["license_value"] = "CEMIPLIMAB"
    prod["role_value"] = "suspect"
    prod["indications"][0]["reportedReaction"] = "Squamous cell carcinoma of skin"

    adverse_event = get_ws1_all_data(extracted_datajson, "10047")
    adverse_event_dict = get_events_data_dict(adverse_event)
    action_taken = adverse_event_dict["Action taken with study treatment"]
    if action_taken not in ["", None]:
        if "dosage maintained" in action_taken.lower():
            action_taken = "Dose Not Changed"
        elif "drug discontinued (temp)" in action_taken.lower():
            action_taken = "Dose Temporarily withdrawn"
        elif "dose delayed" in action_taken.lower() or "dose interrupted" in action_taken.lower():
            action_taken = "Dose Temporarily withdrawn"

    prod["actionTaken"]["value"] = action_taken
    # products_all = [prod]
    if pvi_json['products'][0]['license_value'] not in [None, '']:
        pvi_json['products'].insert(0, prod)
    else:
        pvi_json['products'] = [prod]
    # pvi_json["products"] = products_all
    # update seq num
    for seq in range(len(pvi_json["products"])):
        pvi_json["products"][seq]["seq_num"] = seq + 1

    return pvi_json


# and med_data["startDate"] not in ["Events (SAE)", "EPORT_24-MAR-2021", "rmaceuticals"]:
# filtering header from medical history
def remove_header_medicalhistory(pvi_json):
    medhis = []
    for med_data in pvi_json["patient"]["medicalHistories"]:
        if med_data["reportedReaction"] not in ['R2810-ONC-1788_SAE R']:
            if med_data["startDate"] not in ["Events (SAE)", "rmaceuticals", "Events-(SAE)"]:
                medhis.append(med_data)
    pvi_json["patient"]["medicalHistories"] = medhis
    return pvi_json


def remove_empty_seriousness_criteria(pvi_json):
    indx = 0
    for event in pvi_json["events"]:
        criteria = []
        for ser in event["seriousnesses"]:
            if ser["value"] not in [None, ""]:
                criteria.append(ser)
        pvi_json["events"][indx]["seriousnesses"] = criteria
        indx += 1
    return pvi_json


def filter_medicalhistory(pvi_json):
    medhis = pvi_json["patient"]["medicalHistories"]
    medhis_filtered = []
    for indx in range(len(medhis)):
        # Atleast one field should be having data else ignore section
        if medhis[indx]["startDate"] or medhis[indx]["reportedReaction"] or medhis[indx]["reactionCoded"] or \
                medhis[indx]["historyNote"] or medhis[indx]["historyConditionType"] or medhis[indx]["familyHistory"] or \
                medhis[indx]["endDate"] or medhis[indx]["continuing"]:
            if medhis[indx]["startDate"] not in [None, ""]:
                if "Events (SAE)" in medhis[indx]["startDate"]:
                    medhis[indx]["startDate"] = ""
                if "EPORT_24-MAR-2021" in medhis[indx]["startDate"]:
                    medhis[indx]["startDate"] = ""

            reportedreaction = medhis[indx]["reportedReaction"]
            if reportedreaction not in [None, ""]:
                if "ous Adverse" in reportedreaction or "R2810-ONC-1788_SAE R" in reportedreaction:
                    medhis[indx]["reportedReaction"] = ""

            note = medhis[indx]["historyNote"]
            if note not in ["", None]:
                note = re.sub("Site of Radiation:", "&&Site of Radiation:", note)
                note = re.sub("Lymph Node Other, specify:", "&&Lymph Node Other, specify :", note)
                note = re.sub("Side of Lymph Node Lesion:", "&&Side of Lymph Node Lesion :", note)
                note = re.sub("Lymph Node Location:", "&&Lymph Node Location :", note)

                note = re.sub("\\n", " ", note)
                note = re.sub("&&", " \n", note)
            medhis[indx]["historyNote"] = note
            medhis_filtered.append(medhis[indx])

    pvi_json["patient"]["medicalHistories"] = medhis_filtered
    return pvi_json


def tests_filtering(pvi_json):
    for indx in range(len(pvi_json["tests"])):
        if "If Other, specify:" in pvi_json["tests"][indx]["testNotes"] or "Reason for surgery/procedure" in \
                pvi_json["tests"][indx]["testNotes"]:
            pvi_json["tests"][indx]["testNotes"] = ""

    return pvi_json


def filetering_medhis(pvi_json):
    for indx in range(len(pvi_json["patient"]["medicalHistories"])):
        if "If Other, specify:" in pvi_json["patient"]["medicalHistories"][indx][
            "historyNote"] or "Reason for surgery/procedure" in pvi_json["patient"]["medicalHistories"][indx][
            "historyNote"]:
            pvi_json["patient"]["medicalHistories"][indx]["historyNote"] = ""

    return pvi_json


def process_dose_units_and_description(pvi_json):
    for prod in pvi_json['products']:
        for dose in prod['doseInformations']:
            if dose['dose_inputValue'] not in [None, '']:
                dose['dose_inputValue'] = convert_units(dose['dose_inputValue'])
                dose['description'] = convert_units(dose['description'])
                result_dose = check_code_list_matching_values_for_dose(dose['dose_inputValue'].lower())
                if dose['frequency_value']:
                    result_freq = check_code_list_matching_values_for_frequency(dose['frequency_value'].lower())
                else:
                    result_freq = False
                if result_dose and result_freq:
                    dose['description'] = None
                elif result_dose and not result_freq:
                    if dose['frequency_value'] not in [None, '']:
                        dose['description'] = 'Frequency: ' + dose['frequency_value']
                    else:
                        dose['description'] = None
                    dose['frequency_value'] = None
                elif not result_dose and result_freq:
                    dose['description'] = 'Dose: ' + dose['dose_inputValue']
                    dose['dose_inputValue'] = None
                else:
                    dose['dose_inputValue'] = dose['frequency_value'] = None
    return pvi_json


def process_bcc_diagnosis(pvi_json, extracted_json):
    try:
        data = [x['value'] for x in extracted_json if x['AnnotID'] == '10048'][0]
    except:
        data = []
    if data:
        for every in data:
            if len(every) == 9 and every[1] not in [None, '']:
                med_his = change_reference_values_to_none(copy.deepcopy(pvi_json['patient']['medicalHistories'][0]))
                med_his['reportedReaction'] = every[4].replace('\n', ' ')
                med_his['startDate'] = process_date(every[5])
                if every[6] not in [None, '']:
                    med_his['historyNote'] = 'Surgery Location: ' + every[6].replace('\n', ' ')
                if every[7] not in [None, '', 'Other', 'other']:
                    if med_his['historyNote']:
                        med_his['historyNote'] = med_his['historyNote'] + ', If non-surgical, select local modality: ' + \
                                                 every[7].replace('\n', ' ')
                    else:
                        med_his['historyNote'] = 'If non-surgical, select local modality: ' + every[7].replace('\n',
                                                                                                               ' ')
                if every[8] not in [None, '']:
                    if med_his['historyNote']:
                        med_his['historyNote'] = med_his['historyNote'] + ', If non-surgical, select local modality: ' + \
                                                 every[7].replace('\n', ' ')
                    else:
                        med_his['historyNote'] = 'If non-surgical, select local modality: ' + every[7].replace('\n',
                                                                                                               ' ')
                if med_his['reportedReaction'] not in [None, '']:
                    pvi_json['patient']['medicalHistories'].append(med_his)
    return pvi_json


def process_country_code(pvi_json):
    country_code_list_file_location = '/home/ubuntu/backendservice/utility/template/customizations/ISO_Codes.csv'
    country_code_df = pd.read_csv(country_code_list_file_location)
    country_code_df['Code'] = country_code_df['Code'].astype(str).str.zfill(3)
    code = pvi_json['literatures'][0]['author'].replace('Site Name ', '')[0:3]
    result = country_code_df['Code'].str.lower().isin([code]).any()
    country = None
    if result:
        for index in range(len(country_code_df['Code'])):
            if country_code_df['Code'].iloc[index] == code:
                country = country_code_df['Country Name'].iloc[index]
                break
    if country:
        pvi_json['events'][0]['country'] = country
    pvi_json['literatures'][0]['author'] = None
    return pvi_json


def convert_units(dose):
    if dose:
        if ' mg' in dose:
            dose = dose.replace(' mg', ' milligram')
        start_index = dose.find(' g')
        if start_index != -1:
            if len(dose) <= start_index + 2:
                dose = dose.replace(' g', ' gram')
            elif not dose[start_index + 2].isalpha():
                dose = dose.replace(' g', ' gram')
        if ' ml' in dose:
            dose = dose.replace(' ml', ' milliliter')
        elif 'mL' in dose:
            dose = dose.replace('mL', 'milliliter')
        if ' mcg' in dose:
            dose = dose.replace(' mcg', ' microgram')
    return dose


def process_other_if_specify_indication_for_concom_prod(pvi_json, extracted_json):
    try:
        data = [x['value'] for x in extracted_json if x['AnnotID'] == '10005'][0]
    except:
        data = []
    if data:
        for prod in pvi_json['products']:
            if prod['role_value'] == 'CONCOMITANT':
                for indications in prod['indications']:
                    if indications['reportedReaction'] == 'Other':
                        for each in data:
                            if prod['license_value'] == each[1].replace('\n', ' '):
                                indications['reportedReaction'] = each[14].replace('\n', ' ')
                                break
    return pvi_json


def get_postprocessed_json(pvi_json, extracted_json):
    try:
        pvi_json = study_number(pvi_json, extracted_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = set_names(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = patient_id(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_adverse_event_data(pvi_json, extracted_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = receipt_date(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = patient_dob(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = event_date(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_serious_adverse_event_data(pvi_json, extracted_json)
    except:
        traceback.print_exc()
    try:
        # only date formating happens here
        pvi_json = products_date_formating(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = test_date(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = process_concomitant_products_filtering(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = concom_dose_unit_freq_indication_filtering(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = concom_procedures_surgeries(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = medicalhistory_date(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = tests_seqnum_garbageremoved(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = get_garbageremoved_concom(pvi_json)
    except:
        traceback.print_exc()
    try:
        tests_section_fields = ["startDate", "testAssessment", "testHigh", "testLow", "testName", "testNotes",
                                "testResult", "testResultUnit"]
        pvi_json["tests"] = emptysectionsremoval(pvi_json["tests"], tests_section_fields)
    except:
        traceback.print_exc()

    try:
        medhis_keys = ["continuing", "endDate", "familyHistory", "historyConditionType", "historyNote", "reactionCoded",
                       "reportedReaction", "startDate"]
        pvi_json["patient"]["medicalHistories"] = emptysectionsremoval(pvi_json["patient"]["medicalHistories"],
                                                                       medhis_keys)
    except:
        traceback.print_exc()

    try:
        pvi_json = add_suspect_product(pvi_json, extracted_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = remove_header_medicalhistory(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = remove_empty_seriousness_criteria(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json = filter_medicalhistory(pvi_json)
    except:
        traceback.print_exc()

    try:
        pvi_json['senderCaseUid'] = pvi_json['patient']['patientId']
    except:
        traceback.print_exc()

    try:
        pvi_json = tests_filtering(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = filetering_medhis(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = process_bcc_diagnosis(pvi_json, extracted_json)
    except:
        traceback.print_exc()
    # try:
    pvi_json = process_country_code(pvi_json)
    # except:
    #    print('Error in processing Country Code')
    try:
        pvi_json = process_dose_units_and_description(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = process_other_if_specify_indication_for_concom_prod(pvi_json, extracted_json)
    except:
        traceback.print_exc()
    return pvi_json

