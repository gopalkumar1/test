import re
import copy
import traceback

import pandas as pd
from dateutil import parser
from datetime import date
from datetime import datetime
import json
months = ['JAN', "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


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


# Function to Process Patient Smoking history captured in pvi_aegis element of pvi json
def process_smoking_history(pvi_json):
    med_his = change_reference_values_to_none(copy.deepcopy(pvi_json['patient']['medicalHistories'][0]))
    if pvi_json['aegis_id'] not in [None, '']:
        smoking_status = pvi_json['aegis_id'].split('Status')[-1].split('Number')[0].strip()
        noy_smoked = pvi_json['aegis_id'].split('Smoked')[-1].split('Number of Cigarettes')[0].strip()
        noc_smoked = pvi_json['aegis_id'].split('Per Day')[-1].split('R2810')[0].strip()
        if smoking_status not in [None, '']:
            med_his['reportedReaction'] = smoking_status
            if noy_smoked not in [None, '']:
                med_his['historyNote'] = 'Number of Years Smoked: ' + noy_smoked
            if noc_smoked not in [None, '']:
                if med_his['historyNote']:
                    med_his['historyNote'] = med_his['historyNote'] + '\nNumber of Cigarettes per Day: ' + noc_smoked
                else:
                    med_his['historyNote'] = 'Number of Cigarettes per Day: ' + noc_smoked
            if pvi_json['patient']['medicalHistories'][0]['reportedReaction'] not in [None, '']:
                pvi_json['patient']['medicalHistories'].insert(0, med_his)
            else:
                pvi_json['patient']['medicalHistories'][0] = med_his
    pvi_json['aegis_id'] = None
    return pvi_json


# Function to process study Id based on product
def process_study_id(pvi_json):
    pvi_json['study']['studyNumber'] = 'R2810-ONC-16113-Part2'
    for prod in pvi_json['products']:
        if prod['license_value'].lower() == 'cemiplimab investigational drug 134016 us':
            pvi_json['study']['studyNumber'] = 'R2810-ONC-16113-Part2'
            break
        else:
            pvi_json['study']['studyNumber'] = 'R2810-ONC-16113-Part1'
    return pvi_json


# Function to filter out concomitant products based on date difference with ae onset date
def process_concomitant_products_filtering(pvi_json):
    products_refresh = []
    sample_prod = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    event_onset_date = process_date(pvi_json['events'][0]['startDate'])
    for prod in pvi_json['products']:
        if prod['license_value'] not in [None, '']:
            start_date = process_date(prod['doseInformations'][0]['startDate'])
            end_date = process_date(prod['doseInformations'][0]['endDate'])
            compare_date_result = compare_dates(event_onset_date, start_date, end_date)
            if compare_date_result:
                products_refresh.append(prod)
    if len(products_refresh) == 0:
        products_refresh.append(sample_prod)
    pvi_json['products'] = products_refresh
    return pvi_json


def compare_dates(event_date, start_date, end_date):
    result = True
    if event_date not in [None, '']:
        if len(event_date.split('-')) != 3:
            result = True
        else:
            event_date_day, event_date_month, event_date_year = event_date.split('-')
            event_check_date = date(int(event_date_year), months.index(event_date_month)+1, int(event_date_day))
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
            if int(start_date.split('-')[-1])-compare_date.year >= 1:
                result = 'Not Include'
            elif int(start_date.split('-')[-1]) == compare_date.year:
                if start_month > com_month:
                    result = 'Not Include'
                elif start_month == com_month:
                    if compare_date.day == 1:
                        result = 'Not Include'
                    else:
                        result = 'Include'
                elif com_month-start_month == 1:
                    result = 'Include'
                else:
                    result = 'Check End'
            elif int(start_date.split('-')[-1])-compare_date.year == -1:
                if com_month == 1 and start_month == 12:
                    result = 'Include'
                else:
                    result = 'Check End'
            else:
                result = 'Check End'
        elif len(start_date.split('-')) == 1:
            if int(start_date.split('-')[-1])-compare_date.year >= 1:
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
            if int(end_date.split('-')[-1])-compare_date.year > 1:
                result = False
            elif int(end_date.split('-')[-1])-compare_date.year == 1:
                if com_month == 12 and end_month == 1:
                    result = True
                else:
                    result = False
            elif int(end_date.split('-')[-1]) == compare_date.year:
                if com_month == end_month:
                    result = True
                elif abs(end_month-com_month) == 1:
                    result = True
                else:
                    result = False
            elif int(end_date.split('-')[-1])-compare_date.year == -1:
                if com_month == 1 and end_month == 12:
                    result = True
                else:
                    result = False
            else:
                result = False
        elif len(end_date.split('-')) == 1:
            if int(end_date.split('-')[0]) == compare_date.year:
                result = True
            elif int(end_date.split('-')[0])-compare_date.year == 1:
                if compare_date.month == 12:
                    result = True
                else:
                    result = False
            elif compare_date.year-int(end_date.split('-')[0]) == 1:
                if compare_date.month == 1:
                    result = True
                else:
                    result = False
            else:
                result = False
    else:
        result = True
    return result


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


# Function to process concomitant products data after filtering
def process_concomitant_data(pvi_json):
    for prod in pvi_json['products']:
        prod['role_value'] = 'concomitant'
        prod['license_value'] = prod['license_value'].replace('\n', ' ').strip()
        if prod['indications'][0]['reportedReaction'] not in [None, ''] and prod['indications'][0]['reportedReaction'].lower().replace('\n', '').strip() == 'other':
            prod['indications'][0]['reportedReaction'] = prod['regimen']
            prod['regimen'] = None
        if prod['indications'][0]['reactionCoded'] not in [None, '']:
            prod['indications'][0]['reportedReaction'] = prod['indications'][0]['reactionCoded']
            prod['indications'][0]['reactionCoded'] = None
        if prod['ingredients'][0]['value'] not in [None, '']:
            prod['indications'][0]['reportedReaction'] = prod['ingredients'][0]['value']
        prod['indications'][0]['reportedReaction'] = process_indication_value(prod['indications'][0]['reportedReaction'])
        prod['doseInformations'][0], prod['ingredients'][0] = process_dose_informations(prod['doseInformations'][0], prod['ingredients'][0])
    return pvi_json


# Function to format product indication value
def process_indication_value(indication):
    if indication not in [None, '']:
        indication = indication.replace('\n', ' ')
        if '_' in indication:
            if len(indication.split('_')) == 3:
                indication = indication.split('_')[1]
            elif len(indication.split('_')) == 2:
                if re.match('^\d', indication.split('_')[0]):
                    indication = indication.split('_')[1]
                else:
                    indication = indication.split('_')[0]
    return indication


# Function to process dose Information for all the concomitant products
def process_dose_informations(prod_dose, prod_ind):
    if prod_dose['dose_inputValue'] not in [None, ''] and 'other' in prod_dose['dose_inputValue'].lower():
        prod_dose['dose_inputValue'] = prod_dose['dose_inputValue'].lower().replace('other', prod_ind['strength'])
    prod_dose['dose_inputValue'] = convert_units(prod_dose['dose_inputValue'])
    if prod_dose['dose_inputValue']:
        result = check_code_list_matching_values_for_dose(prod_dose['dose_inputValue'].lower())
        if not result:
            prod_dose['description'] = 'Dose: ' + prod_dose['dose_inputValue']
            prod_dose['dose_inputValue'] = None
    if prod_dose['frequency_value'] not in [None, ''] and prod_dose['frequency_value'].lower() == 'other':
        prod_dose['frequency_value'] = prod_ind['unit']
    if prod_dose['frequency_value']:
        result = check_code_list_matching_values_for_frequency(prod_dose['frequency_value'].lower())
        if not result:
            if prod_dose['description']:
                prod_dose['description'] = prod_dose['description'] + ', Frequency: ' + prod_dose['frequency_value']
            else:
                prod_dose['description'] = 'Frequency: ' + prod_dose['frequency_value']
            prod_dose['frequency_value'] = None
    if prod_dose['route_value'] not in [None, ''] and prod_dose['route_value'].lower() == 'other':
        prod_dose['route_value'] = prod_ind['value_acc']
    prod_dose['startDate'] = process_date(prod_dose['startDate'])
    prod_dose['endDate'] = process_date(prod_dose['endDate'])
    prod_ind = change_reference_values_to_none(prod_ind)
    prod_dose['continuing'] = None
    return prod_dose, prod_ind


# Function to extract suspect products from the unstructured section in form
def process_suspect_product(pvi_json, extracted_json):
    try:
        data = [x['value'] for x in extracted_json if x['AnnotID'] == '10016'][0]
    except:
        data = []
    suspect_prods = []
    suspect_prod_name_list = []
    if data:
        chemo_start_search = re.search(r'\b(Did the subject receive chemotherapy?)\b', data[0])
        ipilimumab_start_search = re.search(r'\b(Did the subject receive Ipilimumab?)\b', data[0])
        if chemo_start_search:
            chemo_start_index = chemo_start_search.start()
        else:
            chemo_start_index = None
        if ipilimumab_start_search:
            ipilimumab_start_index = ipilimumab_start_search.start()
        else:
            ipilimumab_start_index = None
        if chemo_start_index and ipilimumab_start_index:
            if chemo_start_index > ipilimumab_start_index:
                suspect_prods, suspect_prod_name_list = finding_ipilimumab(data[0], suspect_prods, suspect_prod_name_list, pvi_json)
                suspect_prods, suspect_prod_name_list = finding_chemo(data[0], suspect_prods, suspect_prod_name_list, pvi_json)
            else:
                suspect_prods, suspect_prod_name_list = finding_chemo(data[0], suspect_prods, suspect_prod_name_list, pvi_json)
                suspect_prods, suspect_prod_name_list = finding_ipilimumab(data[0], suspect_prods, suspect_prod_name_list, pvi_json)
        else:
            suspect_prods, suspect_prod_name_list = finding_chemo(data[0], suspect_prods, suspect_prod_name_list, pvi_json)
            suspect_prods, suspect_prod_name_list = finding_ipilimumab(data[0], suspect_prods, suspect_prod_name_list, pvi_json)
        suspect_prods, suspect_prod_name_list = process_to_find_all_sus_prods(data[0], suspect_prods, suspect_prod_name_list, pvi_json)
        if len(suspect_prods) > 0:
            pvi_json = merge_concom_and_sus_prod(pvi_json, suspect_prods)
    return pvi_json


def finding_chemo(data, suspect_prods, suspect_prod_name_list, pvi_json):
    if 'Did the subject receive chemotherapy?' in data:
        data_list_chemotherapy = data.split('Did the subject receive chemotherapy?')
        for every_data in data_list_chemotherapy:
            if 'Chemotherapy Administration Study Visit' in every_data and every_data.strip().startswith('Yes'):
                suspect_prods, suspect_prod_name_list = process_chemotherapy_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data)
    return suspect_prods, suspect_prod_name_list


