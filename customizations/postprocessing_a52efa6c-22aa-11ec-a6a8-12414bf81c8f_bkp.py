'''
version    date      change desc    changed by
0.1       20-April-2022  changes in post processing Nand kishore










'''



import re
import pandas as pd
from postal.parser import parse_address
from nameparser import HumanName as hn
import copy
import traceback
from copy import deepcopy
import json


'''
import json
mapping_file = "/home/rx-sandeshs/backendservice/utility/template/form_configurations/a52efa6c-22aa-11ec-a6a8-12414bf81c8f.json"
with open(mapping_file) as json_file:
    pvi_json = json.load(json_file)
'''


# check None type
def field_na_checker(inp_string):
    if inp_string:
        return inp_string
    else:
        return None


# segregate products based on role of products
def role_value_based_prod_seperation(pvi_json):
    suspect_prods = []
    concom_prods = []
    suspect_first = []
    concom_first = []
    for every_prod in pvi_json["products"]:
        if every_prod["license_value"] is not None and every_prod["role_value"] == "Suspect":
            suspect_prods.append(every_prod)
        if every_prod["license_value"] is not None and every_prod["role_value"] == "Concomitant":
            concom_prods.append(every_prod)
        if every_prod["license_value"] is not None and every_prod["role_value"] == "Suspect_first":
            suspect_first.append(every_prod)
        if every_prod["license_value"] is not None and every_prod["role_value"] == "Concomitant_first":
            concom_first.append(every_prod)
    return suspect_prods, concom_prods, suspect_first, concom_first


# remove extra characters
def strip_characters(inp_string):
    inp_string = re.sub(r'[^\x00-\x7F]+', '', inp_string)
    if inp_string:
        out_string = inp_string.replace("\n", "").strip(" { } ( ) \ / ; . [ ] , - : ")
        return out_string
    else:
        return inp_string


# extract regex match
def regex_match(pattern, text):
    value = None
    matched_data = re.search(pattern, text)
    if matched_data:
        value = matched_data.group()
    return value


# processing products data
def preprocess_productdata(pvi_json):
    for every_prod in pvi_json["products"]:
        if every_prod["role_value"] == "Suspect_first" and every_prod["license_value"] != None:
            try:
                every_prod["seq_num"] = re.search("\d", str(every_prod["seq_num"]))
                if every_prod["seq_num"] is None:
                    every_prod["seq_num"] = "0"
                else:
                    every_prod["seq_num"] = every_prod["seq_num"].group()
                if every_prod["seq_num"] == "1":
                    first_prod_dose_info = every_prod["doseInformations"]
                    dose = ""
                    route = ""
                    start_date = ""
                    for every_dose in first_prod_dose_info:
                        if every_dose["dose_inputValue"]:
                            dose = dose + every_dose["dose_inputValue"]
                        if every_dose["route_value"]:
                            route = route + every_dose["route_value"]
                        if every_dose["startDate"]:
                            start_date = start_date + every_dose["startDate"]
                        first_prod_indication = every_prod["indications"]
                    reported_reaction = ""
                    for every_indication in first_prod_indication:
                        if every_indication["reportedReaction"]:
                            reported_reaction = reported_reaction + every_indication["reportedReaction"]
                    dose_temp = pvi_json["products"][0]["doseInformations"][0]
                    dose_temp["doseContinuing"] = None
                    dose_temp["customProperty_batchNumber_value"] = None
                    dose_temp["customProperty_expiryDate"] = None
                    dose_temp["description"] = None
                    dose_temp["dose_inputValue"] = None
                    dose_temp["duration"] = None
                    dose_temp["endDate"] = None
                    dose_temp["frequency_value"] = None
                    dose_temp["route_value"] = None
                    dose_temp["startDate"] = None
                    every_prod["doseInformations"] = [dose_temp]
                    indication_temp = pvi_json["products"][0]["indications"][0]
                    indication_temp["reactionCoded"] = None
                    indication_temp["reportedReaction"] = None
                    every_prod["indications"] = [indication_temp]
                    dose_dict = {}
                    try:
                        dose_dict["dose"] = dose.strip("||")
                    except:
                        dose_dict["dose"] = dose
                    try:
                        dose_dict["route"] = route.strip("||")
                    except:
                        dose_dict["route"] = route
                    try:
                        dose_dict["start_date"] = start_date.strip("||")
                    except:
                        dose_dict["start_date"] = start_date
                    try:
                        dose_dict["indication"] = reported_reaction.strip("||")
                    except:
                        dose_dict["indication"] = reported_reaction
                license_reported = ""
                coded_form = ["", ""]
                if every_prod["license_value"]:
                    try:
                        license_reported = strip_characters(
                            regex_match("[)].*[(]", every_prod["license_value"].rstrip("()")))
                    except:
                        license_reported = field_na_checker("")
                    try:
                        license_coded_form = strip_characters(regex_match("[(].*,|[(].*", every_prod["license_value"]))
                        coded_form = license_coded_form.split(")")
                    except:
                        coded_form = ["", ""]
                    try:
                        res = every_prod["license_value"].split(",")
                        if len(res) == 2:
                            strength = res[1].strip("")
                            every_prod["ingredients"][0]["strength"] = strip_characters(strength)
                    except:
                        pass
                every_prod["license_value"] = None
                liscense_coded = field_na_checker(coded_form[0])
                try:
                    formulation = field_na_checker(strip_characters(coded_form[1]))
                except:
                    formulation = field_na_checker("")
                if license_reported not in [None, ""]:
                    if "codenotbroken" not in "".join(license_reported.split()).lower():
                        every_prod["license_value"] = field_na_checker(license_reported)
                    elif "Blinded" in license_reported and license_reported not in [None, ""]:
                        every_prod["license_value"] = field_na_checker(
                            strip_characters(license_reported.strip("Blinded")))
                    else:
                        every_prod["license_value"] = field_na_checker(license_reported)
                if formulation:
                    formulation = re.sub(r'[^\x00-\x7F]+', '', formulation)
                    every_prod["dosageForm_value"] = field_na_checker(formulation)
                    if every_prod["dosageForm_value"]:
                        every_prod["dosageForm_value"] = every_prod["dosageForm_value"].replace("  ", " ")
            except Exception as e:
                print(e)
                # print("check in suspect first")
                pass
        elif every_prod["role_value"] == "Concomitant_first" and every_prod["license_value"] != None:
            try:
                every_prod["seq_num"] = re.search("\d", str(every_prod["seq_num"]))
                if every_prod["seq_num"] == None:
                    every_prod["seq_num"] = "0"
                else:
                    every_prod["seq_num"] = every_prod["seq_num"].group()
                liscense_reported_cf = ""
                liscense_coded_cf = ""
                if every_prod["license_value"]:
                    liscense_reported_cf = strip_characters(every_prod["license_value"])
                every_prod["license_value"] = None
                if every_prod["dosageForm_value"]:
                    liscense_coded_cf = strip_characters(every_prod["dosageForm_value"])
                dose_form_cf = ""
                try:
                    liscense_coded_up_cf = liscense_coded_cf.split(")")[0]
                except:
                    liscense_coded_up_cf = field_na_checker("")
                try:
                    liscense_reported_up_cf = liscense_reported_cf.split("(")[0]
                except:
                    liscense_reported_up_cf = field_na_checker("")
                try:
                    dose_form_cf = liscense_coded_cf.split(")")[1].strip()
                except:
                    dose_form_cf = field_na_checker("")
                every_prod["dosageForm_value"] = None
                try:
                    dose_date_cf = ""
                    if every_prod["regimen"]:
                        dose_date_cf = strip_characters(every_prod["regimen"]).replace(
                            "(Continued on Additional Information Page)", "")
                except:
                    dose_date_cf = field_na_checker("")
                every_prod["regimen"] = None
                try:
                    start_end_date_cf = ""
                    start_date_cf = ""
                    if dose_date_cf:
                        start_end_date_cf = strip_characters(dose_date_cf.split("&")[0])
                        start_date_cf = strip_characters(start_end_date_cf.split("/")[0])
                except:
                    start_end_date_cf = ""
                    start_date_cf = ""
                try:
                    end_date_cf = ""
                    end_date_cf = strip_characters(start_end_date_cf.split("/")[1])
                except:
                    end_date_cf = field_na_checker("")
                if liscense_reported_up_cf not in [None, ""]:
                    if "codenotbroken" not in "".join(liscense_reported_up_cf.split()).lower():
                        every_prod["license_value"] = field_na_checker(liscense_reported_up_cf)
                    elif "Blinded" in liscense_reported_up_cf and liscense_reported_up_cf not in [None, ""]:
                        every_prod["license_value"] = field_na_checker(liscense_reported_up_cf.strip("Blinded"))
                    else:
                        every_prod["license_value"] = field_na_checker(liscense_reported_up_cf)
                every_prod["dosageForm_value"] = field_na_checker(dose_form_cf)
                if every_prod["dosageForm_value"]:
                    every_prod["dosageForm_value"] = every_prod["dosageForm_value"].replace("  ", " ")
                if start_date_cf and start_date_cf.lower() not in ["unk","unknown"]:
                    every_prod["doseInformations"][0]["startDate"] = field_na_checker(start_date_cf)
                else:
                    every_prod["doseInformations"][0]["startDate"] = None
                if end_date_cf and "Ongoing" in end_date_cf:
                    every_prod["doseInformations"][0]["endDate"] = "Ongoing"
                elif end_date_cf and end_date_cf.lower() not in ['unk','unknown']:
                    every_prod["doseInformations"][0]["endDate"] = field_na_checker(end_date_cf)
                else:
                    every_prod["doseInformations"][0]["endDate"] = None
            except:
                print("check in concom first")
        elif every_prod["role_value"] == "Concomitant" and every_prod["license_value"] != None:
            try:
                every_prod["seq_num"] = re.search("\d{1,2}", str(every_prod["seq_num"]))
                if every_prod["seq_num"] == None:
                    every_prod["seq_num"] = "0"
                else:
                    every_prod["seq_num"] = every_prod["seq_num"].group()
                liscense_reported_cl = strip_characters(every_prod["license_value"])
                every_prod["license_value"] = None
                liscense_coded_cl = strip_characters(every_prod["dosageForm_value"])
                try:
                    liscense_coded_up_cl = liscense_coded_cl.split(")")[0]
                except:
                    liscense_coded_up_cl = None
                try:
                    dose_form_cl = liscense_coded_cl.split(")")[1].strip()
                except:
                    print("check in dose_form_cl")
                    dose_form_cl = None
                every_prod["dosageForm_value"] = None
                dose_date_cl = strip_characters(
                    every_prod["regimen"].replace("23. OTHER RELEVANT HISTORY  continued", ""))
                if "Case Version" in dose_date_cl:
                    try:
                        footer_start_pos = dose_date_cl.find("Case Version")
                        dose_date_cl = dose_date_cl[:footer_start_pos - 18]
                    except:
                        pass
                every_prod["regimen"] = None
                try:
                    start_end_date = strip_characters(dose_date_cl.split("; ")[1])
                    start_date_cl = ""
                    start_date_cl = strip_characters(start_end_date)
                except:
                    print("check in cf start date1")
                    pass
                try:
                    end_date_cl = ""
                    end_date_cl = strip_characters(start_end_date.split("/")[1])
                except:
                    print("check in cf start date2")
                    pass
                if liscense_reported_cl not in ["", None]:
                    if "codenotbroken" not in "".join(liscense_reported_cl.split()).lower():
                        every_prod["license_value"] = field_na_checker(liscense_reported_cl)
                    elif "Blinded" in liscense_reported_cl and liscense_reported_cl not in [None, ""]:
                        every_prod["license_value"] = field_na_checker(liscense_reported_cl.strip("Blinded"))
                    else:
                        every_prod["license_value"] = field_na_checker(liscense_reported_cl)
                every_prod["dosageForm_value"] = field_na_checker(dose_form_cl)
                if every_prod["dosageForm_value"]:
                    every_prod["dosageForm_value"] = every_prod["dosageForm_value"].replace("  ", " ")
                if start_date_cl and start_date_cl.lower() not in ["unk","unknown"]:
                    every_prod["doseInformations"][0]["startDate"] = start_date_cl
                else:
                    every_prod["doseInformations"][0]["startDate"] = None
                if "Ongoing" in end_date_cl:
                    every_prod["doseInformations"][0]["endDate"] = "Ongoing"
                elif end_date_cl and end_date_cl.lower() not in ['unk','unknown']:
                    every_prod["doseInformations"][0]["endDate"] = field_na_checker(end_date_cl)
                else:
                    every_prod["doseInformations"][0]["endDate"] = None
            except:
                print("check in concom last page")
        elif every_prod["role_value"] == "Suspect" and every_prod["license_value"] != None:
            try:
                try:
                    licence_val = strip_characters(
                        every_prod["license_value"].replace("14-19. SUSPECT DRUG(S) continued", "").replace("\n", " "))
                except:
                    licence_val = every_prod["license_value"]
                every_prod["license_value"] = None
                seq_numb = regex_match("^#\d{1,2}\s*[)]", licence_val)
                every_prod["seq_num"] = re.search("\d", seq_numb)
                if every_prod["seq_num"] == None:
                    every_prod["seq_num"] = "0"
                else:
                    every_prod["seq_num"] = every_prod["seq_num"].group()
                liscense_reported_sl = strip_characters(regex_match("[)].*[(]", licence_val))
                liscense_coded_form_sl = strip_characters(regex_match("[(].*;|[(].*", licence_val))
                liscence_coded_sl = liscense_coded_form_sl.split(")")[0]
                liscence_coded_sl = liscence_coded_sl.replace("  ", " ")
                try:
                    liscence_form_sl = liscense_coded_form_sl.split(")")[-1]
                    liscence_form_sl = liscence_form_sl.split(",")[0]
                except:
                    liscence_form_sl = None
                if liscense_reported_sl not in ["", None]:
                    if "codenotbroken" not in "".join(liscense_reported_sl.split()).lower():
                        every_prod["license_value"] = field_na_checker(liscense_reported_sl)
                    elif liscense_reported_sl not in [None, ""] and "Blinded" in liscense_reported_sl:
                        every_prod["license_value"] = field_na_checker(liscense_reported_sl.strip("Blinded"))
                    else:
                        every_prod["license_value"] = field_na_checker(liscense_reported_sl)
                if every_prod["dosageForm_value"]:
                    dosageForm_value = every_prod["dosageForm_value"].replace("\n", "")
                every_prod["dosageForm_value"] = None
                dose_freq = regex_match("^.*;", dosageForm_value)

                try:
                    if not ("Blinded".lower() in dose_freq.lower()):
                        if "," in dose_freq:
                            comma_index = dose_freq.find(",")
                            comma_dose = dose_freq[:comma_index]
                            comma_freq = dose_freq[comma_index + 1:].replace("ADDITIONAL INFO","").replace("15. DAILY DOSE(S);","")           # Remove Junk (Change)
                            every_prod["doseInformations"][0]["dose_inputValue"] = field_na_checker(
                                strip_characters(comma_dose))
                            # if len(dose_freq.split(","))>1:
                            every_prod["doseInformations"][0]["frequency_value"] = field_na_checker(strip_characters(comma_freq))
                        else:
                            comma_dose = field_na_checker(strip_characters(dose_freq))
                            comma_freq = None
                            every_prod["doseInformations"][0]["dose_inputValue"] = comma_dose
                            if every_prod["doseInformations"][0]["dose_inputValue"].lower() in ["unk", "unknown"]:                              #change evey_prod_dose to every_prod
                                every_prod["doseInformations"][0]["dose_inputValue"] = None
                            # every_prod["doseInformations"][0]["frequency_value"] = field_na_checker(strip_characters(comma_freq))
                            every_prod["doseInformations"][0]["frequency_value"] = comma_freq
                    if every_prod["doseInformations"][0]["dose_inputValue"]:
                        if "(" in every_prod["doseInformations"][0]["dose_inputValue"] and ")" not in \
                                every_prod["doseInformations"][0]["dose_inputValue"]:
                            every_prod["doseInformations"][0]["dose_inputValue"] = every_prod["doseInformations"][0][
                                                                                       "dose_inputValue"] + ")"
                except:
                    pass
                every_prod["dosageForm_value"] = field_na_checker(strip_characters(liscence_form_sl))
                if every_prod["dosageForm_value"]:
                    every_prod["dosageForm_value"] = every_prod["dosageForm_value"].replace("  ", " ")
                dosageForm_value = re.sub(r'[^\x00-\x7F]+', '', dosageForm_value)
                dosageForm_value = dosageForm_value.replace("\n", " ")
                dosageForm_value = dosageForm_value.replace("NISTRATION continued", "")
                form = strip_characters(regex_match(";.*", dosageForm_value))
                form = form.replace('ADDITIONAL INFO',"").replace('15. DAILY DOSE(S);16. ROUTE(S) OF ADMIN',"")       #removing Junk (Change)
                if form.lower() in ['unk','unknown']:
                    form = None
                every_prod["doseInformations"][0]["route_value"] = form
                if every_prod["doseInformations"][0]["route_value"]:
                    if every_prod["doseInformations"][0]["frequency_value"]:
                        every_prod["doseInformations"][0]["frequency_value"]=every_prod["doseInformations"][0]["frequency_value"].split(';')[0]
                else:
                    every_prod["doseInformations"][0]["frequency_value"] = strip_characters(every_prod["doseInformations"][0]["frequency_value"])
                dose_date = every_prod["regimen"].replace("\n", " ")
                every_prod["regimen"] = None
                try:
                    start_date_sl = strip_characters(dose_date.split("/")[0].strip().split(" ")[0])
                    if start_date_sl:
                        if start_date_sl.lower() in ['unk','unknown']:                        #change
                            every_prod["doseInformations"][0]["startDate"] = None

                        else:
                            every_prod["doseInformations"][0]["startDate"] = field_na_checker(
                                strip_characters(start_date_sl))
                except:
                    every_prod["doseInformations"][0]["startDate"] = None
                    print("error in start date suspect last page")
                try:
                    end_date_sl = dose_date.split("/")[1].strip().split(" ")[0]
                    if "Ongoing" in end_date_sl:
                        every_prod["doseInformations"][0]["endDate"] = "Ongoing"
                    else:
                        every_prod["doseInformations"][0]["endDate"] = field_na_checker(strip_characters(end_date_sl))
                except:
                    every_prod["doseInformations"][0]["endDate"] = None
                    print("check in end date suspect last page")
            except Exception as e:
                print(e)
                print("check in suspect last page")
    return pvi_json, dose_dict


