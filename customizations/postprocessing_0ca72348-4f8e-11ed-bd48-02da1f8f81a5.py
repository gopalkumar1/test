import copy
import json
import traceback
import re
import requests
from functools import reduce


def strip_characters(inp_string):
    inp_string = re.sub(r'[^\x00-\x7F]+', '', inp_string)
    if inp_string:
        out_string = inp_string.replace("\n", "").strip(" { } ( ) \ / ; . [ ] , - : ")
        return out_string
    else:
        return inp_string


def check_list_length(check_list):
    Check = False
    if len(check_list) > 0:
        Check = True
    return Check


def populate_product_event(pvi_json, extracted_json):
    product_list = []
    event_list = []
    seriousness = []
    product_final = []
    event_final = []
    pvi_json['events'][0]['reportedReaction'] = None
    pvi_json['products'][0]['license_value'] = None
    pvi_json['events'][0]['seriousnesses'][0]['value'] = None
    product_sample = copy.deepcopy(pvi_json['products'][0])
    event_sample = copy.deepcopy(pvi_json['events'][0])
    for annot in extracted_json:
        if annot['AnnotID'] == '10004':
            data_list = annot['value']
        if annot['AnnotID'] == '10008':
            country = annot['value'][0]
            if country:
                country = country.replace('\t', ' ').strip()
    for data in data_list:
        if data_list.index(data) == 0:
            data = data.replace('\t', ' ')
            if '/' in data:
                product_list.append(data.split('/'))
            elif "\\" in data:
                product_list.append(data.split('\\'))
            else:
                product_list.append(data.split('<'))                            #Not present in data splitted for the inserting in 2d array only
        elif data_list.index(data) == 1:
            data = data.replace('\t', ' ')
            event_list.append(data.split(':')[0].replace(' and ', ',').split(','))
        elif data_list.index(data) == 2:
            seriousness.append(strip_characters(data))
    if seriousness and seriousness[0].lower() in ['serious', 'other']:
        seriousness[0] = 'Other Medically Important Condition'
    for product in product_list[0]:
        product_final.append(copy.deepcopy(product_sample))
        product_final[-1]['license_value'] = product
        product_final[-1]['seq_num'] = product_list[0].index(product) + 1

    for event in event_list[0]:
        event_final.append(copy.deepcopy(event_sample))
        event_final[-1]['reportedReaction'] = event
        event_final[-1]['seq_num'] = event_list[0].index(event) + 1
        event_final[-1]['country'] = country
    pvi_json['events'] = event_final
    pvi_json['products'] = product_final
    if seriousness:
        for event in pvi_json['events']:
            event['seriousnesses'][0]['value'] = seriousness[0]
    if pvi_json['receiptDate']:
        pvi_json['receiptDate'] = pvi_json['receiptDate'].strip()
        pvi_json['receiptDate'] = pvi_json['receiptDate'].replace(" ", "-")
    return pvi_json


def response_from_external_ws(url, request_type, pvi_json):
    obj = {'text': pvi_json["summary"]["senderComments"]}
    if request_type == "POST":
        response = requests.post(url, data=obj, timeout=400)
    elif request_type == "GET":
        response = requests.get(url, timeout=400)

    return response.json()