def finding_ipilimumab(data, suspect_prods, suspect_prod_name_list, pvi_json):
    if 'Did the subject receive Ipilimumab?' in data:
        data_list_ipilimumab = data.split('Did the subject receive Ipilimumab?')
        for every_data in data_list_ipilimumab:
            if every_data.strip().startswith('Yes'):
                suspect_prods, suspect_prod_name_list = process_ipilimumab_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data)
    return suspect_prods, suspect_prod_name_list


def process_to_find_all_sus_prods(data, suspect_prods, suspect_prod_name_list, pvi_json):
    if 'Did the subject receive Cemiplimab' in data:
        data_list_cemiplimab = data.split('Did the subject receive Cemiplimab')
        for every_data in data_list_cemiplimab:
            if every_data.strip().startswith('Yes'):
                suspect_prods, suspect_prod_name_list = process_cemiplimab_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data)
    if 'Did the subject receive blinded study drug' in data:
        data_list_blinded_study = data.split('Did the subject receive blinded study drug')
        for every_data in data_list_blinded_study:
            if every_data.strip().startswith('Yes'):
                suspect_prods, suspect_prod_name_list = process_blinded_study_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data)
    if 'Did the subject receive REG2810' in data:
        data_list_reg_2810 = data.split('Did the subject receive REG2810')
        for every_data in data_list_reg_2810:
            if every_data.strip().startswith('Yes'):
                suspect_prods, suspect_prod_name_list = process_reg_2810_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data)
    return suspect_prods, suspect_prod_name_list


