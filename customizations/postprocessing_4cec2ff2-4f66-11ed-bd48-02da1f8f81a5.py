import copy
import json
import traceback
from datetime import datetime
from date_format import transform_date
import re


def update_date_format(pvi_json):
    if pvi_json['receiptDate'] and pvi_json['receiptDate'].count(':') == 1:
        try:
            pvi_json['receiptDate'] = datetime.strptime(pvi_json['receiptDate'], '%d %b %Y %H:%M').strftime('%d-%b-%Y')
        except:
            pvi_json['receiptDate'] = None
    elif pvi_json['receiptDate'] and pvi_json['receiptDate'].count(':') == 2:
        try:
            pvi_json['receiptDate'] = datetime.strptime(pvi_json['receiptDate'], '%d %b %Y %H:%M:%S').strftime(
                '%d-%b-%Y')
        except:
            pvi_json['receiptDate'] = None
    elif pvi_json['receiptDate']:
        pvi_json['receiptDate'] = pvi_json['receiptDate'].strip().replace(' ', '-')

    if pvi_json['receiptDate_acc'] and pvi_json['receiptDate_acc'].count(':') == 1:
        try:
            pvi_json['receiptDate_acc'] = datetime.strptime(pvi_json['receiptDate_acc'], '%d %b %Y %H:%M').strftime(
                '%d-%b-%Y')
        except:
            pvi_json['receiptDate_acc'] = None
    elif pvi_json['receiptDate_acc'] and pvi_json['receiptDate_acc'].count(':') == 2:
        try:
            pvi_json['receiptDate_acc'] = datetime.strptime(pvi_json['receiptDate_acc'], '%d %b %Y %H:%M:%S').strftime(
                '%d-%b-%Y')
        except:
            pvi_json['receiptDate_acc'] = None
    elif pvi_json['receiptDate_acc']:
        pvi_json['receiptDate_acc'] = pvi_json['receiptDate_acc'].strip().replace(' ', '-')
    return pvi_json


def remove_null_products(pvi_json):
    prod_final = []
    medhis_final = []
    medhis_sample = copy.deepcopy(pvi_json['patient']['medicalHistories'][0])
    for prod in pvi_json['products']:
        if prod['license_value']:
            prod_final.append(prod)
    pvi_json['products'] = prod_final
    for medhis in pvi_json['patient']['medicalHistories']:
        if medhis['reportedReaction']:
            medhis_final.append(medhis)
    if not medhis_final:
        for keys in medhis_sample.keys():
            medhis_sample[keys] = None
        medhis_final.append(copy.deepcopy(medhis_sample))
    pvi_json['patient']['medicalHistories'] = medhis_final
    return pvi_json


def mapping_changes(pvi_json):
    pvi_json['summary']['caseDescription'], pvi_json['summary']['senderComments_acc'] = pvi_json['summary'][
        'senderComments_acc'], None
    pvi_json['summary']['adminNotes'], pvi_json['additionalNotes'] = None, pvi_json['summary']['adminNotes']
    pvi_json['patient']['age']['inputValue_acc'], pvi_json['patient']['patientDob'] = None, pvi_json['patient']['age'][
        'inputValue_acc']
    pvi_json['reporters'][0]['Intermediary'], pvi_json['reporters'][0]['additionalNotes'] = None, \
    pvi_json['reporters'][0]['Intermediary']
    for event in pvi_json['events']:
        event['hospitalizationStartDate_acc'], event['additionalNotes'] = None, event['hospitalizationStartDate_acc']
    pvi_json['senderCaseUid_acc'], pvi_json['references'][0]['referenceNotes'] = None, pvi_json['senderCaseUid_acc']
    return pvi_json


def parse_receipt_date(pvi_json):
    date = None
    date_acc = None
    if pvi_json['receiptDate']:
        try:
            date = datetime.strptime(pvi_json['receiptDate'], '%d-%b-%Y')
        except:
            pass
    if pvi_json['receiptDate_acc']:
        try:
            date_acc = datetime.strptime(pvi_json['receiptDate_acc'], '%d-%b-%Y')
        except:
            pass
    if date and date_acc:
        if date_acc < date:
            pvi_json['receiptDate_acc'], pvi_json['receiptDate'] = None, pvi_json['receiptDate_acc']
    return pvi_json


def parse_event_date(pvi_json):
    for event in pvi_json['events']:
        if event['startDate'] and '/' in event['startDate']:
            try:
                event['startDate'], event['endDate'] = event['startDate'].split('/')
            except:
                pass
        if event['startDate'] and not event['endDate']:
            dd_mmm_yyyy_hh_mm_ss = re.search(r"^\d{2}-[A-Za-z]{3}-\d{4} \d{2}:\d{2}:\d{2}$",
                                             event['startDate'])  # 13-JUN-2022 12:30:00
            dd_mmm_yyyy = re.search(r"^\d{2}-[A-Za-z]{3}-\d{4}$", event['startDate'])  # 13-JUN-2022
            d_mmm_yyyy = re.search(r"^\d{1}-[A-Za-z]{3}-\d{4}$", event['startDate'])  # 5-JUN-2022
            mmm_yyyy = re.search(r"^[A-Za-z]{3}-\d{4}$", event['startDate'])  # JUN-2022
            yyyy = re.search(r"^\d{4}$", event['startDate'])  # 2022

            date_formats = ["%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%d-%b-%Y", "%b-%Y", "%Y"]
            date_patterns = [dd_mmm_yyyy_hh_mm_ss, dd_mmm_yyyy, d_mmm_yyyy, mmm_yyyy, yyyy]
            # event['startDate'] = None
            for idx in range(len(date_patterns)):
                if date_patterns[idx]:
                    try:
                        event['startDate'] = date_patterns[idx].group()
                        if idx == 2:
                            event['startDate'] = '0' + event['startDate']  # application support zero-padded decimal
                        date_obj = datetime.strptime(event['startDate'], date_formats[idx])
                    except ValueError:
                        pass
                    break
            if not any(date_patterns):
                event['additionalNotes'] = 'AE onset/stopdate (EN): ' + event['startDate']
                event['startDate'] = None

    return pvi_json


def get_postprocessed_json(pvi_json, ws1_json):
    try:
        pvi_json = update_date_format(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = mapping_changes(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = remove_null_products(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = parse_receipt_date(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = parse_event_date(pvi_json)
    except:
        traceback.print_exc()

    return pvi_json