def populate_product_form_unstruct(pvi_json, unstruct_json):
    product_name_list = []
    ingredient_name_list = []
    for product in pvi_json['products']:
        if product['license_value']:
            product_name_list.append(product['license_value'].lower())
        if product['ingredients'] and product['ingredients'][0]['name']:
            ingredient_name_list.append(product['ingredients'][0]['name'].lower())
    # if len(pvi_json['products']) == 1:
        # if not pvi_json['products'][0]['license_value']:
    if check_list_length(unstruct_json['products']):
        for product_unst in unstruct_json['products']:
            if product_unst['license_value'].lower().replace(" ", "") not in product_name_list:        # and product['license_value'].lower() not in ingredient_name_list
                pvi_json['products'].append(product_unst)
    for product in pvi_json['products']:
        for product_unst in unstruct_json['products']:
            if product['license_value'].lower().replace(" ","") == product_unst['license_value'].lower().replace(" ",""):
                if not product['doseInformations'][0]['dose_inputValue'] and product_unst['doseInformations'][0]['dose_inputValue']:
                    product['doseInformations'][0]['dose_inputValue'] = product_unst['doseInformations'][0][
                        'dose_inputValue']
                if not product['doseInformations'][0]['startDate'] and product_unst['doseInformations'][0]['startDate']:
                    product['doseInformations'][0]['startDate'] = product_unst['doseInformations'][0]['startDate']
                if not product['doseInformations'][0]['duration'] and product_unst['doseInformations'][0]['duration']:
                    product['doseInformations'][0]['duration'] = product_unst['doseInformations'][0]['duration']
                if not product['doseInformations'][0]['frequency_value'] and product_unst['doseInformations'][0]['frequency_value']:
                    product['doseInformations'][0]['frequency_value'] = product_unst['doseInformations'][0][
                        'frequency_value']
                if not product['doseInformations'][0]['route_value'] and product_unst['doseInformations'][0]['route_value']:
                    product['doseInformations'][0]['route_value'] = product_unst['doseInformations'][0]['route_value']
                if not product['actionTaken']['value'] and product_unst['actionTaken']['value']:
                    product['actionTaken']['value'] = product_unst['actionTaken']['value']
                if not product['role_value'] and product_unst['role_value']:
                    product['role_value'] = product_unst['role_value']
                if not product['dosageForm_value'] and product_unst['dosageForm_value']:
                    product['dosageForm_value'] = product_unst['dosageForm_value']
                if not product['indications'] and product_unst['indications']:
                    product['dosageForm_value'] = product_unst['indications']
    for product in pvi_json['products']:
        if product['license_value']:
            product['license_value'] = product['license_value'].strip()
    return pvi_json


def populate_event_from_unstruct(pvi_json, unstruct_json):
    event_name_list = []
    reaction_coded_list = []

    for event in pvi_json["events"]:
        if event['reportedReaction']:
            event_name_list.append(event['reportedReaction'].lower())
        if event['reactionCoded']:
            reaction_coded_list.append(event['reactionCoded'].lower())
    # if len(pvi_json['events']) == 1:
    #     if not pvi_json['events'][0]['reportedReaction']:
    if check_list_length(unstruct_json['events']):
        for event_unst in unstruct_json['events']:
            if event_unst['reportedReaction'].lower() not in event_name_list and event['reportedReaction'].lower() not in reaction_coded_list:
                pvi_json['events'].append(event_unst)
    for event in pvi_json['events']:
        for event_unst in unstruct_json['events']:
            if event['reportedReaction'].lower() == event_unst['reportedReaction'].lower():
                if not event['outcome'] and event_unst['outcome']:
                    event['outcome'] = event_unst['outcome']
                if not event['startDate'] and event_unst['startDate']:
                    event['startDate'] = event_unst['startDate']
                if not event['seriousnesses'][0]['value'] and event_unst['seriousnesses'][0]['value']:
                    event['seriousnesses'][0]['value'] = event_unst['seriousnesses'][0]['value']
    for event in pvi_json['events']:
        event['reportedReaction'] = event['reportedReaction'].strip()
    return pvi_json


def populate_test_from_unstruct(pvi_json, unstruct_json):
    test_name_list = []
    test_list = []
    for test in pvi_json['tests']:
        if test['testName']:
            test_name_list.append(test['testName'].lower())
    if check_list_length(unstruct_json['tests']):
        for test_unst in unstruct_json['tests']:
            if test_unst['testName'].lower() not in test_name_list:
                pvi_json['tests'].append(test_unst)
    for tests in pvi_json['tests']:
        if tests['testName'] not in ['', None]:
            test_list.append(tests)
    if len(test_list) == 0:
        test_list.append(copy.deepcopy(pvi_json['tests'][0]))
    pvi_json['tests'] = test_list

    return pvi_json