# Function to process suspect product in pvi_json after extraction
def process_chemotherapy_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data):
    sus_product = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    if len(every_data.split('Chemotherapy type')) > 1:
        sus_product['license_value'] = every_data.split('Chemotherapy type')[1].split('Date of Administration')[0].strip()
    if sus_product['license_value'] not in suspect_prod_name_list:
        sus_product['role_value'] = 'suspect'
        suspect_prod_name_list.append(sus_product['license_value'])
        sus_product['doseInformations'][0]['startDate'] = every_data.split('Date of Administration (dd-mon-yyyy)')[1].split('Start Time')[0].strip()
        sus_product['doseInformations'][0]['startDate'] = process_date(sus_product['doseInformations'][0]['startDate'])
        sus_product['doseInformations'][0]['dose_inputValue'] = every_data.split('Planned dose to be administered')[1].strip()
        if sus_product['doseInformations'][0]['dose_inputValue'] not in [None, '', 'Other', 'other', 'OTHER']:
            sus_product['doseInformations'][0]['description'] = 'Dose: ' + sus_product['doseInformations'][0]['dose_inputValue']
        else:
            other_dose = every_data.split('Planned dose to be administered, if other')[1].split('Planned Dose Unit')[0].strip()
            other_dose_unit = every_data.split('Planned Dose Unit')[1].split('Was the Actual Dose modified?')[0].strip()
            if other_dose not in [None, '']:
                sus_product['doseInformations'][0]['dose_inputValue'] = other_dose + ' ' + other_dose_unit
                sus_product['doseInformations'][0]['description'] = 'Dose: ' + other_dose + ' ' + other_dose_unit
        suspect_prods.append(sus_product)
    return suspect_prods, suspect_prod_name_list


def process_cemiplimab_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data):
    sus_product = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    sus_product['license_value'] = 'Cemiplimab'
    if sus_product['license_value'] not in suspect_prod_name_list:
        sus_product['role_value'] = 'suspect'
        suspect_prod_name_list.append(sus_product['license_value'])
        sus_product['doseInformations'][0]['startDate'] = every_data.split('Date of Administration (dd-mon-yyyy)')[1].split('Start Time')[0].strip()
        sus_product['doseInformations'][0]['startDate'] = process_date(sus_product['doseInformations'][0]['startDate'])
        sus_product['doseInformations'][0]['dose_inputValue'] = every_data.split('Planned R2810 Dose Level')[1].split('Actual Dose')[0].strip()
        if sus_product['doseInformations'][0]['dose_inputValue'] not in [None, '']:
            sus_product['doseInformations'][0]['description'] = 'Dose: ' + sus_product['doseInformations'][0]['dose_inputValue']
        suspect_prods.insert(0, sus_product)
    return suspect_prods, suspect_prod_name_list


def process_blinded_study_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data):
    sus_product = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    sus_product['license_value'] = 'Cemiplimab Investigational Drug 134016 US'
    if sus_product['license_value'] not in suspect_prod_name_list:
        sus_product['role_value'] = 'suspect'
        suspect_prod_name_list.append(sus_product['license_value'])
        sus_product['doseInformations'][0]['startDate'] = every_data.split('Date of Administration (dd-mon-yyyy)')[1].split('Start Time')[0].strip()
        sus_product['doseInformations'][0]['startDate'] = process_date(sus_product['doseInformations'][0]['startDate'])
        sus_product['doseInformations'][0]['dose_inputValue'] = every_data.split('Planned blinded study drug Dose Level')[1].split('Actual Dose')[0].strip()
        if sus_product['doseInformations'][0]['dose_inputValue'] not in [None, '']:
            sus_product['doseInformations'][0]['description'] = 'Dose: ' + sus_product['doseInformations'][0]['dose_inputValue']
        suspect_prods.insert(0, sus_product)
    return suspect_prods, suspect_prod_name_list


def process_reg_2810_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data):
    sus_product = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    sus_product['license_value'] = 'Cemiplimab'
    if sus_product['license_value'] not in suspect_prod_name_list:
        sus_product['role_value'] = 'suspect'
        suspect_prod_name_list.append(sus_product['license_value'])
        sus_product['doseInformations'][0]['startDate'] = every_data.split('Date of Administration (dd-mon-yyyy)')[1].split('Start Time')[0].strip()
        sus_product['doseInformations'][0]['startDate'] = process_date(sus_product['doseInformations'][0]['startDate'])
        sus_product['doseInformations'][0]['dose_inputValue'] = every_data.split('Planned R2810 Dose Level')[1].split('Actual Dose')[0].strip()
        if sus_product['doseInformations'][0]['dose_inputValue'] not in [None, '']:
            sus_product['doseInformations'][0]['description'] = 'Dose: ' + sus_product['doseInformations'][0]['dose_inputValue']
        suspect_prods.insert(0, sus_product)
    return suspect_prods, suspect_prod_name_list


def process_ipilimumab_data(suspect_prods, suspect_prod_name_list, pvi_json, every_data):
    sus_product = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    sus_product['license_value'] = 'Ipilimumab'
    if sus_product['license_value'] not in suspect_prod_name_list:
        sus_product['role_value'] = 'suspect'
        suspect_prod_name_list.append(sus_product['license_value'])
        sus_product['doseInformations'][0]['startDate'] = every_data.split('Date of Administration (dd-mon-yyyy)')[1].split('Start Time')[0].strip()
        sus_product['doseInformations'][0]['startDate'] = process_date(sus_product['doseInformations'][0]['startDate'])
        sus_product['doseInformations'][0]['dose_inputValue'] = every_data.split('Planned Ipilimumab Dose to be Administered')[1].split('Actual Ipilimumab Dose')[0].strip()
        if sus_product['doseInformations'][0]['dose_inputValue'] not in [None, '']:
            sus_product['doseInformations'][0]['description'] = 'Dose: ' + sus_product['doseInformations'][0]['dose_inputValue']
        suspect_prods.append(sus_product)
    return suspect_prods, suspect_prod_name_list


# Function to merge concomitant and suspect products
def merge_concom_and_sus_prod(pvi_json, suspect_prods):
    sample_prod = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
    if len(pvi_json['products']) == 1:
        if pvi_json['products'][0]['license_value'] in [None, '']:
            pvi_json['products'] = suspect_prods
        else:
            for prod in pvi_json['products']:
                suspect_prods.append(prod)
            pvi_json['products'] = suspect_prods
    else:
        for prod in pvi_json['products']:
            suspect_prods.append(prod)
        pvi_json['products'] = suspect_prods
    if len(pvi_json['products']) == 0:
        pvi_json['products'] = [sample_prod]
    return pvi_json