# first page suspect products dose information mapping
def first_suspect_dose(prod, dose_dict):
    if dose_dict["dose"]:
        dose_info = dose_dict["dose"].split("||")
        for every_dose in dose_info:
            dose_val = ""
            freq_val = ""
            split_dose = every_dose.split("&")
            try:
                dose_val = strip_characters(split_dose[1])
                if "Blinded".lower() in dose_val.lower():
                    continue
            except:
                pass
            seq_num_dose = re.search("\d{1,2}", split_dose[0])
            if seq_num_dose == None:
                seq_num_dose = "0"
            else:
                seq_num_dose = seq_num_dose.group()
            try:
                if split_dose[1]:
                    dose_freq = split_dose[1]
                    if "," in split_dose[1]:
                        comma_index = dose_freq.find(",")
                        comma_dose = dose_freq[:comma_index]
                        comma_freq = dose_freq[comma_index + 1:]
                        dose_val = field_na_checker(strip_characters(comma_dose))
                        freq_val = field_na_checker(strip_characters(comma_freq))
                    else:
                        dose_val = field_na_checker(strip_characters(dose_freq))
                        freq_val = None
            except:
                pass
            for every_prod_dose in prod:
                if every_prod_dose["role_value"] == "Suspect_first" and every_prod_dose["seq_num"] == seq_num_dose:
                    every_prod_dose["doseInformations"][0]["dose_inputValue"] = field_na_checker(dose_val)
                    if every_prod_dose["doseInformations"][0]["dose_inputValue"]:
                        if every_prod_dose["doseInformations"][0]["dose_inputValue"].lower() in ["unk", "unknown"]:
                            every_prod_dose["doseInformations"][0]["dose_inputValue"] = None
                        every_prod_dose["doseInformations"][0]["frequency_value"] = field_na_checker(freq_val)
                    if every_prod_dose["doseInformations"][0]["dose_inputValue"]:
                        if "(" in every_prod_dose["doseInformations"][0]["dose_inputValue"] and ")" not in \
                                every_prod_dose["doseInformations"][0]["dose_inputValue"]:
                            every_prod_dose["doseInformations"][0]["dose_inputValue"] = \
                            every_prod_dose["doseInformations"][0]["dose_inputValue"] + ")"
    if dose_dict["route"]:
        route_info = dose_dict["route"].split("||")
        for every_route in route_info:
            route_val = ""
            split_route = every_route.split("&")
            try:
                route_val = strip_characters(split_route[1])
                if "Blinded information" in route_val:
                    continue
            except:
                pass
            seq_num_route = re.search("\d{1,2}", split_route[0])
            if seq_num_route == None:
                seq_num_route = "0"
            else:
                seq_num_route = seq_num_route.group()
            for every_prod_dose in prod:
                if every_prod_dose["role_value"] == "Suspect_first" and every_prod_dose["seq_num"] == seq_num_route:
                    if route_val and route_val.lower() in ["unknown"]:
                        every_prod_dose["doseInformations"][0]["route_value"] = None
                    else:
                        every_prod_dose["doseInformations"][0]["route_value"] = field_na_checker(route_val).replace('ADDITIONAL INFO',"").replace('15. DAILY DOSE(S);16. ROUTE(S) OF ADMIN',"")             #change
    if dose_dict["start_date"]:
        dates_info = dose_dict["start_date"].split("||")
        for every_date in dates_info:
            start_date = ""
            end_date = ""
            split_date = every_date.split("&")
            try:
                start_date = strip_characters(split_date[1])
                start_date = start_date.split(" ")[0]
            except:
                pass
            try:
                end_date = strip_characters(split_date[2])
                end_date = end_date.split(" ")[0]
            except:
                pass
            seq_num_date = re.search("\d{1,2}", split_date[0])
            if seq_num_date == None:
                seq_num_date = "0"
            else:
                seq_num_date = seq_num_date.group()
            for every_prod_dose in prod:
                if every_prod_dose["role_value"] == "Suspect_first" and every_prod_dose["seq_num"] == seq_num_date:
                    if start_date.lower() not in ['unk','unknown']:
                        every_prod_dose["doseInformations"][0]["startDate"] = field_na_checker(start_date)
                    else:
                        every_prod_dose["doseInformations"][0]["startDate"] = None
                    if end_date.lower() not in ['unk','unknown']:
                        every_prod_dose["doseInformations"][0]["endDate"] = field_na_checker(end_date)
                    else:
                        every_prod_dose["doseInformations"][0]["startDate"] = None
    if dose_dict["indication"]:
        indication_info = dose_dict["indication"].split("||")
        for every_indication in indication_info:
            reported_val = ""
            coded_val = ""
            split_indication = every_indication.split("&")
            try:
                reported_val = strip_characters(split_indication[1])
            except:
                pass
            seq_num_indication = re.search("\d{1,2}", split_indication[0])
            try:
                coded_val = strip_characters(split_indication[2])
            except:
                pass
            if seq_num_indication is None:
                seq_num_indication = "0"
            else:
                seq_num_indication = seq_num_indication.group()
            for every_prod_dose in prod:
                if every_prod_dose["role_value"] == "Suspect_first" and \
                        every_prod_dose["seq_num"] == seq_num_indication:
                    if reported_val and reported_val.lower()  in ['unk','unknown']:
                        reported_val = None
                        every_prod_dose["indications"][0]["reportedReaction"] = reported_val
                    else:
                        every_prod_dose["indications"][0]["reportedReaction"] = field_na_checker(reported_val)
                    if coded_val and coded_val.lower() in ['unk', 'unknown']:
                        coded_val = None
                        every_prod_dose["indications"][0]["reactionCoded"] = coded_val
                    else:
                        every_prod_dose["indications"][0]["reactionCoded"] = field_na_checker(coded_val)
    return prod