def populate_patient_from_unstruct(pvi_json, unstruct_json):
    med_his_list = []
    drug_name_list = []
    parent_med_his_list = []
    med_his_pvi = []
    past_drug_list = []
    if not pvi_json['patient']['age']['inputValue'] and unstruct_json['patient']['age']['inputValue']:
        pvi_json['patient']['age']['inputValue'] = unstruct_json['patient']['age']['inputValue'].replace('old', '')
    elif pvi_json['patient']['age']['inputValue'] and pvi_json['patient']['age']['inputValue'].lower() in ['unk',
                                                                                                           'unknown']:
        if unstruct_json['patient']['age']['inputValue']:
            pvi_json['patient']['age']['inputValue'] = unstruct_json['patient']['age']['inputValue']
    if not pvi_json['patient']['gender'] and unstruct_json['patient']['gender']:
        pvi_json['patient']['gender'] = unstruct_json['patient']['gender']
    elif pvi_json['patient']['gender'] and pvi_json['patient']['gender'].lower() in ['unk', 'unknown']:
        if unstruct_json['patient']['gender']:
            pvi_json['patient']['gender'] = unstruct_json['patient']['gender']
    if not pvi_json['patient']['pregnant'] and unstruct_json['patient']['pregnancy']:
        pvi_json['patient']['pregnant'] = unstruct_json['patient']['pregnancy']
    #
    for med_his in pvi_json['patient']['medicalHistories']:
        if med_his['reportedReaction']:
            med_his_list.append(med_his['reportedReaction'].lower())
    # if len(pvi_json['patient']['medicalHistories']) == 1:
    #     if not pvi_json['patient']['medicalHistories'][0]['reportedReaction']:
    if check_list_length(unstruct_json['patient']['medicalHistories']):
        for med_his_unst in unstruct_json['patient']['medicalHistories']:
            if med_his_unst['reportedReaction'].lower() not in med_his_list:
                pvi_json['patient']['medicalHistories'].append(med_his_unst)
    #
    for drug_his in pvi_json['patient']['pastDrugHistories']:
        if drug_his['drugName']:
            drug_name_list.append(drug_his['drugName'].lower())
    if check_list_length(unstruct_json['patient']['pastDrugHistories']):
        for drug_his_unst in unstruct_json['patient']['pastDrugHistories']:
            if drug_his_unst['drugName'].lower() not in drug_name_list:
                pvi_json['patient']['pastDrugHistories'].append(drug_his_unst)
    # # for parent_med_his in pvi_json['parent']['medicalHistories']:
    # #     if parent_med_his['reportedReaction']:
    # #         parent_med_his_list.append(arent_med_his['reportedReaction'].lower())
    #
    # if 'lmpDate' in unstruct_json['patient'].keys():
    #     pvi_json['patient']['lmpDate'] = unstruct_json['patient']['lmpDate']
    #
    for med in pvi_json['patient']['medicalHistories']:
        if med['reportedReaction'] not in ['', None]:
            med_his_pvi.append(med)
    if len(med_his_pvi) == 0:
        med_his_pvi.append(copy.deepcopy(pvi_json['patient']['medicalHistories'][0]))
    pvi_json['patient']['medicalHistories'] = med_his_pvi
    #
    for drug in pvi_json['patient']['pastDrugHistories']:
        if drug['drugName'] not in ['', None]:
            past_drug_list.append(drug)
    if len(past_drug_list) == 0:
        past_drug_list.append(copy.deepcopy(pvi_json['patient']['pastDrugHistories'][0]))
    pvi_json['patient']['pastDrugHistories'] = past_drug_list
    return pvi_json


def populate_reporter_from_unstruct(pvi_json, unstruct_json):
    for reporter in pvi_json['reporters']:
        if not reporter['country'] and unstruct_json['reporters'][0]['country']:
            reporter['country'] = unstruct_json['reporters'][0]['country']
        # if not reporter['qualification'] and unstruct_json['reporters'][0]['qualification']:
        #     reporter['qualification'] = unstruct_json['reporters'][0]['qualification']
    return pvi_json


