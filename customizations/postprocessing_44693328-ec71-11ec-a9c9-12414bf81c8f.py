import re
import json
import traceback
import pycountry
from nameparser import HumanName
import datetime


def update_tests(pvi_json):
    new_test_list = []
    for test in pvi_json['tests']:
        check_flag = False
        for new_test in new_test_list:
            if test['testName'] == new_test['testName']:
                check_flag = True
                if new_test['testResult']:
                    new_test['testResult'] += '; ' + test['testResult']
                else:
                    new_test['testResult'] = test['testResult']
        if not check_flag:
            new_test_list.append(test)

    pvi_json['tests'] = new_test_list
    return pvi_json


def update_products(pvi_json):
    new_prod_list = []
    for prod in pvi_json['products']:
        check_flag = False
        for new_prod in new_prod_list:
            if prod['license_value'] == new_prod['license_value']:
                check_flag = True
                new_prod['doseInformations'].extend(prod['doseInformations'])

        if not check_flag:
            new_prod_list.append(prod)

    new_prod_list = [product for product in new_prod_list if product['license_value']]
    pvi_json['products'] = new_prod_list

    return pvi_json


def update_patient(pvi_json):
    data = pvi_json['summary']['reporterComments'].split('\n')
    dob = ''
    ethnicity = ''
    for row in data:
        if 'Patient DOB' in row:
            dob = row.strip('Patient DOB:').strip()
        elif 'Ethnicity' in row:
            ethnicity = row.strip('Ethnicity:').strip()

    if len(dob) == 4:
        dob = '01-JUL-'+dob

    pvi_json['patient']['patientDob'] = dob
    pvi_json['patient']['ethnicGroup'] = ethnicity

    for medhis in pvi_json['patient']['medicalHistories']:
        if medhis['historyNote']:
            medhis['historyNote'] = str(medhis['historyNote'].strip(',') or None)
    return pvi_json


def update_events(pvi_json):
    for event in pvi_json['events']:
        reportedReaction = event['reportedReaction']
        reportedReaction = re.search('AE(.*)-', reportedReaction).group()
        event['reportedReaction'] = str(reportedReaction.replace('AE', '').replace('-', '').strip() or None)

    return pvi_json


def update_country(pvi_json):
    country = pvi_json['study']['centerNumber']
    country_code = country[:2]
    pvi_json['reporters'][0]['country'] = pycountry.countries.get(alpha_2=country_code).name

    return pvi_json


def split_reporter_name(pvi_json):
    name = pvi_json['reporters'][0]['givenName']
    hnObject = HumanName(name)

    pvi_json['reporters'][0]['title'] = hnObject.title if hnObject.title else None
    pvi_json['reporters'][0]['firstName'] = hnObject.first if hnObject.first else None
    pvi_json['reporters'][0]['middleName'] = hnObject.middle if hnObject.middle else None
    pvi_json['reporters'][0]['lastName'] = hnObject.last if hnObject.last else None
    pvi_json['reporters'][0]['givenName'] = None
    return pvi_json


def validate_date_format(given_date):
    if given_date:
        dd_mmm_yyyy_hh_mm_ss = re.search(r"^\d{2}-[A-Z]{3}-\d{4} \d{2}:\d{2}:\d{2}$", given_date)       # 13-JUN-2022 12:30:00
        dd_mmm_yyyy = re.search(r"^\d{2}-[A-Z]{3}-\d{4}$", given_date)                                  # 13-JUN-2022
        d_mmm_yyyy = re.search(r"^\d{1}-[A-Z]{3}-\d{4}$", given_date)                                   # 5-JUN-2022
        mmm_yyyy = re.search(r"^[A-Z]{3}-\d{4}$", given_date)                                           # JUN-2022
        yyyy = re.search(r"^\d{4}$", given_date)                                                        # 2022

        date_formats = ["%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%d-%b-%Y", "%b-%Y", "%Y"]
        date_patterns = [dd_mmm_yyyy_hh_mm_ss, dd_mmm_yyyy, d_mmm_yyyy, mmm_yyyy, yyyy]
        given_date = None
        for idx in range(len(date_patterns)):
            if date_patterns[idx]:
                try:
                    given_date = date_patterns[idx].group()
                    if idx == 2:
                        given_date = '0' + given_date                                                   # application support zero-padded decimal
                    date_obj = datetime.datetime.strptime(given_date, date_formats[idx])
                except ValueError:
                    given_date = None
                break
        return given_date


def validate_date(pvi_json):
    # print(pvi_json)
    try:
        for key, value in pvi_json.items():
            if isinstance(value, dict):
                validate_date(value)
            elif isinstance(value, list):
                for val in value:
                    validate_date(val)
            else:
                if key.endswith("Date") or key.endswith("date"):
                    pvi_json.update({key: validate_date_format(value)})
    except:
        traceback.print_exc()
    return pvi_json


def get_postprocessed_json(pvi_json, w1_json):
    # extracted_df = pd.DataFrame(w1_json)
    # extracted_df.set_index('class', inplace=True)
    # print(extracted_df)
    print("inside postprocessing...")
    try:
        pvi_json = update_tests(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_products(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_patient(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_events(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_country(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = split_reporter_name(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = validate_date(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json







# extracted_json = json.load(open('/home/rxlogix/Downloads/gfp-forms/genmab-csv/CSV-outer-json.json')) #remove
# pvi_json = json.load(open('/home/rxlogix/Downloads/gfp-forms/genmab-csv/CSV-outer-json.json')) #remove
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_json)))