# Function to process concomitant surgeries and procedure based on date
def process_concom_surgery_procedure(pvi_json):
    test_block = change_reference_values_to_none(copy.deepcopy(pvi_json['tests'][0]))
    con_surgery = [test for test in pvi_json['tests'] if test['seq_num']]
    pvi_json['tests'] = []
    ae_onset_date = pvi_json['events'][0]['startDate']
    for every in con_surgery:
        every['startDate'] = process_date(every['startDate'])
        if every['testNotes']:
            if every['testNotes'].lower() == 'diagnostic' or every['testNotes'] == '':
                every = process_test_data(every)
                pvi_json['tests'].append(every)
            else:
                result = check_med_test_dates(ae_onset_date, every['startDate'])
                if result:
                    med_his_block = change_reference_values_to_none(copy.deepcopy(pvi_json['patient']['medicalHistories'][0]))
                    med_his_block = process_med_his_concom_surgery_data(every, med_his_block)
                    pvi_json['patient']['medicalHistories'].append(med_his_block)
                else:
                    every = process_test_data(every)
                    pvi_json['tests'].append(every)
    if len(pvi_json['tests']) == 0:
        pvi_json['tests'] = [test_block]
    return pvi_json


# Function to compare date to determine which section to populate between med history and test
def check_med_test_dates(ae_date, start_date):
    result = True
    if len(ae_date.split('-')) == 3:
        ae_datetime = date(int(ae_date.split('-')[2]), months.index(ae_date.split('-')[1])+1, int(ae_date.split('-')[0]))
        if start_date not in [None, '']:
            if len(start_date.split('-')) == 3:
                start_datetime = date(int(start_date.split('-')[2]), months.index(start_date.split('-')[1]) + 1, int(start_date.split('-')[0]))
                if ae_datetime > start_datetime:
                    result = True
                else:
                    result = False
            elif len(start_date.split('-')) == 2:
                if ae_datetime.year == int(start_date.split('-')[-1]):
                    if ae_datetime.month > int(months.index(start_date.split()[0])+1):
                        result = True
                    else:
                        result = False
                elif ae_datetime.year > int(start_date.split('-')[-1]):
                    result = True
                else:
                    result = False
            elif len(start_date.split('-')) == 1:
                if ae_datetime.year > int(start_date.split('-')[0]):
                    result = True
                else:
                    result = False
    else:
        result = False
    return result


# Function to process test section data
def process_test_data(every):
    if every['seq_num']:
        every['seq_num'] = int(every['seq_num'])
    every['testName'] = every['testName'].replace('\n', ' ').strip()
    every['testNotes'] = every['testAssessment'] = None
    every['startDate'] = process_date(every['startDate'])
    return every


# Function to process med history section from concom surgery data
def process_med_his_concom_surgery_data(every, med_his_block):
    every['testNotes'] = every['testAssessment'] = None
    med_his_block['reportedReaction'] = every['testName'].replace('\n', ' ')
    med_his_block['startDate'] = process_date(every['startDate'])
    return med_his_block


# Function to process Medical histories of patient
def process_medical_history(pvi_json):
    med_his = change_reference_values_to_none(copy.deepcopy(pvi_json['patient']['medicalHistories'][0]))
    med_histories = [med for med in pvi_json['patient']['medicalHistories'] if med['historyConditionType'] not in [None, '']]
    if len(med_histories) > 0:
        for med in med_histories:
            med['historyConditionType'] = None
            med['reportedReaction'] = med['reportedReaction'].replace('\n', ' ').strip()
            med['startDate'] = process_date(med['startDate'])
            med['reactionCoded'] = None
            if med['historyNote']:
                med['historyNote'] = med['historyNote'].replace('\n', ' ').strip()
            med['endDate'] = process_date(med['endDate'])
            med['familyHistory'] = None
        pvi_json['patient']['medicalHistories'] = med_histories
    else:
        pvi_json['patient']['medicalHistories'] = [med_his]
    return pvi_json


def process_prst_section_data(pvi_json, extracted_json):
    prst_dict = get_prst_dict(extracted_json, '10049')
    if prst_dict != {}:
        med_his = change_reference_values_to_none(copy.deepcopy(pvi_json['patient']['medicalHistories'][0]))
        if prst_dict['Therapy setting'] not in [None, '']:
            med_his['reportedReaction'] = prst_dict['Therapy setting']
            if med_his['reportedReaction'].lower() == 'other':
                med_his['reportedReaction'] = prst_dict['Therapy_other']
            if prst_dict['Line of therapy'] not in [None, '']:
                if prst_dict['Line of therapy'].lower() == 'other':
                    med_his['historyNote'] = 'Line of therapy: ' + prst_dict['Line_other']
                else:
                    med_his['historyNote'] = 'Line of therapy: ' + prst_dict['Line of therapy']
            if prst_dict['Start date (dd-mon-yyyy)'] not in [None, '']:
                med_his['startDate'] = process_date(prst_dict['Start date (dd-mon-yyyy)'])
            if prst_dict['Stop date (dd-mon-yyyy)'] not in [None, '']:
                med_his['endDate'] = process_date(prst_dict['Stop date (dd-mon-yyyy)'])
            if prst_dict['Subject’s Best Response'] not in [None, '']:
                if med_his['historyNote']:
                    med_his['historyNote'] = med_his['historyNote'] + '\nSubject Best Response: ' + prst_dict['Subject’s Best Response']
                else:
                    med_his['historyNote'] = 'Subject Best Response: ' + prst_dict['Subject’s Best Response']
            pvi_json['patient']['medicalHistories'].append(med_his)
    return pvi_json


def get_prst_dict(extracted_json, annot):
    try:
        data = [x['value'] for x in extracted_json if x['AnnotID'] == annot][0]
        prst_dict = {}
        new_other = ['Therapy_other', 'Line_other']
        temp = 0
        if data:
            for each in data:
                if len(each) == 2:
                    if each[0] == 'If Other, specify' and temp < 2:
                        prst_dict[new_other[temp]] = each[1]
                        temp += 1
                    else:
                        prst_dict[each[0]] = each[1]
                else:
                    if None in each:
                        each.remove(None)
                    if len(each) >= 2:
                        if each[0] == 'If Other, specify' and temp < 2:
                            prst_dict[new_other[temp]] = each[1]
                            temp += 1
                        else:
                            prst_dict[each[0]] = each[1]
    except:
        prst_dict = {}
    return prst_dict