def populate_general_fields_from_unstruct(pvi_json, unstruct_json):
    # if not pvi_json['deathDetail']['deathDate']['date'] and unstruct_json['deathDetail']['deathDate']['date']:
    #     pvi_json['deathDetail']['deathDate']['date'] = unstruct_json['deathDetail']['deathDate']['date']
    if check_list_length(unstruct_json['deathDetail']['deathCauses']):
        if not pvi_json['deathDetail']['deathCauses']['reportedReaction'] and \
                unstruct_json['deathDetail']['deathCauses'][0]['reportedReaction']:
            pvi_json['deathDetail']['deathCauses']['reportedReaction'] = unstruct_json['deathDetail']['deathCauses'][0][
                'reportedReaction']
    # if not pvi_json['deathDetail']['autopsyDone'] and unstruct_json['deathDetail']['autopsyDone']:
    #     pvi_json['deathDetail']['autopsyDone'] = unstruct_json['deathDetail']['autopsyDone']
    #
    # if not pvi_json['sourceType'][0]['value'] and unstruct_json['sourceType'][0]['value']:
    #     pvi_json['sourceType'][0]['value'] = unstruct_json['sourceType'][0]['value']
    # # if not pvi_json['study']['studyType'] and unstruct_json['study']['studyType']:
    # #     pvi_json['study']['studyType'] = unstruct_json['study']['studyType']
    if not pvi_json['study']['studyNumber'] and unstruct_json['study']['studyNumber']:
        try:
            data = re.findall("[A-Za-z0-9-# ]+", unstruct_json['study']['studyNumber'])
        except:
            data[0] = None
        if data:
            pvi_json['study']['studyNumber'] = data[0]
    return pvi_json


headers = {
    'PVI_PUBLIC_TOKEN': 'zn9MrreyDiATUdoUs/FMmw70qMDExQOya/9LFs1uE5lCp2eCxNeOZCdTgubUCdbYWpLu3bRJRL5zD79iOm+sewLbXnt9r1KbSBNJhWd9BKhbGFhpYPVodA5J7P87aUnXfHLSSXB1F5xTJkCjyMszHA==',
    'Cookie': 'PVSecurity-I=daaf8dcb-6047-457f-a130-128abef64a5d'
}
url = "https://pvcm52-service-dev.rxlogix.com/api/pv-browser/WHODD/search?search_value="


def encoding_call(event_name):
    url = "http://52.2.44.188:9000/autocoding/live?input_string="
    payload = {}
    headers = {}
    response = requests.request("GET", url + event_name, headers=headers, data=payload)
    if response.status_code == 200:
        input = json.loads(response.text)
        output = []
        for ele in input['searchList']:
            if all(len(word) <= 4 for word in event_name.split()):
                if is_abbrev(event_name, ele['lltName']):
                    # print(event_name + ' > ' + ele['lltName'])
                    # print((ele['lltName'], ele['score']))
                    output.append((ele['lltName'], ele['score']))
            else:
                output.append((ele['lltName'], ele['score']))
    else:
        output = []
    # print(json.dumps(output, indent=2))
    return output


def is_abbrev(abbrev, text):
    abbrev = abbrev.lower()
    text = text.lower()
    words = text.split()
    if not abbrev:
        return True
    if abbrev and not text:
        return False
    if abbrev[0] != text[0]:
        return False
    else:
        return (is_abbrev(abbrev[1:], ' '.join(words[1:])) or
                any(is_abbrev(abbrev[1:], text[i + 1:])
                    for i in range(len(words[0]))))


def abbrev_check_in_list(abbrev, ele_list):
    for ele in ele_list:
        if ele and is_abbrev(abbrev, ele):
            # print(abbrev + ' > ' + ele)
            return True
    return False