def set_indication_suspect(pvi_json, extracted_df):
    indication_dict = suspect_drug_indication(extracted_df)
    products = pvi_json["products"]
    for idx in range(len(products)):
        license = products[idx]['license_value']
        try:
            indications = indication_dict.get(license, None)
            indication = []
            for idx_ind in range(len(indications)):
                if indications[idx_ind] not in indication:                                  #removing same repeating for same product
                    indication.append(indications[idx_ind])

            indications = indication
            indication_final = []
            for ix in range(len(indications)):
                if indications[ix][0] and indications[ix][1]:
                    indication_final.append({"reactionCoded" : indications[ix][0].strip(), "reportedReaction" : indications[ix][1].strip()})
                else:
                    indication_final.append(
                        {"reactionCoded": indications[ix][0], "reportedReaction": indications[ix][1]})
                # pvi_json["products"][idx]["indications"][ix]["reportedReaction"] = indications[ix][0]
                # pvi_json["products"][idx]["indications"][ix]["reactionCoded"] = indications[ix][1]
            pvi_json["products"][idx]["indications"] = indication_final
        except Exception as e:
            print(e)
            # pass
    return pvi_json


def suspect_drug_indication(extracted_df):
    # supect_drug_continues = extracted_df.loc["suspect drug  continued"]["value"]
    # indication_dict = dict()
    # for drug in supect_drug_continues:
    #     indication = list()
    #     drug_name = re.search(r'\([^()]+\)', drug[0])
    #     if drug_name:
    #         drug_name = drug_name.group().replace("\n", "").strip("()")
    #     reported_reaction = re.search("^[^\(]+", drug[2])
    #     if reported_reaction:
    #         reported_reaction = reported_reaction.group().replace("\n", "").strip(" ()")
    #     reaction_coded = re.search(r'\([^()]+\)', drug[2])
    #     if reaction_coded:
    #         reaction_coded = reaction_coded.group().replace("\n", "").strip(" ()")
    #     indication.append((reported_reaction, reaction_coded))
    #     indication_dict[drug_name] = indication
    supect_drug_continues = extracted_df.loc["suspect drug  continued"]["value"]
    indication_dict = dict()
    for drug in supect_drug_continues:
        indication = list()
        drug_name = re.search("[)].*[(]", drug[0].replace("\n",""))
        if drug_name:
            drug_name = drug_name.group().replace("\n", "").strip("() ")
        reported_reaction = re.findall("^[^\(]+", drug[2].replace("\n", "")) \
                     + re.findall("[)].*[(]", drug[2].replace("\n", ""))
        # if reported_reaction:
        #     reported_reaction = reported_reaction.group().replace("\n", "").strip(" ()")
        # reaction_coded = re.findall(r'\([^()]+\)', drug[2]) + re.findall("[)].*[(]", drug[2])
        # if reaction_coded:
        #     reaction_coded = reaction_coded.group().replace("\n", "").strip(" ()")
        reported_reaction = [ele.strip("()") for ele in reported_reaction if ele]
        for ele in reported_reaction:
            if ele.lower()  in ['unk','unknown']:
                ele = None
            indication.append((ele, ele))


        if drug_name in indication_dict.keys():
            indication_dict[drug_name] = indication_dict[drug_name] + indication
        else:
            indication_dict[drug_name] = indication  # replace when same drug name so change it
    return indication_dict


def set_concomitant_continues(pvi_json, extracted_df):
    concomitant_drugs = list()
    startdate = list()
    enddate = list()
    concomitant_drug_continues = extracted_df.loc["22. concomitant drugs(s) last page"]["value"]
    for drug in concomitant_drug_continues:
        license_match = re.search(r'\([^()]+\)', drug[2])
        if license_match:
            license = license_match.group()
            license = license.replace("\n", "").strip(" ()")
            concomitant_drugs.append(license)
            dates = strip_characters(drug[3])
            if '/' in dates:
                dates=dates.split('/')
                start = strip_characters(dates[0])
                end = strip_characters(dates[1])
                if start.lower() == 'unknown':
                    start = None
                if end.lower() == 'unknown':
                    end = None
            else:
                start = strip_characters(dates)
                if start.lower() == 'unknown':
                    start = None
                end = None
            startdate.append(start)
            enddate.append(end)
        else:
            pass
    products = pvi_json["products"]
    products_cnt = len(products)
    # date_cnt = len(startdate)

    for drug in concomitant_drugs:
        idx = 0
        while idx < products_cnt:
            if products[idx]["role_value"] == "Concomitant" and re.match(products[idx]["license_value"], drug):
                pvi_json["products"][idx]["license_value"] = drug
                # pvi_json['products'][idx]['doseInformations'][0]['startDate'] = startdate[date_cnt]
                # pvi_json['products'][idx]['doseInformations'][0]['endDate'] = enddate[date_cnt]
                # date_cnt +=1
                idx += 1
            else:
                idx += 1
    for idx in range(len(products)):
        for idx_date in range(len(concomitant_drugs)):
            if pvi_json['products'][idx]['license_value'] == concomitant_drugs[idx_date]:
                pvi_json['products'][idx]['doseInformations'][0]['startDate'] = startdate[idx_date]
                pvi_json['products'][idx]['doseInformations'][0]['endDate'] = enddate[idx_date]
    return pvi_json


# merging dose information for repeating products
def merge_dose_info(products):
    prod_list = []
    for every_prod in products:
        check_flag = False
        for prod_in_list in prod_list:
            if every_prod["seq_num"] == prod_in_list["seq_num"]:
                check_flag = True
                # if prod_in_list["doseInformations"][-1]["startDate"] == every_prod["doseInformations"][0][
                #     "startDate"] and \
                #         prod_in_list["doseInformations"][-1]["endDate"] == every_prod["doseInformations"][0][
                #     "endDate"] and \
                #         prod_in_list["doseInformations"][-1]["doseContinuing"] == every_prod["doseInformations"][0]["doseContinuing"] and \
                #         prod_in_list["dosageForm_value"] == every_prod["dosageForm_value"]:
                if prod_in_list["doseInformations"][-1]["startDate"] == every_prod["doseInformations"][0][
                    "startDate"] and \
                        prod_in_list["doseInformations"][-1]["endDate"] == every_prod["doseInformations"][0][
                    "endDate"] and \
                        prod_in_list["doseInformations"][-1]["doseContinuing"] == every_prod["doseInformations"][0][
                    "doseContinuing"]:

                    prod_in_list["dosageForm_value"] = every_prod["dosageForm_value"]
                    pass
                else:
                    prod_in_list["doseInformations"].extend(every_prod["doseInformations"])
                    prod_in_list["dosageForm_value"] = every_prod["dosageForm_value"]
                break
        if check_flag == False:
            prod_list.append(every_prod)
    return prod_list


# updating role type to suspect and concom
def change_continued_page_role_type(products):
    seq_num = 1
    for every_prod in products:
        if every_prod["role_value"] == "Concomitant_first":
            every_prod["role_value"] = "Concomitant"
        elif every_prod["role_value"] == "Suspect_first":
            every_prod["role_value"] = "Suspect"
        every_prod["seq_num"] = seq_num
        seq_num += seq_num
    return products


# updating product seq numstartDate
def process_seqnum(pvi_json):
    seq = 1
    for every_prod in pvi_json["products"]:
        every_prod["seq_num"] = seq
        seq += 1
    return pvi_json


# main function for processing products
def postprocess_products(pvi_json, extracted_df):
    pvi_json, first_suspect_dose_dict = preprocess_productdata(pvi_json)
    suspect_prods, concom_prods, suspect_first, concom_first = role_value_based_prod_seperation(pvi_json)
    suspect_first = first_suspect_dose(suspect_first, first_suspect_dose_dict)
    # suspect_first = set_indication_suspect(suspect_first, extracted_df)
    suspect_first.extend(suspect_prods)
    concom_first.extend(concom_prods)
    suspect_first = merge_dose_info(suspect_first)
    concom_first = merge_dose_info(concom_first)
    # concom_first = set_indication_concom(concom_first, extracted_df)
    suspect_first.extend(concom_first)
    products = change_continued_page_role_type(suspect_first)
    pvi_json["products"] = products
    pvi_json = process_seqnum(pvi_json)
    return pvi_json


# processing patient medical history
def update_pat_med_his(pvi_json):
    for every_med_his in pvi_json["patient"]["medicalHistories"]:
        reported_coded = field_na_checker(every_med_his["reportedReaction"])
        if reported_coded:
            reported_coded = reported_coded.replace("\n", "")
            reported = ""
            coded = ""
            try:
                reported = strip_characters(reported_coded.split("(")[0])
                reported = re.sub(r'[^\x00-\x7F]+', '', reported)
                every_med_his["reportedReaction"] = every_med_his["reactionCoded"] = field_na_checker(
                    strip_characters(reported))
            except:
                print("check in med his 1")
            # try:
            #     coded = regex_match("[(].*?[)]", reported_coded)
            #     coded = re.sub(r'[^\x00-\x7F]+', '', coded)
            #     every_med_his["reactionCoded"] = field_na_checker(strip_characters(coded))
            # except:
            #     print("check in med his 2")

        try:
            dates = field_na_checker(every_med_his["startDate"].replace("From/To Dates", ""))
        except:
            print("check in med his 3")
            dates = every_med_his["startDate"]
        every_med_his["startDate"] = None
        every_med_his["endDate"] = None
        if dates:
            start_date = ""
            end_date = ""
            try:
                start_date = strip_characters(dates.split("to")[0])
                every_med_his["startDate"] = field_na_checker(start_date)
            except:
                pass
            try:
                end_date = strip_characters(dates.split("to")[1])
                if "Ongoing" in end_date:
                    every_med_his["continuing"] = "Yes"
                else:
                    every_med_his["endDate"] = field_na_checker(end_date)
            except:
                pass

        try:
            history = field_na_checker(every_med_his["historyNote"].replace("Type of History / Notes", ""))
        except:
            history = every_med_his["historyNote"]
        if history:
            every_med_his["historyNote"] = re.sub(r'[^\x00-\x7F]+', '', history).replace("\n", " ")
        else:
            every_med_his["historyNote"] = field_na_checker("")


    i = 0
    med_his_list = pvi_json["patient"]["medicalHistories"]
    for every_his in med_his_list:
        if not every_his["reportedReaction"] and not every_his["reactionCoded"] and not every_his["startDate"] and not \
        every_his["endDate"] and not every_his["historyNote"]:
            pvi_json["patient"]["medicalHistories"][i] = ""
        i += 1
    while "" in pvi_json["patient"]["medicalHistories"]:
        pvi_json["patient"]["medicalHistories"].remove("")
    return pvi_json


# removing empty events
def update_empty_events(pvi_json):
    i = 0
    events_list = pvi_json["events"]
    for every_event in events_list:
        if not every_event["reactionCoded"] and not every_event["reportedReaction"]:
            pvi_json["events"][i] = ""
        i += 1
    while "" in pvi_json["events"]:
        pvi_json["events"].remove("")
    i = 1
    for updated_event in pvi_json["events"]:
        updated_event["seq_num"] = i
        i += 1
    return pvi_json