# Function to process AE section called from main function
def process_ae_section(pvi_json, extracted_json):
    ae_dict = get_ae_dict(extracted_json, '10045')
    if ae_dict != {}:
        pvi_json['events'][0]['reportedReaction'] = ae_dict['Main Adverse Event Description (Term)'].replace('\n', ' ')
        pvi_json['events'][0]['startDate'] = process_date(ae_dict['Start date (dd-mon-yyyy)'])
        if ae_dict['Outcome of AE'].lower() == 'not recovered/not resolved':
            ae_dict['Outcome of AE'] = 'Not Recovered'
        if ae_dict['Outcome of AE'].lower() == 'recovering/resolving':
            ae_dict['Outcome of AE'] = 'Recovering'
        if ae_dict['Outcome of AE'].lower() == 'recovered/resolved with sequelae':
            ae_dict['Outcome of AE'] = 'Recovered with Sequelae'
        pvi_json['events'][0]['outcome'] = ae_dict['Outcome of AE']
        pvi_json['events'][0]['endDate'] = process_date(ae_dict['Resolution date (dd-mon-yyyy)'])
        pvi_json['events'][0]['seq_num'] = 1
        pvi_json['events'][0]['eventCategory'][0]['value'] = ae_dict['AE most extreme severity CTCAE grade']
        es_list = process_event_seriousness(ae_dict)
        pvi_json = process_es_data(es_list, pvi_json)
    return pvi_json


# Function to process Event Seriousnesses called from function to process AE section
def process_es_data(es_list, pvi_json):
    if len(es_list) > 0:
        es_block = change_reference_values_to_none(copy.deepcopy(pvi_json['events'][0]['seriousnesses'][0]))
        pvi_json['events'][0]['seriousnesses'] = []
        for each in es_list:
            es_block['value'] = each
            pvi_json['events'][0]['seriousnesses'].append(es_block)
    return pvi_json


# Function to filter out event seriousness on basis of checked called from process AE section
def process_event_seriousness(ae_dict):
    es_list = []
    if ae_dict['It resulted in death'].lower() == 'checked':
        es_list.append('Death')
    if ae_dict['It was life-threatening'].lower() == 'checked':
        es_list.append('Life Threatening')
    if ae_dict['It required or prolonged inpatient\nhospitalization'].lower() == 'checked':
        es_list.append('Hospitalization')
    if ae_dict['It is a congenital anomaly/birth defect in\noffspring of study subject'].lower() == 'checked':
        es_list.append('Congenital Anomaly')
    if ae_dict['Persistent or significant disability /\nincapacity'].lower() == 'checked':
        es_list.append('Disability')
    if ae_dict['Other medically serious important event\n(It does not meet any of the above\nserious criteria, but may jeopardize the\nsubject, and may require medical or\nsurgical intervention to prevent one of\nthe outcomes listed above).'].lower() == 'checked':
        es_list.append('Other Medically Important Condition')
    if ae_dict['Other medically serious important event\n(It does not meet any of the above\nserious criteria, but may jeopardize the\nsubject, and may require medical or\nsurgical intervention to prevent one of\nthe outcomes listed above).'].lower() == 'other':
        es_list.append('Other Medically Important Condition')
    return es_list


# Function to populate action taken called from main function
def populate_action_taken(pvi_json, extracted_json):
    ae_dict = get_ae_dict(extracted_json, '10045')
    if ae_dict != {}:
        if 'Action taken with REGN2810' in ae_dict.keys():
            pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with REGN2810'], 'cemiplimab')
        if 'Action taken with blinded study drug' in ae_dict.keys():
            pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with blinded study drug'], 'cemiplimab investigational drug 134016 us')
        if 'Action taken with Cemiplimab' in ae_dict.keys():
            pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with blinded study drug'], 'cemiplimab')
        pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with Carboplatin'], 'carboplatin')
        pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with Paclitaxel'], 'paclitaxel')
        pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with Pemetrexed'], 'pemetrexed')
        pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with Cisplatin'], 'cisplatin')
        if 'Action taken with Ipilimumab' in ae_dict.keys():
            pvi_json = populate_action_taken_data(pvi_json, ae_dict['Action taken with Ipilimumab'], 'ipilimumab')
    return pvi_json


# Function to populate action taken data called from above function
def populate_action_taken_data(pvi_json, action_taken, ref_string):
    for prod in pvi_json['products']:
        if prod['license_value'].lower() == ref_string:
            if action_taken not in [None, '', 'NOT APPLICABLE', 'NOT CHECKED', 'Not Applicable']:
                if action_taken.lower() == 'dosage maintained':
                    action_taken = 'Dose Not Changed'
                if action_taken.lower() in ['drug discontinued (temp)', 'dose delayed', 'dose interrupted', 'drug interrupted']:
                    action_taken = 'Dose Temporarily withdrawn'
                if action_taken.lower() == 'study treatment withdrawn':
                    action_taken = 'Drug Withdrawn'
                prod['actionTaken']['value'] = action_taken
            break
    return pvi_json


