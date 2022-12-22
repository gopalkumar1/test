import json
import re
import traceback
from nameparser import HumanName as hn
from datetime import datetime


def reporter_junk(pvi_json):
    for reporter in pvi_json['reporters']:
        if reporter['givenName']:
            name = hn(reporter['givenName'])
            reporter['firstName'] = name['first']
            reporter['lastName'] = name['last']
        reporter['givenName'] = None
        if reporter['organization']:
            reporter['organization'] = reporter['organization'].replace('Littlejohn', '')
    if pvi_json['patient']['height']:
        pvi_json['patient']['heightUnit'] = 'Cms'
    if pvi_json['patient']['weight']:
        pvi_json['patient']['weightUnit'] = 'Kgs'
    if pvi_json['patient']['age']['inputValue']:
        pvi_json['patient']['patientDob'] = pvi_json['patient']['age']['inputValue']
    if pvi_json['patient']['gender_acc']:
        pvi_json['patient']['ethnicGroup'] = pvi_json['patient']['gender_acc']
        pvi_json['patient']['gender_acc'] = None
    for prod in pvi_json['products']:
        for dose in prod['doseInformations']:
            if dose['dose_inputValue']:
                if ' ' not in dose['dose_inputValue']:
                    dose['description'] = 'Dose: ' + dose['dose_inputValue']
            if dose['startDate']:
                dose['startDate'] = dose['startDate'].replace(', ', '-').replace('00:00:00', '').replace('-22', '-2022')
            if dose['endDate']:
                dose['endDate'] = dose['endDate'].replace(', ', '-').replace('00:00:00', '')
    for event in pvi_json['events']:
        if event['endDate'] and '00:00:00' in event['endDate']:
            event['endDate'] = event['endDate'].replace('00:00:00', '')
        if event['startDate'] and '00:00:00' in event['startDate']:
            event['startDate'] = event['startDate'].replace('00:00:00', '')
        if event['hospitalizationEndDate']:
            endDate = re.findall(r'\d{2} [A-Z]{3} \d{4}', event['hospitalizationEndDate'])
            endDate = endDate[0].replace(' ', '-')
            event['hospitalizationEndDate'] = endDate
        if event['hospitalizationStartDate']:
            startDate = re.findall(r'\d{2} [A-Z]{3} \d{4}', event['hospitalizationStartDate'])
            startDate = startDate[0].replace(' ', '-')
            event['hospitalizationStartDate'] = startDate
    med_his = pvi_json['patient']['medicalHistories'][1:]
    pvi_json['patient']['medicalHistories'] = med_his
    for med in pvi_json['patient']['medicalHistories']:
        if med['startDate'] and '00:00:00' in med['startDate']:
            med['startDate'] = med['startDate'].replace('00:00:00', '')
    if pvi_json['receiptDate']:
        pvi_json['receiptDate'] = pvi_json['receiptDate'].replace('00:00:00', '')
    for prod in pvi_json['products'][1:]:
        prod['role_value'] = 'Concomitant'
        prod['doseInformations'][0]['startDate'] = None
    return pvi_json


def populate_codelist_value(pvi_json):
    seriousness = {'1': 'Death', '2': 'Life Threatening', '3': 'Hospitalization', '4': 'Congenital Anomaly',
                   '5': 'Disabling', '6': 'Medically Important'}
    related = {'1': 'Not related', '2': 'Possible', '3': 'Related'}
    action_taken = {'1': 'Dose not changed', '2': 'Drug withdrawn', 'Z': 'Drug withdrawn', '3': 'Dose reduced',
                    '4': 'Unknown', '5': 'Not applicable', '6': 'Unknown'}
    outcome = {'1': 'recovered/resolved', '2': 'recovered/resolved with sequelae', '3': 'recovering/resolving',
               '4': 'not recovered/not resolved/ongoing', '5': 'fatal', '6': 'Unknown'}
    severity = {'1': 'Mild', '2': 'Moderate', '3': 'Severe'}
    dechall = {'1': 'Positive', '2': 'Negative', '3': 'N/A'}
    rechall = {'1': 'Positive', '2': 'Negative', '3': 'N/A'}
    for event in pvi_json['events']:
        for ser in event['seriousnesses']:
            if ser['value'] in seriousness.keys():
                ser['value'] = seriousness[ser['value']]
        if event['outcome'] and event['outcome'] in outcome.keys():
            event['outcome'] = outcome[event['outcome']]

    for pe_matrix in pvi_json['productEventMatrix']:
        if pe_matrix['relatednessAssessments'][0]['result']['value'] and \
                pe_matrix['relatednessAssessments'][0]['result']['value'] in related.keys():
            pe_matrix['relatednessAssessments'][0]['result']['value'] = related[
                pe_matrix['relatednessAssessments'][0]['result']['value']]
        if pe_matrix['dechallenge']['value'] and pe_matrix['dechallenge']['value'] in dechall.keys():
            pe_matrix['dechallenge']['value'] = dechall[pe_matrix['dechallenge']['value']]
        if pe_matrix['rechallenge']['value'] and pe_matrix['rechallenge']['value'] in rechall.keys():
            pe_matrix['rechallenge']['value'] = rechall[pe_matrix['rechallenge']['value']]
        pe_matrix['relatednessAssessments'][0]['method']['value'] = 'Global Introspection'
        pe_matrix['relatednessAssessments'][0]['source']['value'] = 'Primary source reporter'

    for prod in pvi_json['products']:
        if prod['actionTaken']['value'] and prod['actionTaken']['value'] in action_taken.keys():
            prod['actionTaken']['value'] = action_taken[prod['actionTaken']['value']]
    return pvi_json


def get_postprocessed_json(pvi_json, extracted_json):
    try:
        pvi_json = reporter_junk(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_codelist_value(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json


# extracted_json = json.load(
#     open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/199_inter.json'))
# pvi_json = json.load(
#     open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/Final_SAGE.json'))
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_json)))