# processing events section
def update_events(pvi_json):
    seriousness_flag = other_serious_criteria(pvi_json)
    event_country = pvi_json["events"][0]["country"]
    if not event_country:
        if pvi_json["reporters"][0]["country"]:
            event_country = pvi_json["reporters"][0]["country"]
    if pvi_json["events"][0]["startDate"]:
        try:
            event_onset = strip_characters(pvi_json["events"][0]["startDate"].replace(" ", ""))
        except:
            event_onset = field_na_checker("") # ask: why we are not passing None value directly
    seriousnes_final = []
    for event in range(len(pvi_json["events"])):
        for every_seriousness in range(len(pvi_json["events"][event]["seriousnesses"])):
            if pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"] == 0:
                pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"] = None
            if pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"] == "Other":
                pvi_json["events"][event]["seriousnesses"][every_seriousness][
                    "value"] = "Other Medically Important Condition"
    for event in range(len(pvi_json["events"])):
        for every_seriousness in range(len(pvi_json["events"][event]["seriousnesses"])):
            if pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"] != None:
                seriousnes_final.append(pvi_json["events"][event]["seriousnesses"][every_seriousness])
    i = 1
    serious_empty = [{'value': None, 'value_acc': 0.95}]

    for event_index in range(len(pvi_json["events"])):
        pvi_json["events"][event_index]["seq_num"] = i
        i += 1
        # coded = pvi_json["events"][event_index]["reactionCoded"]
        reported = pvi_json["events"][event_index]["reportedReaction"]
        # if coded:
        #     try:
        #         pvi_json["events"][event_index]["reactionCoded"] = field_na_checker(strip_characters(coded))
        #     except:
        #         pvi_json["events"][event_index]["reactionCoded"] = field_na_checker("")
        if reported:
            try:
                pvi_json["events"][event_index]["reportedReaction"] = field_na_checker(strip_characters(reported.split("(")[0]))
                # if "(" in pvi_json["events"][event_index]["reportedReaction"] and \
                #         ")" not in pvi_json["events"][event_index]["reportedReaction"]:
                #     pvi_json["events"][event_index]["reportedReaction"] = pvi_json["events"][event_index][
                #                                                               "reportedReaction"] + ")"

            except:
                pvi_json["events"][event_index]["reportedReaction"] = field_na_checker("")
        pvi_json["events"][event_index]["reactionCoded"] = pvi_json["events"][event_index]["reportedReaction"]
    pvi_json = update_empty_events(pvi_json)

    if seriousness_flag == "Yes":
        other_found = False
        for first_seriousness in seriousnes_final:
            if first_seriousness["value"] == "Medically Important":
                other_found = True
        if other_found == False:
            seriousnes_final.append({'value': 'Medically Important', 'value_acc': 0.95})
    if seriousnes_final:
        pvi_json["events"][0]["seriousnesses"] = seriousnes_final
    else:
        pvi_json["events"][0]["seriousnesses"] = serious_empty
    pvi_json["events"][0]["country"] = event_country
    pvi_json["events"][0]["startDate"] = event_onset
    if len(pvi_json["events"]) > 1:
        for event_index in range(1, len(pvi_json["events"])):
            pvi_json["events"][event_index]["seriousnesses"] = serious_empty
    return pvi_json


# processing lab data
def update_labtest(pvi_json):
    for test in pvi_json["tests"]:

        test_seq = test["seq_num"]
        if test_seq:
            test["seq_num"] = field_na_checker(
                re.sub(r'[^\x00-\x7F]+', '', str(test_seq)).replace("\n", " ").replace("#", ""))
        else:
            test["seq_num"] = None

        test_name = test["testName"]
        if test_name:
            test["testName"] = field_na_checker(
                re.sub(r'[^\x00-\x7F]+', '', test_name).replace("\n", " ").replace("Test / Assessment / Notes", ""))
        else:
            test["testName"] = None

        test_result = test["testResult"]
        if test_result:
            test["testResult"] = field_na_checker(
                re.sub(r'[^\x00-\x7F]+', '', test_result).replace("F\n", " ").replace("\n", " ").replace("Results", ""))
        else:
            test["testResult"] = None

        test_date = test["startDate"]
        if test_date:
            test_date = test_date.split("\n")[0]
            test["startDate"] = field_na_checker(
                re.sub(r'[^\x00-\x7F]+', '', test_date).replace("\n", " ").replace("Date", ""))
        else:
            test["startDate"] = None
        if test["testName"]:
            if "Results" in test["testName"]:
                result_in_name = test["testName"].split("Results")
                try:
                    test["testName"] = field_na_checker(strip_characters(result_in_name[0]))
                except:
                    pass
                try:
                    test["testAssessment"] = field_na_checker(strip_characters(result_in_name[1]))
                except:
                    pass
            elif "positive" in test["testName"].lower():
                test_name_po = test["testName"]
                try:
                    result_start_pos = test_name_po.lower().find("positive")
                    test["testName"] = field_na_checker(strip_characters(test_name_po[:result_start_pos - 1]))
                    test["testAssessment"] = field_na_checker(strip_characters(test_name_po[result_start_pos:]))
                except:
                    print("check in positive")
            elif "negative" in test["testName"].lower():
                test_name_po = test["testName"]
                try:
                    result_start_pos = test_name_po.lower().find("negative")
                    test["testName"] = field_na_checker(strip_characters(test_name_po[:result_start_pos - 1]))
                    test["testAssessment"] = field_na_checker(strip_characters(test_name_po[result_start_pos:]))
                except:
                    print("check in negative")
            elif "normal" in test["testName"].lower():
                test_name_po = test["testName"]
                try:
                    result_start_pos = test_name_po.lower().find("normal")
                    test["testName"] = field_na_checker(strip_characters(test_name_po[:result_start_pos - 1]))
                    test["testAssessment"] = field_na_checker(strip_characters(test_name_po[result_start_pos:]))
                except:
                    print("check in negative")
        test_highlow = test["testLow"]
        if test_highlow:
            test_highlow_up = field_na_checker(
                re.sub(r'[^\x00-\x7F]+', '', test_highlow).replace("Normal High / Low", "").replace("High / Low",
                                                                                                    "").replace("N/A",
                                                                                                                "").replace(
                    "\n", ":").replace("/", ":"))
            if test_highlow_up:
                highlow = test_highlow_up.split(":")
                try:
                    test["testLow"] = highlow[1]
                except:
                    test["testLow"] = None
                try:
                    test["testHigh"] = highlow[0]
                except:
                    test["testHigh"] = None
            else:
                test["testLow"] = None
        else:
            test["testLow"] = None
    tests = pvi_json["tests"]
    i = 0
    for every_test in tests:
        if every_test["seq_num"] == None and every_test["testName"] == None and every_test["testResult"] == None and \
                every_test["startDate"] == None and every_test["testHigh"] == None and every_test["testLow"] == None:
            pvi_json["tests"][i] = ""
        i += 1
    while '' in pvi_json["tests"]:
        pvi_json["tests"].remove('')
    i = 1
    for each_lab in pvi_json["tests"]:
        try:
            each_lab["seq_num"] = int(each_lab["seq_num"])
        except:
            print("check in seq num setting for labdata")
    return pvi_json


def num_there(given_string):
    return any(str.isdigit() for str in given_string)


# processing patient name
def patient_name(pvi_json):
    patient = pvi_json["patient"]
    patient_name = pvi_json["patient"]["name"]
    patient_name = re.sub(r'[^A-Za-z0-9 ]+', '', patient_name)
    if patient_name:
        patient_name = patient_name.replace("\n", "")
    if "PRIVACY" in patient_name:
        pvi_json["patient"]["name"] = "UNK"
        return pvi_json

    elif not patient["weight"] and not patient["gender"] and not patient["age"]["inputValue"]:

        pvi_json["patient"]["name"] = "Unknown"
        return pvi_json

    elif patient["patientId"]:
        if patient["patientId"] in patient_name:
            pvi_json["patient"]["name"] = None
            return pvi_json
        else:
            pvi_json["patient"]["name"] = patient_name
            return pvi_json
    else:
        pvi_json["patient"]["name"] = patient_name
        return pvi_json
    return pvi_json


# processing patient weight
def patient_weight(pvi_json):
    weight = pvi_json["patient"]["weight"]
    if weight:
        weight_val = ""
        weight_unit = ""
        try:
            weight = re.sub(r'[^\x00-\x7F]+', '', pvi_json["patient"]["weight"]).replace("\n", " ")
            weight_val = weight.split(" ")[0]
            weight_unit = weight.split(" ")[1]
        except:
            print("check in patient weight")
        if weight_val.lower() not in ["unk", "unknown"]:
            pvi_json["patient"]["weight"] = field_na_checker(weight_val)
        else:
            pvi_json["patient"]["weight"] = None
        weight_unit = field_na_checker(weight_unit)
        if weight_unit:
            pvi_json["patient"]["weightUnit"] = weight_unit + "s" if weight_unit.lower() == "kg" else weight_unit
        else:
            pvi_json["patient"]["weightUnit"] = None  # todo decide weightUnit in case of unknown weight
    return pvi_json


# processing patient age
def patient_age(pvi_json):
    age_dict = pvi_json["patient"]["age"]
    if age_dict["inputValue"]:
        pvi_json["patient"]["age"]["inputValue"] = re.sub(r'[^\x00-\x7F]+', '', age_dict["inputValue"]).replace("\n",
                                                        " ").replace("F", "").replace("M", "").replace("Years","Year").replace("Year", "Years")
        pvi_json["patient"]["age"]["inputValue"] = re.sub("ecades", "Decades", pvi_json["patient"]["age"]["inputValue"]).strip()

        pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"
        pvi_json["patient"]["age"]["inputValue_acc"] = None
        return pvi_json
    elif age_dict["inputValue_acc"]:
        if "PRIVA" in age_dict["inputValue_acc"]:
            pvi_json["patient"]["age"]["inputValue"] = None
            pvi_json["patient"]["age"]["ageType"] = None
            pvi_json["patient"]["age"]["inputValue_acc"] = None
            return pvi_json
        elif pvi_json["reporters"][0]["country"] in ["", None] and pvi_json["patient"]["weight"] in ["", None] and \
                pvi_json["patient"]["age"]["inputValue"] in ["", None] and pvi_json["patient"]["gender"] in ["", None]:
            pvi_json["patient"]["age"]["inputValue"] = strip_characters(
                pvi_json["patient"]["age"]["inputValue_acc"].replace(" ", "").replace("--", "-"))
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_BIRTH_DATE"
            pvi_json["patient"]["age"]["inputValue_acc"] = None
            return pvi_json
    return pvi_json


def patient_gender(pvi_json):
    gender = pvi_json["patient"]["gender"]
    gender = re.sub(r'[^A-Za-z0-9 ]+', "", gender)
    if gender == "":
        pvi_json["patient"]["gender"] = "UNKNOWN"
    elif gender.lower() in ["unk", "unknown"]:
        pvi_json["patient"]["gender"] = "UNKNOWN"
    else:
        pvi_json["patient"]["gender"] = gender
    return pvi_json


"""
def drug_reaction_old(pvi_json, extracted_df):
    rel_history = extracted_df.loc["other relevant history page1"]["value"]
    rel_history_cont = extracted_df.loc["other relevant history last page updated"]["value"]
    final_history = rel_history + rel_history_cont
    final_history_df = pd.DataFrame(final_history)
    final_history_df.columns = ["From/To Dates", "Type of History / Notes", "Description"]
    final_history_df.set_index("Type of History / Notes", inplace=True)
    try:
        rel_history_list = final_history_df.loc["Historical Drug"]["Description"].to_list()
        drug_history = pvi_json["patient"]["pastDrugHistories"]
        idx = 0
        cnt = len(drug_history)
        for i in range(cnt):
            drug_reaction = drug_history[i]["drugReaction"]
            temp_drug_reaction = copy.deepcopy(drug_reaction[0])
            if idx < len(rel_history_list):
                try:
                    reaction = rel_history_list[idx].split("Drug Reaction: ")[1]
                    start_parenthesis = reaction.find("(")
                    reported_reaction =reaction[:start_parenthesis].strip(" ()")
                    reaction_coded = reaction[start_parenthesis+1:].strip(" ()")
                    if reported_reaction:
                        temp_drug_reaction["reportedReaction"]=reported_reaction.replace("\n", "")
                    if reaction_coded:
                        temp_drug_reaction["reactionCoded"] = reaction_coded.replace("\n", "")
                    if temp_drug_reaction:
                        drug_reaction.append(temp_drug_reaction)
                    idx +=1
                except:
                    pass
        pvi_json["patient"]["pastDrugHistories"]=drug_history
    except KeyError:
        pass
    return pvi_json
"""