# Function to populate pe matrix called from main function
def populate_pe_matrix(pvi_json, extracted_json):
    pe_mat_block = change_reference_values_to_none(copy.deepcopy(pvi_json['productEventMatrix'][0]))
    ae_dict = get_ae_dict(extracted_json, '10045')
    if ae_dict != {}:
        pe_matrix = []
        if 'AE suspected to be caused by\nREGN2810?' in ae_dict.keys():
            pe_matrix = process_pe_data(pe_matrix, pvi_json, ae_dict['AE suspected to be caused by\nREGN2810?'], 'cemiplimab')
        if 'AE suspected to be caused by blinded\nstudy drug?' in ae_dict.keys():
            pe_matrix = process_pe_data(pe_matrix, pvi_json, ae_dict['AE suspected to be caused by blinded\nstudy drug?'], 'cemiplimab investigational drug 134016 us')
        if 'AE suspected to be caused by\nCemiplimab' in ae_dict.keys():
            pe_matrix = process_pe_data(pe_matrix, pvi_json, ae_dict['AE suspected to be caused by\nCemiplimab'], 'cemiplimab')
        pe_matrix = process_pe_data(pe_matrix, pvi_json, ae_dict['Carboplatin'], 'carboplatin')
        pe_matrix = process_pe_data(pe_matrix, pvi_json, ae_dict['Paclitaxel'], 'paclitaxel')
        pe_matrix = process_pe_data(pe_matrix, pvi_json, ae_dict['Pemetrexed'], 'pemetrexed')
        pe_matrix = process_pe_data(pe_matrix, pvi_json, ae_dict['Cisplatin'], 'cisplatin')
        pvi_json = process_other_causality(pvi_json, ae_dict, extracted_json)
        if len(pe_matrix) == 0:
            pvi_json['productEventMatrix'] = [pe_mat_block]
        else:
            pvi_json['productEventMatrix'] = pe_matrix
    return pvi_json


# Function to process other causality called from populate pe matrix function
def process_other_causality(pvi_json, ae_dict, extracted_json):
    if 'Other Causality' and 'If Other Causality, Specify' in ae_dict.keys():
        if ae_dict['Other Causality'].lower() == 'checked':
            if pvi_json['summary']['caseDescription']:
                pvi_json['summary']['caseDescription'] = pvi_json['summary']['caseDescription'].strip() + '\nOther Causality: ' + ae_dict['If Other Causality, Specify'].strip()
            else:
                pvi_json['summary']['caseDescription'] = 'Other Causality: ' + ae_dict['If Other Causality, Specify'].strip()
    else:
        try:
            data = [x['value'] for x in extracted_json if x['AnnotID'] == '10048'][0]
            causality = data[0].replace('Other', '').replace('If', '').replace('specify', '').replace(',', '').replace('\n', '').strip()
            if causality.startswith('CHECKED'):
                causality = causality.replace('CHECKED', '').strip()
                if pvi_json['summary']['caseDescription']:
                    pvi_json['summary']['caseDescription'] = pvi_json['summary']['caseDescription'].strip() + '\nOther Causality: ' + causality
                else:
                    pvi_json['summary']['caseDescription'] = 'Other Causality: ' + causality
        except:
            pass
    return pvi_json


# Function to populate pe data called from populate pe matrix function
def process_pe_data(pe_matrix, pvi_json, check_string, ref_string):
    pe_mat_block = change_reference_values_to_none(copy.deepcopy(pvi_json['productEventMatrix'][0]))
    check_dict = {'Yes': 'Related', 'No': 'Not Related', 'Unknown': 'Unknown', '': 'Not Reported', 'NOT CHECKED': '', 'CHECKED': ''}
    for prod in pvi_json['products']:
        if prod['role_value'].lower() == 'suspect' and prod['license_value'].lower() == ref_string:
            if check_dict[check_string] in ['Related', 'Not Related', 'Unknown', 'Not Reported']:
                for event in pvi_json['events']:
                    pe_mat_block['product_seq_num'] = prod['seq_num']
                    pe_mat_block['event_seq_num'] = event['seq_num']
                    pe_mat_block['relatednessAssessments'][0]['result']['value'] = check_dict[check_string]
                    pe_matrix.append(pe_mat_block)
            break
    return pe_matrix


# Function to process Patient ID called from Main function
def process_patient_id_sender_case_uid(pvi_json):
    if pvi_json['patient']['patientId'] not in [None, ''] and len(pvi_json['patient']['patientId']) > 4:
        pvi_json['patient']['patientId'] = pvi_json['patient']['patientId'][0:-3] + "-" + pvi_json['patient']['patientId'][-3:]
    pvi_json['senderCaseUid'] = pvi_json['patient']['patientId']
    return pvi_json


# Function to process secondary event section
def process_second_ae_section(pvi_json, extracted_json):
    ae_dict = get_ae_dict(extracted_json, '10046')
    if ae_dict != {}:
        pvi_json = process_second_event_data(pvi_json, ae_dict)
    return pvi_json


# Function to get AE dict from extracted json
def get_ae_dict(extracted_json, annot):
    try:
        data = [x['value'] for x in extracted_json if x['AnnotID'] == annot][0]
        ae_dict = {}
        if data:
            for each in data:
                if len(each) == 2:
                    ae_dict[each[0]] = each[1]
                else:
                    if None in each:
                        each.remove(None)
                    if len(each) >= 2:
                        ae_dict[each[0]] = each[1]
    except:
        ae_dict = {}
    return ae_dict


# Function to populate secondary event data
def process_second_event_data(pvi_json, ae_dict):
    if pvi_json['events'][0]['reportedReaction'] not in [None, '']:
        if ae_dict['Adverse Event Description\n(Term)'].strip().replace('\n', ' ') != pvi_json['events'][0]['reportedReaction']:
            eve_block = change_reference_values_to_none(copy.deepcopy(pvi_json['events'][0]))
            eve_block['reportedReaction'] = ae_dict['Adverse Event Description\n(Term)']
            eve_block['startDate'] = process_date(ae_dict['Start Date (dd-mon-yyyy)'])
            eve_block['seq_num'] = 2
            pvi_json['events'].append(eve_block)
    else:
        pvi_json['events'][0]['reportedReaction'] = ae_dict['Adverse Event Description\n(Term)'].replace('\n', ' ')
        pvi_json['events'][0]['startDate'] = process_date(ae_dict['Start Date (dd-mon-yyyy)'])
        pvi_json['events'][0]['seq_num'] = 1
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


def process_route_intravenous_and_convert_mg_to_milligram(pvi_json):
    for prod in pvi_json['products']:
        if prod['role_value'].lower() == 'suspect':
            for dose in prod['doseInformations']:
                dose['route_value'] = 'Intravenous'
                if dose['dose_inputValue']:
                    dose['dose_inputValue'] = convert_units(dose['dose_inputValue'])
                    dose['description'] = convert_units(dose['description'])
                    if ' IV' in dose['dose_inputValue']:
                        dose['dose_inputValue'] = dose['dose_inputValue'].replace(' IV', '')
                        dose['description'] = dose['description'].replace(' IV', '')
                    result = check_code_list_matching_values_for_dose(dose['dose_inputValue'].lower())
                    if result:
                        dose['description'] = None
                    else:
                        dose['dose_inputValue'] = None
    return pvi_json