def event_validation(event_list):
    event_encoded_list = []
    for event in event_list:
        encoded_terms = encoding_call(event_name=event)
        encoded_terms = [enc[0] for enc in encoded_terms]
        event_encoded_list.append(encoded_terms)
    eviction_list = []
    for i in range(len(event_encoded_list)):
        if len(event_encoded_list[i]) == 0:
            eviction_list.append(i)
            continue
        for j in range(i + 1, len(event_encoded_list)):
            test_list1, test_list2 = event_encoded_list[i], event_encoded_list[j]
            res = reduce(lambda x, y: x + test_list1.count(y), set(test_list2), 0)
            if res > 1:
                event_encoded_list[j] = event_encoded_list[i]
                if len(event_list[i]) >= len(event_list[j]):
                    event_list[j] = event_list[i]
                else:
                    event_list[i] = event_list[j]
    #                eviction_list.append(j)

    event_list = [None if i in eviction_list else event_encoded_list[i][0] for i in range(len(event_list))]

    return event_list


def merge_dict(dict1, dict2):
    keys = dict1.keys()
    for key in keys:
        if dict1[key] is None and key in dict2:
            dict1[key] = dict2[key]
        elif type(dict1[key]) is str and key in dict2 and dict1[key].strip() == "":
            dict1[key] = dict2[key]
        elif type(dict1[key]) is dict and key in dict2:
            dict1[key] = merge_dict(dict1[key], dict2[key])
        elif type(dict1[key]) is list and key in dict2:
            for index in range(len(dict1[key])):
                dict1[key][index] = merge_dict(dict1[key][index], dict2[key][index])
    return dict1


def event_processing(event_json):
    event_list = []
    for event in event_json:
        event_list.append(event['reportedReaction'])

    event_list = event_validation(event_list)
    for index in range(len(event_list)):
        event_json[index]['reactionCoded'] = event_list[index]
    event_json_final = []
    done_event = []
    for index in range(len(event_list)):
        event = event_list[index]
        if event is None:
            continue
        if event_list.count(event) == 1:
            event_json_final.append(event_json[index])
        else:
            if event_json[index]['reactionCoded'] in done_event:
                continue
            for second_index in range(index + 1, len(event_list)):
                if event_json[index]['reactionCoded'] == event_json[second_index]['reactionCoded']:
                    event_json[index] = merge_dict(event_json[index], event_json[second_index])
            done_event.append(event_json[index]['reactionCoded'])
            event_json_final.append(event_json[index])
    return event_json_final


def validate_product(product_list):
    for index in range(len(product_list)):
        product = product_list[index]
        response = requests.request("GET", url + str(product), headers=headers, data={})
        if len(response.text) < 5:
            product_list[index] = None

    return product_list


def remove_null_products(pvi_json):
    licence_value_list = []
    new_product_json = []
    for product in pvi_json['products']:
        licence_value_list.append(product['license_value'])
#    licence_value_list = validate_product(licence_value_list)
    for index in range(len(pvi_json['products'])):
        if licence_value_list[index] is None:
            continue
        new_product_json.append(pvi_json['products'][index])
    pvi_json['products'] = new_product_json
    return pvi_json


def populate_data_from_unstruct(pvi_json, unstruct_json):
    try:
        pvi_json = populate_event_from_unstruct(pvi_json, unstruct_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_patient_from_unstruct(pvi_json, unstruct_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_product_form_unstruct(pvi_json, unstruct_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_test_from_unstruct(pvi_json, unstruct_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_general_fields_from_unstruct(pvi_json, unstruct_json)
    except:
        traceback.print_exc()
    pvi_json['summary']['senderComments'] = None
    return pvi_json



def get_postprocessed_json(pvi_json, extracted_json):
    try:
        pvi_json = populate_product_event(pvi_json, extracted_json)
    except:
        traceback.print_exc()
    url = 'http://54.161.252.139:9888/unstruct/live'
    try:
        unstruct_json = response_from_external_ws(url, 'POST', pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_data_from_unstruct(pvi_json, unstruct_json)
    except:
        traceback.print_exc()
    try:
        pvi_json['events'] = event_processing(pvi_json['events'])
    except:
        traceback.print_exc()
    try:
        pvi_json = remove_null_products(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json