def drug_reaction(pvi_json, extracted_df):
    rel_history = extracted_df.loc["other relevant history page1"]["value"]
    rel_history_cont = extracted_df.loc["other relevant history last page updated"]["value"]
    final_history = rel_history + rel_history_cont
    final_history_df = pd.DataFrame(final_history)
    final_history_df.columns = ["From/To Dates", "Type of History / Notes", "Description"]
    final_history_df.set_index("Type of History / Notes", inplace=True)
    try:
        try:
            rel_history_list = final_history_df.loc["Historical Drug"]["Description"].to_list()
        except:
            rel_history_list = list()
            rel_history_list.append(final_history_df.loc["Historical Drug"]["Description"])
        drug_history = pvi_json["patient"]["pastDrugHistories"]
        for idx in range(len(rel_history_list)):
            try:
                drug_name = drug_history[idx]["drugReaction"][0]["reportedReaction"]
                drug_name_coded = drug_history[idx]["drugReaction"][0]["reactionCoded"]
                if drug_name:
                    drug_history[idx]["drugName"] = drug_name
                    drug_history[idx]["drugReaction"][0]["reportedReaction"] = None
                if drug_name_coded:
                    drug_history[idx]["drugNameCoded"] = drug_name_coded
                    drug_history[idx]["drugReaction"][0]["reactionCoded"] = None

                reaction = rel_history_list[idx].split("Drug Reaction: ")[1]
                start_parenthesis = reaction.find("(")
                reported_reaction = reaction[:start_parenthesis].strip(" ()")
                # reaction_coded = reaction[start_parenthesis + 1:].strip(" ()")
                reported_reaction = reported_reaction.replace("\n","").strip()
                if reported_reaction:
                    drug_history[idx]["drugReaction"][0]["reportedReaction"] = reported_reaction
                    drug_history[idx]["drugReaction"][0]["reactionCoded"] = reported_reaction

                indication = rel_history_list[idx].split("Drug Indication: ")[1].split("Drug Reaction: ")[0]
                start_parenthesis = indication.find("(")
                indication = indication[:start_parenthesis].strip(" ()")
                indication = indication.replace("\n", "").strip()
                if indication:
                    drug_history[idx]["drugIndication"][0]["reportedReaction"] = indication
                    drug_history[idx]["drugIndication"][0]["reactionCoded"] = indication
            except:
                pass
        pvi_json["patient"]["pastDrugHistories"] = drug_history
    except KeyError:
        pass
    return pvi_json


def get_literature_text(pvi_json, extracted_df):
    flag = extracted_df.loc["literature"]["value"]
    res = list()
    if flag == ["1"]:
        res = list()
        literature = extracted_df.loc["Report_Source_Literature"]["value"]
        for lit in literature:
            if lit.startswith("Journal"):
                try:
                    if curr_dict:
                        res.append(curr_dict)
                except:
                    pass
                curr_dict = dict()
            try:
                line_dict = dict([i.strip().split(":") for i in lit.split("  ")])
                curr_dict = merge_dict(curr_dict, line_dict)
            except:
                curr_dict["Title"] = curr_dict.get("Title") + lit
        res.append(curr_dict)
    return res


def merge_dict(args1, args2):
    res = {**args1, **args2}
    return res


def literatures(pvi_json, extracted_df):
    final_literature = list()
    literature_text = get_literature_text(pvi_json, extracted_df)
    for lit in literature_text:
        literature_json = copy.deepcopy(pvi_json["literatures"][0])
        literature_json["author"] = lit.get("Author", None)
        literature_json["journal"] = lit.get("Journal", None)
        literature_json["pages"] = lit.get("Pages", None)
        literature_json["title"] = lit.get("Title", None)
        literature_json["vol"] = lit.get("Volume", None)
        literature_json["year"] = lit.get("Year", None)
        final_literature.append(literature_json)
    pvi_json["literatures"] = final_literature
    return pvi_json