def populate_suspect_product_from_action_taken(pvi_json, extracted_json):
    suspect = False
    for prod in pvi_json['products']:
        if prod['role_value'].lower() == 'suspect':
            suspect = True
            break
    if not suspect:
        ae_dict = get_ae_dict(extracted_json, '10045')
        sus_prod = change_reference_values_to_none(copy.deepcopy(pvi_json['products'][0]))
        if 'Action taken with Cemiplimab' in ae_dict.keys():
            if ae_dict['Action taken with Cemiplimab'] not in [None, '', 'NOT APPLICABLE', 'NOT CHECKED', 'Not Applicable']:
                sus_prod['license_value'] = 'Cemiplimab'
                sus_prod['role_value'] = 'suspect'
                suspect = True
        if 'Action taken with REGN2810' in ae_dict.keys():
            if ae_dict['Action taken with REGN2810'] not in [None, '', 'NOT APPLICABLE', 'NOT CHECKED', 'Not Applicable']:
                sus_prod['license_value'] = 'Cemiplimab'
                sus_prod['role_value'] = 'suspect'
                suspect = True
        if 'Action taken with blinded study drug' in ae_dict.keys():
            if ae_dict['Action taken with blinded study drug'] not in [None, '', 'NOT APPLICABLE', 'NOT CHECKED', 'Not Applicable']:
                sus_prod['license_value'] = 'Cemiplimab Investigational Drug 134016 US'
                sus_prod['role_value'] = 'suspect'
                suspect = True
        if not suspect:
            sus_prod['license_value'] = 'Cemiplimab'
            sus_prod['role_value'] = 'suspect'
        pvi_json['products'].insert(0, sus_prod)
    seq_num = 1
    for prod in pvi_json['products']:
        prod['seq_num'] = seq_num
        seq_num += 1
        if prod['role_value'].lower() == 'suspect':
            prod['indications'][0]['reportedReaction'] = 'Non-small cell Lung Cancer'
    return pvi_json


def create_pe_matrix_for_all_products(pvi_json):
    event_len = len(pvi_json['events'])
    sus_prod_len = len([prod for prod in pvi_json['products'] if prod['role_value'].lower() == 'suspect'])
    sus_prod_index_already_exist = []
    insert_index = 0
    for index in range(len(pvi_json['productEventMatrix'])):
        if pvi_json['productEventMatrix'][index]['product_seq_num'] not in sus_prod_index_already_exist:
            sus_prod_index_already_exist.append(pvi_json['productEventMatrix'][index]['product_seq_num'])
    for index in range(sus_prod_len):
        if index+1 not in sus_prod_index_already_exist:
            for event in pvi_json['events']:
                pe_mat = change_reference_values_to_none(copy.deepcopy(pvi_json['productEventMatrix'][0]))
                pe_mat['product_seq_num'] = index+1
                pe_mat['event_seq_num'] = event['seq_num']
                pvi_json['productEventMatrix'].insert(insert_index, pe_mat)
                insert_index += 1
        else:
            insert_index = insert_index + event_len
    return pvi_json


def process_drug_name_prst(pvi_json, extracted_json):
    try:
        data = [x['value'] for x in extracted_json if x['AnnotID'] == '10050'][0]
    except:
        data = []
    final_past_his = []
    if data:
        drug_data = data[0]
        drug_names = None
        if 'R2810-ONC-16113' in drug_data:
            drug_names = drug_data.split('Position')[-1].split('R2810-ONC')[0].strip()
        elif 'Regeneron Pharmaceuticals' in drug_data:
            drug_names = drug_data.split('Position')[-1].split('Regeneron Pharmaceuticals')[0].strip()
        if drug_names not in [None, '']:
            drug_names = re.split('(\d+)', drug_names)
            final_drug_name = []
            for every in drug_names:
                if every not in [None, '']:
                    if not every.isdigit():
                        final_drug_name.append(every.strip())
            drug_processed = []
            for every in final_drug_name:
                if every not in drug_processed:
                    past_his = change_reference_values_to_none(copy.deepcopy(pvi_json['patient']['pastDrugHistories'][0]))
                    past_his['drugReaction'][0]['reportedReaction'] = every.replace('\n', ' ')
                    final_past_his.append(past_his)
                drug_processed.append(every)
    if final_past_his:
        pvi_json['patient']['pastDrugHistories'] = final_past_his
    return pvi_json


def process_country_code(pvi_json):
    country_code_list_file_location = '/home/ubuntu/backendservice/utility/template/customizations/ISO_Codes.csv'
    country_code_df = pd.read_csv(country_code_list_file_location)
    country_code_df['Code'] = country_code_df['Code'].astype(str).str.zfill(3)
    code = pvi_json['literatures'][0]['author'].replace('Site ', '')[0:3]
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


def date_format_update(given_date):

    if given_date.lower() not in ["unk", "un","unknown"]:
        dd_mmm_yyyy = re.compile(r"^\d{2}-[A-Z]{3}-\d{4}$")                      # 26-MAY-2022
        d_mmm_yyyy = re.compile(r"^\d{1}-[A-Z]{3}-\d{4}$")                       # 4-MAY-2022
        mmm_yyyy = re.compile(r"^[A-Z]{3}-\d{4}$")                              # MAY-2022
        yyyy = re.compile(r"^\d{4}$")                                           # 2021

        dd_mmm_yyyy_ptn = re.findall(dd_mmm_yyyy, given_date)
        d_mmm_yyyy_ptn = re.findall(d_mmm_yyyy, given_date)
        mmm_yyyy_ptn = re.findall(mmm_yyyy, given_date)
        yyyy_ptn = re.findall(yyyy, given_date)
        if len(dd_mmm_yyyy_ptn) > 0:
            try:
                given_date = dd_mmm_yyyy_ptn[0]
                date_obj = datetime.strptime(given_date, "%d-%b-%Y")
            except:
                given_date = None

        elif len(d_mmm_yyyy_ptn) > 0:
            try:
                given_date = "0" + d_mmm_yyyy_ptn[0]
                date_obj = datetime.strptime(given_date, "%d-%b-%Y")
            except:
                given_date = None


        elif len(mmm_yyyy_ptn) > 0:
            try:
                given_date = mmm_yyyy_ptn[0]
                date_obj = datetime.strptime(given_date, "%b-%Y")
            except:
                given_date = None
        elif len(yyyy_ptn) > 0:
            try:
                given_date = yyyy_ptn[0]
                date_obj = datetime.strptime(given_date, "%Y")
            except:
                given_date = None

    return given_date



def validate_date(pvi_json):
    if pvi_json["affiliate_date"]:
        pvi_json["affiliate_date"] = date_format_update(pvi_json["affiliate_date"])
    if pvi_json["deathDetail"]["deathDate"]["date"]:
        pvi_json["deathDetail"]["deathDate"]["date"] = date_format_update(pvi_json["deathDetail"]["deathDate"]["date"])
    for idx in range(len(pvi_json["events"])):
        if pvi_json["events"][idx]["startDate"]:
            pvi_json["events"][idx]["startDate"] = date_format_update(pvi_json["events"][idx]["startDate"])
        if pvi_json["events"][idx]["endDate"]:
            pvi_json["events"][idx]["endDate"] = date_format_update(pvi_json["events"][idx]["endDate"])
    if pvi_json["mostRecentReceiptDate"]:
        pvi_json["mostRecentReceiptDate"] = date_format_update(pvi_json["mostRecentReceiptDate"])
    for idx in range(len(pvi_json["patient"]["medicalHistories"])):
        if pvi_json["patient"]["medicalHistories"][idx]["endDate"]:
            pvi_json["patient"]["medicalHistories"][idx]["endDate"] = date_format_update(pvi_json["patient"]["medicalHistories"][idx]["endDate"])
        if pvi_json["patient"]["medicalHistories"][idx]["startDate"]:
            pvi_json["patient"]["medicalHistories"][idx]["startDate"] = date_format_update(pvi_json["patient"]["medicalHistories"][idx]["startDate"])
    for idx in range(len(pvi_json["patient"]["pastDrugHistories"])):
        if pvi_json["patient"]["pastDrugHistories"][idx]["endDate"]:
            pvi_json["patient"]["pastDrugHistories"][idx]["endDate"] = date_format_update(pvi_json["patient"]["pastDrugHistories"][idx]["endDate"])
        if pvi_json["patient"]["pastDrugHistories"][idx]["startDate"]:
            pvi_json["patient"]["pastDrugHistories"][idx]["startDate"] = date_format_update(pvi_json["patient"]["pastDrugHistories"][idx]["startDate"])
    for idx in range(len(pvi_json["products"])):
        for idx_dose in range(len(pvi_json["products"][idx]["doseInformations"])):
            if pvi_json["products"][idx]["doseInformations"][idx_dose]["endDate"]:
                pvi_json["products"][idx]["doseInformations"][idx_dose]["endDate"] = date_format_update(pvi_json["products"][idx]["doseInformations"][idx_dose]["endDate"])
            if pvi_json["products"][idx]["doseInformations"][idx_dose]["startDate"]:
                pvi_json["products"][idx]["doseInformations"][idx_dose]["startDate"] = date_format_update(pvi_json["products"][idx]["doseInformations"][idx_dose]["startDate"])
            if pvi_json["products"][idx]["doseInformations"][idx_dose]["customProperty_expiryDate"]:
                pvi_json["products"][idx]["doseInformations"][idx_dose]["customProperty_expiryDate"] = date_format_update(pvi_json["products"][idx]["doseInformations"][idx_dose]["customProperty_expiryDate"])
    if pvi_json["receiptDate"]:
        pvi_json["receiptDate"] = date_format_update(pvi_json["receiptDate"])
    for idx in range(len(pvi_json["tests"])):
        if pvi_json["tests"][idx]["startDate"]:
            pvi_json["tests"][idx]["startDate"] = date_format_update(pvi_json["tests"][idx]["startDate"])
    return pvi_json

# Main function to call all the other functions
def get_postprocessed_json(pvi_json, extracted_json):
    try:
        pvi_json = process_ae_section(pvi_json, extracted_json)
    except:
        print('Error in First AE processing')
    try:
        pvi_json = process_second_ae_section(pvi_json, extracted_json)
    except:
        print('Error in second ae processing')
    try:
        pvi_json = process_medical_history(pvi_json)
    except:
        print('Error in processing medical history')
    try:
        pvi_json = process_smoking_history(pvi_json)
    except:
        print('Error in processing smoking history')
    try:
        pvi_json = process_concomitant_products_filtering(pvi_json)
    except:
        print('Error in processing concomitants product filtering')
    try:
        pvi_json = process_concomitant_data(pvi_json)
    except:
        print('Error in processing concomitant data')
    try:
        pvi_json = process_suspect_product(pvi_json, extracted_json)
    except:
        print('Error in processing suspect products')
    try:
        pvi_json = process_concom_surgery_procedure(pvi_json)
    except:
        print('Error in processing concomitant surgery procedure')
    try:
        pvi_json = process_prst_section_data(pvi_json, extracted_json)
    except:
        print('Error in processing PRST section')
    pvi_json = process_patient_id_sender_case_uid(pvi_json)
    try:
        pvi_json = populate_suspect_product_from_action_taken(pvi_json, extracted_json)
    except:
        print('Error in populating suspect product from action taken')
    try:
        pvi_json = populate_pe_matrix(pvi_json, extracted_json)
    except:
        print('Error in processing PE Matrix')
        pvi_json['productEventMatrix'][0]['dechallenge']['value'] = None
        pvi_json['productEventMatrix'][0]['rechallenge']['value'] = None
    pvi_json = process_study_id(pvi_json)
    try:
        pvi_json = populate_action_taken(pvi_json, extracted_json)
    except:
        print('Error in processing Action Taken')
    try:
        pvi_json = create_pe_matrix_for_all_products(pvi_json)
    except:
        print('Error in creating PE matrix for all suspect products')
    try:
        pvi_json = process_route_intravenous_and_convert_mg_to_milligram(pvi_json)
    except:
        print('Error in processing gram and milligram conversion')
    try:
        pvi_json = process_drug_name_prst(pvi_json, extracted_json)
    except:
        print('Error in processing PRST drug name')
    try:
        pvi_json = process_country_code(pvi_json)
    except:
        print('Error in processing Country Code')
    try:
        pvi_json = validate_date(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json