# main function for processing patient details
def update_patient(pvi_json):
    try:
        pvi_json = patient_name(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = patient_weight(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = patient_age(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = patient_gender(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json


# processing receipt date
def receipt_date(pvi_json, extracted_df):
    initialFlag = True if extracted_df.loc["Initial logic"]["value"][0] == '1' else False
    followupFlag = True if extracted_df.loc["FU_logic"]["value"][0] == '1' else False

    if initialFlag and not followupFlag:
        pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
    elif not initialFlag and followupFlag:
        pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
        pvi_json["receiptDate"] = None

    return pvi_json


# processing refernce type
def referenceType(pvi_json):
    pvi_json["references"][0]["referenceType"] = "LP Case Number"
    return pvi_json


# processing source type
def update_report_source(pvi_json, extracted_df):
    val = pvi_json["project"]
    literatures_checked = ischecked(extracted_df, "literature")
    health_professional_checked = ischecked(extracted_df, "health professional")
    other_checked = ischecked(extracted_df, "report source - other")
    study_checked = ischecked(extracted_df, "study")
    pvi_json["project"] = None
    source_type = pvi_json["sourceType"][0]
    if val:
        if "literature" in val.lower() or literatures_checked:
            source_type["value"] = "literature"
        elif not health_professional_checked and not study_checked and not other_checked and not study_checked and not literatures_checked:
            source_type["value"] = None
        else:
            source_type["value"] = "Spontaneous"
    pvi_json["sourceType"] = [source_type]
    return pvi_json


# processing sendercase version
def sendercase_version(pvi_json):
    if pvi_json["senderCaseVersion"]:
        if "followup" in pvi_json["senderCaseVersion"]:
            # if pvi_json["senderCaseVersion_acc"] and pvi_json["senderCaseVersion_acc"] != "1":
            if pvi_json["senderCaseVersion_acc"]:
                pvi_json["senderCaseVersion"] = int(pvi_json["senderCaseVersion_acc"])+1
            else:
                pvi_json["senderCaseVersion"] = 2
    pvi_json["senderCaseVersion_acc"] = None
    if pvi_json["senderCaseVersion"]:
        pvi_json["senderCaseVersion"] = int(pvi_json["senderCaseVersion"])
    return pvi_json


# processing seriousness criteria
def other_serious_criteria(pvi_json):
    if pvi_json["summary"]["caseDescription_acc"]:
        if "Other Serious Criteria:" in pvi_json["summary"]["caseDescription_acc"]:
            pvi_json["summary"]["caseDescription_acc"] = None
            return "Yes"
    pvi_json["summary"]["caseDescription_acc"] = None
    return "No"


# processing patient study id
def patient_study_id(pvi_json):
    study_id = None
    pat_id = None
    remarks = pvi_json["patient"]["patientId"]
    if remarks:
        pat_id_start_pos = remarks.find("Patient ID:")
        study_id_start_pos = remarks.find("Study ID:")
        center_id_start_pos = remarks.find("Center ID:")
        if pat_id_start_pos != -1:
            if study_id_start_pos != -1:
                pat_id = remarks[pat_id_start_pos + len("Patient ID:"):study_id_start_pos]
            else:
                pat_id = remarks[pat_id_start_pos + len("Patient ID:"):]
        if study_id_start_pos != -1:
            if center_id_start_pos != -1:
                study_id = remarks[study_id_start_pos + len("Study ID:"):center_id_start_pos]
            else:
                study_id = remarks[study_id_start_pos + len("Study ID:"):]
        if pat_id:
            pat_id = pat_id.strip()
        if study_id:
            study_id = study_id.strip()
        pvi_json["patient"]["patientId"] = pat_id
        pvi_json["study"]["studyNumber"] = study_id
    else:
        pvi_json["patient"]["patientId"] = None
    return pvi_json


# processing patient death date
def deathdate(pvi_json):
    deathdate = pvi_json["deathDetail"]["deathDate"]["date"]
    if deathdate:
        res = re.findall(re.compile("^\d{2}-\w*-\d{4}"), deathdate)
        if len(res) > 0:
            pvi_json["deathDetail"]["deathDate"]["date"] = res[0]
        else:
            pvi_json["deathDetail"]["deathDate"]["date"] = None
    return pvi_json


def break_address_into_components(address_str):
    parsed_address_tuple = parse_address(address_str)
    address_dict = {}
    for address_component in parsed_address_tuple:
        address_dict[address_component[1]] = address_component[0]
    for key, val in address_dict.items():
        if key == "country":
            address_dict[key] = val.upper()
        else:
            address_dict[key] = val.title()
    return address_dict


# processing reporter for last page
def reporter_last_page(second_reporter_address, country_list):
    second_reporter_address_list = second_reporter_address.split("\n")
    country_index = []
    start_index = 0
    for country in country_list:
        for indx in range(start_index, len(second_reporter_address_list)):
            if country.lower() in second_reporter_address_list[indx].lower():
                country_index.append(indx)
    adr = {}
    for indx in range(len(country_index)):
        if indx == 0:
            adr[indx] = "\n".join(second_reporter_address_list[0:country_index[indx] + 1])
        elif indx < len(country_index) - 1:
            adr[indx] = "\n".join(second_reporter_address_list[country_index[indx - 1] + 1:country_index[indx]])
        else:
            adr[indx] = "\n".join(second_reporter_address_list[country_index[indx - 1] + 1:])
    return adr


def populate_reporter_name(pvi_json, reporter_index, first_reporter_name):
    if first_reporter_name not in (None, ""):
        first_reporter_name = first_reporter_name.replace("=", "")
        first_reporter_name = first_reporter_name.replace(".", " ")
        first_reporter_name = first_reporter_name.replace(",", " ")
        reportername_parsed = hn(first_reporter_name)
        pvi_json["reporters"][reporter_index]["title"] = field_na_checker(reportername_parsed["title"])
        pvi_json["reporters"][reporter_index]["firstName"] = field_na_checker(reportername_parsed["first"])
        pvi_json["reporters"][reporter_index]["middleName"] = field_na_checker(reportername_parsed["middle"])
        pvi_json["reporters"][reporter_index]["lastName"] = field_na_checker(reportername_parsed["last"])
    pvi_json["reporters"][reporter_index]["givenName"] = None
    return pvi_json


# processing reporter address
def populate_reporter_adr(pvi_json, reporter_address, row_index):
    street = ""
    street = reporter_address.get("house_number", "")
    street = street + " " + reporter_address.get("house", "").strip()
    street = street + " " + reporter_address.get("road", "").strip()
    pvi_json["reporters"][row_index]["street"] = street
    pvi_json["reporters"][row_index]["city"] = reporter_address.get("city", None)
    pvi_json["reporters"][row_index]["state"] = reporter_address.get("state", None)
    pvi_json["reporters"][row_index]["postcode"] = reporter_address.get("postcode", None)
    if "country" in reporter_address.keys():
        if reporter_address["country"]:
            pvi_json["reporters"][row_index]["country"] = reporter_address["country"]
    return pvi_json


def empty_repo():
    reporters = {"reporters": [{
        "country": None,
        "country_acc": None,
        "city": None,
        "city_acc": None,
        "givenName": None,
        "givenName_acc": None,
        "firstName": None,
        "firstName_acc": None,
        "middleName": None,
        "middleName_acc": None,
        "lastName": None,
        "lastName_acc": None,
        "postcode": None,
        "postcode_acc": None,
        "title": None,
        "title_acc": None,
        "street": None,
        "street_acc": None,
        "organization": None,
        "organization_acc": None,
        "occupation": None,
        "occupation_acc": None,
        "qualification": None,
        "qualification_acc": None,
        "state": None,
        "state_acc": None,
        "department": None,
        "department_acc": None,
        "email": None,
        "email_acc": None,
        "telephone": None,
        "fax": None,
        "report_media": None,
        "Intermediary": None,
        "healthAuthorityCaseNumber": None,
        "primary": None
    }]}
    return reporters


# splitting reporters based on country
def reporter_split_based_on_country(pvi_json):
    reporter_address = {}
    country_list = ["afghanistan", "albania", "algeria", "andorra", "angola", "antigua and barbuda", "argentina",
                    "armenia", "australia", "austria", "azerbaijan", "the bahamas", "bahrain", "bangladesh", "barbados",
                    "belarus", "belgium", "belize", "benin", "bhutan", "bolivia", "bosnia and herzegovina", "botswana",
                    "brazil", "brunei", "bulgaria", "burkina faso", "burundi", "cambodia", "cameroon", "canada",
                    "cape verde", "central african republic", "chad", "chile", "china", "colombia", "comoros",
                    "congo, republic of the", "congo, democratic republic of the", "costa rica", "cote d\'ivoire",
                    "croatia", "cuba", "cyprus", "czech republic", "denmark", "djibouti", "dominica",
                    "dominican republic", "east timor (timor-leste)", "ecuador", "egypt", "el salvador",
                    "equatorial guinea", "eritrea", "estonia", "ethiopia", "fiji", "finland", "france", "gabon",
                    "the gambia", "georgia", "germany", "ghana", "greece", "grenada", "guatemala", "guinea",
                    "guinea-bissau", "guyana", "haiti", "honduras", "hungary", "iceland", "india", "indonesia", "iran",
                    "iraq", "ireland", "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan", "kenya",
                    "kiribati", "korea, north", "korea, south", "kosovo", "kuwait", "kyrgyzstan", "laos", "latvia",
                    "lebanon", "lesotho", "liberia", "libya", "liechtenstein", "lithuania", "luxembourg", "macedonia",
                    "madagascar", "malawi", "malaysia", "maldives", "mali", "malta", "marshall islands", "mauritania",
                    "mauritius", "mexico", "micronesia, federated states of", "moldova", "monaco", "mongolia",
                    "montenegro", "morocco", "mozambique", "myanmar (burma)", "namibia", "nauru", "nepal",
                    "netherlands", "new zealand", "nicaragua", "niger", "nigeria", "norway", "oman", "pakistan",
                    "palau", "panama", "papua new guinea", "paraguay", "peru", "philippines", "poland", "portugal",
                    "qatar", "romania", "russia", "rwanda", "saint kitts and nevis", "saint lucia",
                    "saint vincent and the grenadines", "samoa", "san marino", "sao tome and principe", "saudi arabia",
                    "senegal", "serbia", "seychelles", "sierra leone", "singapore", "slovakia", "slovenia",
                    "solomon islands", "somalia", "south africa", "south sudan", "spain", "sri lanka", "sudan",
                    "suriname", "swaziland", "sweden", "switzerland", "syria", "taiwan", "tajikistan", "tanzania",
                    "thailand", "togo", "tonga", "trinidad and tobago", "tunisia", "turkey", "turkmenistan", "tuvalu",
                    "uganda", "ukraine", "united arab emirates", "united kingdom", "united states of america",
                    "uruguay", "uzbekistan", "vanuatu", "vatican city (holy see)", "venezuela", "vietnam", "yemen",
                    "zambia", "zimbabwe"]
    first_reporter_address = pvi_json["literatures"][0]["author"]
    first_reporter_name = ""
    first_reporter = False
    if first_reporter_address and "NAME AND ADDRESS WITHHELD" not in first_reporter_address:
        first_reporter = True
        first_reporter_address = first_reporter_address.replace("25b. NAME AND ADDRESS OF REPORTER", "").replace(
            "(Continued on Additional Information Page)", "").replace("()", "")
        first_reporter_name = first_reporter_address.split("\n")[0]
        for country in country_list:
            cnt = first_reporter_address.lower().find(country)
            if cnt != -1:
                first_reporter_address = first_reporter_address[0:cnt + len(country)]
                break
        if first_reporter_name:
            pvi_json = populate_reporter_name(pvi_json, 0, first_reporter_name)
            first_reporter_address = first_reporter_address.replace(first_reporter_name, "").strip()
        else:
            first_reporter_address = first_reporter_address.strip()
        reporter_address = break_address_into_components(first_reporter_address)
        pvi_json = populate_reporter_adr(pvi_json, reporter_address, 0)
    second_reporter_address_all = pvi_json["literatures"][0]["title"]
    if second_reporter_address_all:
        if "NAME AND ADDRESS WITHHELD" not in second_reporter_address_all:
            second_reporter_address_all = second_reporter_address_all.replace("25b. NAME AND ADDRESS OF REPORTER",
                                                                              "").replace(
                "(Continued on Additional Information Page)", "").replace("()", "").strip()
        if first_reporter:
            reporter_all = [pvi_json["reporters"][0]]
        else:
            reporter_all = []
        lastpage_reporter_adr = reporter_last_page(second_reporter_address_all, country_list)
        for addr in lastpage_reporter_adr.keys():
            if first_reporter_name not in lastpage_reporter_adr[addr]:
                name = lastpage_reporter_adr[addr].split("\n")[0]
                lastpage_addr_all = " ".join(lastpage_reporter_adr[addr].split("\n")[1:])
                address_dict = break_address_into_components(lastpage_addr_all)
                reporter_sec = populate_reporter_name(empty_repo(), 0, name)
                reporter_sec = populate_reporter_adr(reporter_sec, address_dict, 0)
                reporter_all.append(reporter_sec["reporters"][0])
        if reporter_all:
            pvi_json["reporters"] = reporter_all
    pvi_json["literatures"][0]["author"] = None
    pvi_json["literatures"][0]["title"] = None
    return pvi_json


# processing case description
def update_summary(pvi_json):
    if pvi_json["literatures"][0]["digitalObjectIdentifier"]:
        desc1 = pvi_json["literatures"][0]["digitalObjectIdentifier"]
    if pvi_json["literatures"][0]["vol"]:
        desc2 = pvi_json["literatures"][0]["vol"]

    if desc2 and "Case Description:" in desc2:
        case_desc = desc2
    else:
        case_desc = desc1 + desc2

    if case_desc:
        case_desc = re.sub('include generic name.*?Continued on Additional Information Page', '',
                           case_desc, flags=re.DOTALL)
        # case_desc = re.sub('Mfr. Control Number: (\d{2}|\d{1})\-[a-zA-Z]{3}\-\d{4}\s\d{2}\:\d{2}', '', case_desc)
        try:
            while("Mfr. Control Number" in case_desc):
                mfr_start_pos = case_desc.find("Mfr. Control Number")
                case_desc = case_desc.replace(case_desc[mfr_start_pos-12:mfr_start_pos+60],"")
            # case_desc = re.sub('(\d{2}|\d{1})\-[a-zA-Z]{3}\-\d{4}\s\d{2}\:\d{2}','',case_desc)
        except:
            pass
        case_desc = re.sub(r'[^\x00-\x7F]+','',case_desc)
        case_desc = case_desc.replace(
                                "7+13.", "").replace(
                                "include generic name", "").replace(
                                "Continued on Additional Information Page", "").replace(
                                "DESCRIBE REACTION(S) continued", "").replace(
                                "13. Lab Data", "").replace(
                                "II. SUSPECT DRUG(S) INFORMATION", "").replace(
                                "14. SUSPECT DRUG(S)", "").replace(
                                "14-19.", "").replace(
                                "SUSPECT DRUG(S) continued","").replace(
                                "15. DAILY DOSE(S); 18. THERAPY DATES (from/to);", "").replace(
                                "22. CONCOMITANT DRUG(S) AND DATES OF ADMINISTRATION continued", "").replace(
                                "23. OTHER RELEVANT HISTORY  continued", "").replace(
                                "(Continued on Additional Information Page)", "").replace(
                                "ADDITIONAL INFORMATION", "").replace("13. Relevant Tests", "").replace(
                                "DISABILITY OR INCAPACITY", "").replace(
                                "LIFE", "").replace(
                                "CONGENITAL ANOMALY", "").replace(
                                "ANOMALY OTHER", "").replace(
                                "THREATENING", "").replace(
                                "CONGENITAL", "").replace(
                                "INVOLVED PERSISTENT OR SIGNIFICANT", "").replace(
                                "OR SIGNIFICANT", "").replace(
                                "()", "").replace(
                                "OTHER", "")
        case_desc = re.sub(r'[^\x00-\x7F]+', '', case_desc)
        pvi_json["literatures"][0]["vol"] = None                                                                       #change
        pvi_json["literatures"][0]["digitalObjectIdentifier"] = None

        auto_gen_text = "<< PLEASE AUTO GENERATE THE NARRATIVE AS PER NOVONORDISK TEMPLATE >>\n\n"
        pvi_json["summary"]["caseDescription"] = auto_gen_text + case_desc

        if pvi_json["summary"]["caseDescription"]:
            comments_index = pvi_json["summary"]["caseDescription"].find("Causality")
            if comments_index not in [-1]:
                sender_comments = pvi_json["summary"]["caseDescription"][comments_index:]
                pvi_json["summary"]["senderComments"] = sender_comments

    return pvi_json


def valid_date_check(pvi_json):
    for prod in pvi_json['products']:
        for dose in prod['doseInformations']:
            dose['startDate'] = valid_check(dose['startDate'])
            dose['endDate'] = valid_check(dose['endDate'])
    for event in pvi_json['events']:
        event['startDate'] = valid_check(event['startDate'])
    pvi_json['receiptDate'] = valid_check(pvi_json['receiptDate'])
    pvi_json['mostRecentReceiptDate'] = valid_check(pvi_json['mostRecentReceiptDate'])
    for test in pvi_json['tests']:
        test['startDate'] = valid_check(test['startDate'])
    for med_his in pvi_json['patient']['medicalHistories']:
        med_his['startDate'] = valid_check(med_his['startDate'])
        med_his['endDate'] = valid_check(med_his['endDate'])
    for drug_his in pvi_json['patient']['pastDrugHistories']:
        drug_his['startDate'] = valid_check(drug_his['startDate'])
        drug_his['endDate'] = valid_check(drug_his['endDate'])
    return pvi_json


def valid_check(date):
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
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


def seperate_pastdrug_and_medical_history(pvi_json):
    med_his = []
    past_drug = []
    past_drug_history = []
    for history in pvi_json['patient']['medicalHistories']:
        # if "drug" in history['historyNote'].lower():
        if history["historyNote"] and "drug" in history['historyNote'].lower():
            past_drug.append(history)
        else:
            med_his.append(history)
    if med_his:
        pvi_json['patient']['medicalHistories'] = med_his
    if past_drug:
        for each_drug in past_drug:
            drug_copy = copy.deepcopy(pvi_json['patient']['pastDrugHistories'][0])
            if each_drug['reportedReaction']:
                drug_copy['drugReaction'][0]['reportedReaction'] = each_drug['reportedReaction']
            if each_drug['reactionCoded']:
                drug_copy['drugReaction'][0]['reactionCoded'] = each_drug['reactionCoded']
            if each_drug['startDate']:
                drug_copy['startDate'] = each_drug['startDate']
            if each_drug['endDate']:
                drug_copy['endDate'] = each_drug['endDate']
            if each_drug['continuing']:
                drug_copy['continuing'] = each_drug['continuing']
            if each_drug['historyNote']:
                drug_copy['historyNote'] = each_drug['historyNote']
            past_drug_history.append(drug_copy)
        pvi_json['patient']['pastDrugHistories'] = past_drug_history
    return pvi_json


def doseinfo_continuing(pvi_json):
    products = pvi_json['products']
    for idx in range(len(products)):
        doseinfo_len = len(products[idx]["doseInformations"])
        for dose_idx in range(doseinfo_len):
            start_date = products[idx]["doseInformations"][dose_idx]["startDate"]
            end_date = products[idx]["doseInformations"][dose_idx]["endDate"]
            if start_date and re.search("ongoing", start_date.lower(), re.IGNORECASE):
                pvi_json["products"][idx]["doseInformations"][dose_idx]["doseContinuing"] = "Yes"
            elif end_date and re.search("ongoing", end_date.lower(), re.IGNORECASE):
                pvi_json["products"][idx]["doseInformations"][dose_idx]["doseContinuing"] = "Yes"
    return pvi_json


def ischecked(df, annotation):
    return df.loc[annotation]['value'] == ["1"]


def qualification(pvi_json, df):
    if ischecked(df, "health professional") or ischecked(df, "report source - other"):
        reportee = "Other Health professional"
    else:
        reportee = None
    cnt = len(pvi_json["reporters"])
    for idx in range(cnt):
        pvi_json["reporters"][idx]["qualification"] = reportee
    return pvi_json


def get_therapy_dur(pvi_json, extracted_df):
    suspect_fixed = extracted_df.loc["therapy duration_fixed"]["value"]
    suspect_contd = extracted_df.loc["suspect drug  continued"]["value"]
    therapy_dict = dict()
    idx = 0
    for therapy in suspect_fixed:
        match = re.search("\d+", therapy[0])
        if match:
            idx = match.group()
        else:
            idx += 1
        dur = therapy[1].strip(" ()")
        therapy_dict[idx] = list()
        if dur not in therapy_dict[idx]:
            therapy_dict[idx].append(dur)

    for therapy in suspect_contd:
        match = re.search("\d+", therapy[0])
        if match:
            idx = match.group()
        else:
            idx += 1
        dur = therapy[-1].split(";")[1].strip(" \n()").split("\n")[0]


        if idx in therapy_dict.keys() and dur not in therapy_dict[idx]:    #change
        # if dur not in therapy_dict[idx]:  # change

            therapy_dict[idx].append(dur)
        # else:
        #     therapy_dict[idx]=[dur]
    return therapy_dict


def therapy(pvi_json, extracted_df):
    therapy_dict = get_therapy_dur(pvi_json, extracted_df)
    products = pvi_json["products"]
    for prod in products:
        seq = str(prod["seq_num"])
        for idx, dose_info in enumerate(prod["doseInformations"]):
            try:
                dur = therapy_dict.get(seq, None)[idx]
                if dur and dur.lower() != "unknown":
                    dose_info["duration"] = dur
            except:
                pass
    return pvi_json


def dose_continuing(pvi_json):
    products = pvi_json["products"]
    cnt = len(products)
    for idx in range(cnt):
        dose_info = products[idx]["doseInformations"]
        for dose_idx in range(len(dose_info)):
            pvi_json["products"][idx]["doseInformations"][dose_idx]["doseContinuing"] = dose_info[dose_idx]["doseContinuing"]
            if dose_info[dose_idx]["dose_inputValue"]:
                pvi_json["products"][idx]["doseInformations"][dose_idx]["description"] = "Dose: " + dose_info[dose_idx]["dose_inputValue"]
    return pvi_json

""" NEW  """
# def create_pematrix(pvi_json):
#     # rechallenge = pvi_json["productEventMatrix"][0]["rechallenge"]
#     # dechallenge = pvi_json["productEventMatrix"][0]["dechallenge"]
#
#     suspect_no = 0
#     # event,event_list = update_pe_matrix_new(pvi_json)
#     event_no = len(pvi_json["events"])
#     pematrix = []
#     #one_pematrix = pvi_json["productEventMatrix"][0]
#     for prod in pvi_json["products"]:
#         if prod["role_value"] == "Suspect":                                                  #add license_value feild also
#             suspect_no+=1
#     for s_no in range(suspect_no):
#         for e_no in range(event_no):
#             one_pematrix = deepcopy(pvi_json["productEventMatrix"][0])
#             one_pematrix["event_seq_num"] = e_no+1
#             one_pematrix["product_seq_num"] = s_no+1
#             pematrix.append(one_pematrix)
#     pvi_json["productEventMatrix"] = pematrix
#     # return rechallenge, dechallenge, pvi_json
#     return pvi_json
#      #<end > < SJ > < 27 - april - 2022 >
#
#
# def update_pematrix(pvi_json):
#     # rechallenge, dechallenge, pvi_json = create_pematrix(pvi_json)
#     pvi_json = create_pematrix(pvi_json)
#
#     data = pvi_json["summary"]["senderComments"]
#     # pvi_json["summary"]["senderComments"] = None                                                                      #change
#     event_name_list = list()
#
#     event_name_pe = update_pe_matrix_new(pvi_json)
#
#     for event in pvi_json["events"]:
#         event_name_list.append(str(event["seq_num"]) + ":" + event["reportedReaction"])
#
#     code_list = ["Certain", "Not assessed", "Not related", "Possible", "Probable", "Related"
#         , "Unknown", "Unlikely","Not reported"] # Amit 3rd last in ss
#     for event_name in event_name_list:
#         if data:
#             result_value = data.split(event_name.split(":")[1] + ":")[-1].split("\n")[0]
#             result_value = result_value.strip()
#             if not result_value or result_value not in code_list:
#                 try:
#                     result_value = data.split(event_name.split(":")[1])[-2].split("\n")[0]
#                 except:
#                     result_value = None
#
#             if result_value and result_value in code_list:
#                 for ele in pvi_json["productEventMatrix"]:
#                     for event_pe in event_name_pe:
#                         if event_pe and event_pe.lower().strip() in event_name.split(":")[1].lower():
#                             if 'not related' in result_value.lower():
#                                 result_value = "Not Related"
#                             elif 'not reported' in result_value.lower():
#                                 result_value = 'Unknown'
#                             ele["relatednessAssessments"][0]["result"]["value"] = result_value
#                             ele["relatednessAssessments"][0]["source"]["value"] = "Primary Source Reporter"
#
#         # for pe in pvi_json["productEventMatrix"]:
#         #     pe["rechallenge"] = rechallenge
#         #     pe["dechallenge"] = dechallenge
#
#
#     return pvi_json

# def create_pematrix(pvi_json):
#     # rechallenge = pvi_json["productEventMatrix"][0]["rechallenge"]
#     # dechallenge = pvi_json["productEventMatrix"][0]["dechallenge"]
#
#     suspect_no = 0
#     # event,event_list = update_pe_matrix_new(pvi_json)
#     event_no = len(pvi_json["events"])
#     pematrix = []
#     #one_pematrix = pvi_json["productEventMatrix"][0]
#     for prod in pvi_json["products"]:
#         if prod["role_value"] == "Suspect":                                                  #add license_value feild also
#             suspect_no+=1
#     for s_no in range(suspect_no):
#         for e_no in range(event_no):
#             one_pematrix = deepcopy(pvi_json["productEventMatrix"][0])
#             one_pematrix["event_seq_num"] = e_no+1
#             one_pematrix["product_seq_num"] = s_no+1
#             pematrix.append(one_pematrix)
#     pvi_json["productEventMatrix"] = pematrix
#     # return rechallenge, dechallenge, pvi_json
#     return pvi_json
#      #<end > < SJ > < 27 - april - 2022 >
#
#
# def update_pematrix(pvi_json):
#     # rechallenge, dechallenge, pvi_json = create_pematrix(pvi_json)
#     pvi_json = create_pematrix(pvi_json)
#     data = pvi_json["summary"]["senderComments"]
#     pvi_json["summary"]["senderComments"] = None                                                                          #change
#
#     event_name_list = list()
#     event_name_lists = []
#     event_name_lists = update_pe_matrix_new(pvi_json)
#
#     for event in pvi_json['events']:
#         for event_pe in event_name_lists:
#             if event_pe in event["reportedReaction"]:
#                 event_name_list.append(str(event["seq_num"]) + ":" + event["reportedReaction"])
#     # for prod in pvi_json["products"]:
#     #     if "surepost" in prod["license_value"].lower():
#
#
#     code_list = ["Certain", "Not assessed", "Not related", "Possible", "Probable", "Related"
#         , "Unknown", "Unlikely","Not reported"] # Amit 3rd last in ss
#     for event_name in event_name_list:
#         if data:
#             result_value = data.split(event_name.split(":")[1] + ":")[-1].split("\n")[0]
#             result_value = result_value.strip()
#             if not result_value or result_value not in code_list:
#                 try:
#                     result_value = data.split(event_name.split(":")[1])[-2].split("\n")[0]
#                 except:
#                     result_value = None
#
#             if result_value and result_value in code_list:
#                 for ele in pvi_json["productEventMatrix"]:
#                     if ele["event_seq_num"] == int(event_name.split(":")[0]):
#                         if 'not related' in result_value.lower():
#                             result_value = "Not Related"
#                         elif 'not reported' in result_value.lower():
#                             result_value = 'Unknown'
#                         ele["relatednessAssessments"][0]["result"]["value"] = result_value
#                         ele["relatednessAssessments"][0]["source"]["value"] = "Primary Source Reporter"
#
#         # for pe in pvi_json["productEventMatrix"]:
#         #     pe["rechallenge"] = rechallenge
#         #     pe["dechallenge"] = dechallenge
#
#
#     return pvi_json

def create_pematrix(pvi_json):
    # rechallenge = pvi_json["productEventMatrix"][0]["rechallenge"]
    # dechallenge = pvi_json["productEventMatrix"][0]["dechallenge"]

    suspect_no = 0
    event_no = len(pvi_json["events"])
    pematrix = []
    #one_pematrix = pvi_json["productEventMatrix"][0]
    for prod in pvi_json["products"]:
        if prod["role_value"] == "Suspect":
            suspect_no+=1
    for s_no in range(suspect_no):
        for e_no in range(event_no):
            one_pematrix = deepcopy(pvi_json["productEventMatrix"][0])
            one_pematrix["event_seq_num"] = e_no+1
            one_pematrix["product_seq_num"] = s_no+1
            pematrix.append(one_pematrix)
    pvi_json["productEventMatrix"] = pematrix
    # return rechallenge, dechallenge, pvi_json
    return pvi_json


def update_pematrix(pvi_json):
    # rechallenge, dechallenge, pvi_json = create_pematrix(pvi_json)
    pvi_json = create_pematrix(pvi_json)

    data = pvi_json["summary"]["senderComments"]
    pvi_json["summary"]["senderComments"] = None
    event_name_list = list()
    for event in pvi_json["events"]:
        event_name_list.append(str(event["seq_num"]) + ":" + event["reportedReaction"])

    code_list = ["Certain", "Not assessed", "Not related", "Possible", "Probable", "Related"
        , "Unknown", "Unlikely","Not reported"] # Amit 3rd last in ss
    for event_name in event_name_list:
        if data:
            result_value = data.split(event_name.split(":")[1] + ":")[-1].split("\n")[0]
            result_value = result_value.strip()
            if not result_value or result_value not in code_list:
                try:
                    result_value = data.split(event_name.split(":")[1])[-2].split("\n")[0]
                except:
                    result_value = None

            if result_value and result_value in code_list:
                for ele in pvi_json["productEventMatrix"]:
                    if ele["event_seq_num"] == int(event_name.split(":")[0]):
                        if 'not related' in result_value.lower():
                            result_value = "Not Related"
                        elif 'not reported' in result_value.lower():
                            result_value = 'Unknown'
                        ele["relatednessAssessments"][0]["result"]["value"] = result_value
                        ele["relatednessAssessments"][0]["source"]["value"] = "Primary Source Reporter"

        # for pe in pvi_json["productEventMatrix"]:
        #     pe["rechallenge"] = rechallenge
        #     pe["dechallenge"] = dechallenge


    return pvi_json

def remove_junk_casedescription(pvi_json,extracted_df):
    temp = pvi_json['summary']['caseDescription'].split("\n")[-1]
    match = re.search('\d\d-\w\w\w-\d\d\d\d',temp)
    if match:
        removeDate = match.group()
        pvi_json['summary']['caseDescription']=pvi_json['summary']['caseDescription'].replace(temp,"").strip()
    return pvi_json


# def make_regimen_null(pvi_json):
#     for idx in range(len(pvi_json['products'])):
#         pvi_json['products'][idx]['regimen']=None
#     return pvi_json

# def populate_rechallenge_dechalleneg_pematrix(pvi_json, w1_json):
#     rechallenge = None
#     dechallenge = None
#     for i in range(len(w1_json)):
#         if w1_json[i]['AnnotID']=='10086':
#             if w1_json[i]['value'][0]=="1":
#                 dechallenge = 'Positive'
#         if w1_json[i]['AnnotID']=='10087':
#             if w1_json[i]['value'][0]=="1":
#                 dechallenge = 'Negative'
#         if w1_json[i]['AnnotID']=='10089':
#             if w1_json[i]['value'][0]=="1":
#                 rechallenge = 'Positive'
#         if w1_json[i]['AnnotID']=='10091':
#             if w1_json[i]['value'][0]=='1':
#                 rechallenge = 'Negative'
#         if w1_json[i]['AnnotID']=='10092':
#             if w1_json[i]['value'][0]=='1':
#                 rechallenge = 'N/A'
#         if w1_json[i]['AnnotID']=='10094':
#             if w1_json[i]['value'][0]=="1":
#                 dechallenge = 'N/A'
#
#     for idx in range(len(pvi_json['productEventMatrix'])):
#         pvi_json['productEventMatrix'][idx]['dechallenge']['value'] = dechallenge
#         pvi_json['productEventMatrix'][idx]['rechallenge']['value'] = rechallenge
#     return pvi_json

# def populate_patient_age(pvi_json, w1_json):
#     if "year" in pvi_json['patient']['age']['inputValue'].lower():
#         pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"
#         pvi_json['patient']['patientDob'] = None
#     else:
#         pvi_json["patient"]["age"]["ageType"] = "PATIENT_AGE_GROUP"
#         if pvi_json["patient"]["age"]["inputValue"] and pvi_json["patient"]["age"]["inputValue"].lower() not in ['unk','unknown']:
#             pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue_acc"]
#             pvi_json['patient']['patientDob'] = pvi_json["patient"]["age"]["inputValue"]
#         else:
#             pvi_json['patient']['patientDob'] = None
#             pvi_json["patient"]["age"]["inputValue"] = None
#     pvi_json["patient"]["age"]["inputValue_acc"] = None
#     return pvi_json

# def calculate_age_using_dob(pvi_json):
#     if pvi_json['patient']['patientDob'] and pvi_json['events'][0]['startDate']:
#         month_patient = pvi_json['patient']['patientDob'].split('-')[1]
#         month_event = pvi_json['events'][0]['startDate'].split('-')[1]
#
#     return pvi_json
#

def populate_age(pvi_json, w1_json):
    pvi_json['patient']['patientDOB'] = None
    if pvi_json['patient']['age']['inputValue'] and 'year' in pvi_json['patient']['age']['inputValue'].lower():
        pvi_json['patient']['patientDOB'] = pvi_json['patient']['age']['inputValue_acc']
    elif pvi_json['patient']['age']['inputValue_acc'] and '-' in pvi_json['patient']['age']['inputValue_acc']:
        pvi_json['patient']['patientDOB'] = pvi_json['patient']['age']['inputValue_acc']
        pvi_json['patient']['age']['inputValue_acc'] = None
        year_dob = strip_characters(pvi_json['patient']['patientDOB'].split('-')[-1])
        if pvi_json['events'][0]['startDate']:
            year_event = strip_characters(pvi_json['events'][0]['startDate'].split('-')[-1])
        pvi_json['patient']['age']['inputValue'] = str(abs(int(year_event) - int(year_dob))) + ' Years'
    return pvi_json

def populate_seriousness_value(pvi_json, w1_json):
    for idx in range(len(w1_json)):
        if w1_json[idx]['AnnotID'] == '10063':
            if 'intervention required' in w1_json[idx]['value'][0].lower():
                pvi_json['events'][0]['seriousnesses'].append({'value': 'Intervention Required', 'value_acc': 0.95})
            # if 'medically important' in w1_json[idx]['value'][0].lower():
            #     pvi_json['events'][0]['seriousnesses'].append({'value': 'Medically important', 'value_acc': 0.95})
            # if 'ime' in w1_json[idx]['value'][0].lower():
            #     pvi_json['events'][0]['seriousnesses'].append({'value': 'Medically important', 'value_acc': 0.95})
            # if 'important medical event' in w1_json[idx]['value'][0].lower():
            #     pvi_json['events'][0]['seriousnesses'].append({'value': 'Medically important', 'value_acc': 0.95})

    return pvi_json


def remove_duplicate_events(pvi_json, w1_json):
    event_reaction = []
    index_list = []
    for idx in range(len(pvi_json['events'])):
        if pvi_json['events'][idx]['reactionCoded'] not in event_reaction:
            event_reaction.append(pvi_json['events'][idx]['reactionCoded'])
        else:
            # pvi_json['events'].remove(pvi_json['events'][event])
            index_list.append(idx)
    if index_list:
        for idx in index_list:
            pvi_json['events'].remove(pvi_json['events'][idx])

        for idx in range(len(pvi_json['events'])):
            pvi_json['events'][idx]['seq_num'] = idx + 1
    return pvi_json


# #processing sendercase version
# def sendercase_version(pvi_json):
#     if pvi_json["senderCaseVersion"]:
#         if "followup" in pvi_json["senderCaseVersion"]:
#             if pvi_json["senderCaseVersion_acc"] and pvi_json["senderCaseVersion_acc"]!="1":
#                 pvi_json["senderCaseVersion"] = pvi_json["senderCaseVersion_acc"]
#             else:
#                 pvi_json["senderCaseVersion"] = 2
#     pvi_json["senderCaseVersion_acc"] = None
#     if pvi_json["senderCaseVersion"]:
#         pvi_json["senderCaseVersion"] = int(pvi_json["senderCaseVersion"])
#     return pvi_json

# def update_pematrix_new(pvi_json, w1_json):
#     sample_list = pvi_json['literatures'][0]['vol'].split("\n")
#     return sample_list

def patient_age_unknown(pvi_json):
    if pvi_json['patient']['age']['inputValue'] and pvi_json['patient']['age']['inputValue'].lower() in ['unk u','unknown']:
        pvi_json['patient']['age']['inputValue'] = None
    if pvi_json['patient']['age']['inputValue'] and pvi_json['patient']['age']['inputValue'].lower() in ['unk','unknown']:
        pvi_json['patient']['age']['inputValue'] = None
    return pvi_json


#
# def update_pe_matrix_new(pvi_json):
#     data = pvi_json["summary"]["senderComments"]
#     data_split = data.split("Causality")
#     event_list = []
#     event_name_list = []
#     sample_matrix = deepcopy(pvi_json["productEventMatrix"][0])
#     pe_matrix = []
#     for idx in range(len(data_split)):
#         if "surepost" in data_split[-idx].lower():
#             event_list = data_split[-idx].split("\n")[1:]
#     # for idx in range(len(event_list)):
#     #     event_name_list.append(event_list[idx].split(":")[0])
#     #
#     # event_name_list.remove(' ')
#     return event_name_list

def update_pe_matrix_new(pvi_json):
    data = pvi_json["summary"]["senderComments"]
    res = []
    result = []
    data_split = data.split("Reporter's comments:")[-1]
    data_split = data_split.split("[Additional information received")[0].split("Causality")
    for idx in range(len(data_split)):
        if "" in data_split[idx].split(":")[0]:
            result.append(data_split[idx])
    for idx in range(len(data_split)):
        if "surepost" in data_split[idx].lower():
            result.append(data_split[idx])

    # for event in pvi_json["events"]:
    #     result.append(data.split(event["reportedReaction"] + ":")[-1].split("\n"))

    return pvi_json

def populate_country(pvi_json):
    for i in range(len(pvi_json["events"])):
        if pvi_json["events"][i]["country"]:
            if "united states" in pvi_json["events"][i]["country"].lower() or "usa" in pvi_json["events"][i]["country"].lower():
                pvi_json["events"][i]["country"] = "United States Of America"
    for i in range(len(pvi_json["reporters"])):
        if pvi_json["reporters"][i]["country"]:
            if "united states" in pvi_json["reporters"][i]["country"].lower() or "usa" in pvi_json["events"][i]["country"].lower():
                pvi_json["reporters"][i]["country"] = "United States Of America"
    return pvi_json
def products_ing_con(pvi_json):
    strength=pvi_json['products'][0]['ingredients'][0]['strength']
    pvi_json['products'][0]['concentration'][0]['value']=strength

    return pvi_json

def get_postprocessed_json(pvi_json, w1_json):
    extracted_df = pd.DataFrame(w1_json)
    extracted_df.set_index('class', inplace=True)
    print(extracted_df)
    print("inside postprocessing...")
    try:
        pvi_json = update_labtest(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = patient_study_id(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_patient(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = postprocess_products(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = receipt_date(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = referenceType(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_report_source(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = sendercase_version(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_events(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = deathdate(pvi_json)
    except:
        traceback.print_exc()

    # try:
    #     sample = update_pematrix_new(pvi_json,w1_json)
    # except:
    #     traceback.print_exc()


    try:
        pvi_json = reporter_split_based_on_country(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_pat_med_his(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_summary(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = doseinfo_continuing(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = valid_date_check(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = seperate_pastdrug_and_medical_history(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = set_indication_suspect(pvi_json, extracted_df)
    except:
        traceback.print_exc()
        pass
    try:
        pvi_json = set_concomitant_continues(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = drug_reaction(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = literatures(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = qualification(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = therapy(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = dose_continuing(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = update_pematrix(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json["relevantTests_acc"] = None
    except:
        traceback.print_exc()
    try:
        pvi_json = remove_junk_casedescription(pvi_json,extracted_df)
    except:
        traceback.print_exc()
    # try:
    #     pvi_json = make_regimen_null(pvi_json)
    # except:
    #     traceback.print_exc()
    # try:
    #     pvi_json = populate_rechallenge_dechalleneg_pematrix(pvi_json,w1_json)
    # except:
    #     traceback.print_exc()
    # try:
    #     pvi_json = populate_age(pvi_json,w1_json)
    # except:
    #     traceback.print_exc()
    # try:
    #     pvi_json = populate_patient_age(pvi_json,w1_json)
    # except:
    #     traceback.print_exc()
    # try:
    #     pvi_json = calculate_age_using_dob(pvi_json)
    # except:
    #     traceback.print_exc()
    try:
        pvi_json = populate_age(pvi_json,w1_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = populate_seriousness_value(pvi_json,w1_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = remove_duplicate_events(pvi_json,w1_json)
    except:
        traceback.print_exc()
    # try:
    #     update_pematrix_new(pvi_json,w1_json)
    # except:
    #     traceback.print_exc()

    try:
        pvi_json = patient_age_unknown(pvi_json)
    except:
        traceback.print_exc()
    # try:
    #     pvi_json = update_pe_matrix_new(pvi_json)
    # except:
    #     traceback.print_exc()

    try:
        pvi_json = populate_country(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json=products_ing_con(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json


# extracted_json = json.load(open('/home/rxlogix/Downloads/postprocessing/novo-cioms/SI_inter.json')) # remove
# pvi_json = json.load(open('/home/rxlogix/Downloads/postprocessing/novo-cioms/SI_post0.json')) # remove
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_json))) # removemedical

#
# extracted_json = json.load(open('/home/lt-gandharvp/backendservice/utility/template/form_configurations/postprocessing/cn_seriousFU_intermediate.json')) # remove
# pvi_json = json.load(open('/home/lt-gandharvp/backendservice/utility/template/form_configurations/postprocessing/cn_seriousFU_output.json')) # remove
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_json))) # remove