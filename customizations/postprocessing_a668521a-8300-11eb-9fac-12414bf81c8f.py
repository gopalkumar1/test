import re
from postal.parser import parse_address
from nameparser import HumanName as hn

'''
import json
mapping_file = "/home/akshatha/Desktop/SJN_without_post.json"
with open(mapping_file) as json_file:
    pvi_json = json.load(json_file)
'''

#check None type
def field_na_checker(inp_string):
    if inp_string=="" or inp_string==None:
        return None
    else:
        return inp_string

#segregate products based on role of products
def role_value_based_prod_seperation(pvi_json):
    suspect_prods = []
    concom_prods = []
    suspect_first = []
    concom_first = []
    for every_prod in pvi_json["products"]:
        if every_prod["license_value"] != None and every_prod["role_value"] == "Suspect":
            suspect_prods.append(every_prod)
        if every_prod["license_value"] != None and every_prod["role_value"] == "Concomitant":
            concom_prods.append(every_prod)
        if every_prod["license_value"] != None and every_prod["role_value"] == "Suspect_first":
            suspect_first.append(every_prod)
        if every_prod["license_value"] != None and every_prod["role_value"] == "Concomitant_first":
            concom_first.append(every_prod)
    return suspect_prods, concom_prods, suspect_first, concom_first

#remove extra characters
def strip_characters(inp_string):
    try:
        if inp_string:
            try:
                inp_string = re.sub(r'[^\x00-\x7F]+','',inp_string)
            except:
                pass
        if inp_string != None:
            out_string = inp_string.strip(" { } ( ) \ / ; . [ ] , - : ")
        else:
            return inp_string
    except:
        out_string = inp_string
    return out_string

#extract regex match
def regex_match(pattern, text):
    matched_data = re.search(pattern, text)
    if matched_data == None:
        value = ""
    else:
        value = matched_data.group()
    return value

#processing products data
def preprocess_productdata(pvi_json):
    for every_prod in pvi_json["products"]:
        if every_prod["role_value"] == "Suspect_first" and every_prod["license_value"]!=None:
            try:
                every_prod["seq_num"] = re.search("\d", str(every_prod["seq_num"]))
                if every_prod["seq_num"] == None:
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
                    dose_temp["continuing"] = None
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
                coded_form = ["",""]
                if every_prod["license_value"]:
                    try:
                        license_reported = strip_characters(regex_match("[)].*[(]", every_prod["license_value"].rstrip("()")))
                    except:
                        license_reported = field_na_checker("")
                    try:
                        license_coded_form = strip_characters(regex_match("[(].*,|[(].*", every_prod["license_value"]))
                        coded_form = license_coded_form.split(")")
                    except:
                        coded_form = ["",""]
                every_prod["license_value"] = None
                liscense_coded = field_na_checker(coded_form[0])
                try:
                    formulation = field_na_checker(strip_characters(coded_form[1]))
                except:
                    formulation = field_na_checker("")
                if liscense_coded not in [None, ""]:
                    if "codenotbroken" not in "".join(liscense_coded.split()).lower()  :
                        every_prod["license_value"] = field_na_checker(liscense_coded)
                    elif "Blinded" in license_reported and license_reported not in [None, ""]:
                        every_prod["license_value"] = field_na_checker(strip_characters(license_reported.strip("Blinded")))
                    else:
                        every_prod["license_value"] = field_na_checker(license_reported)
                if formulation:
                    formulation = re.sub(r'[^\x00-\x7F]+','',formulation)
                    every_prod["dosageForm_value"] = field_na_checker(formulation)
            except:
                print("check in suspect first")
                pass
        elif every_prod["role_value"] == "Concomitant_first" and every_prod["license_value"]!=None:
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
                    dose_form_cf = liscense_coded_cf.split(")")[1].strip()
                except:
                    dose_form_cf = field_na_checker("")
                every_prod["dosageForm_value"] = None
                try:
                    dose_date_cf = ""
                    if every_prod["regimen"]:
                        dose_date_cf = strip_characters(every_prod["regimen"]).replace("(Continued on Additional Information Page)","")
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
                    start_date_cf = field_na_checker("")
                try:
                    end_date_cf = ""
                    end_date_cf = strip_characters(start_end_date_cf.split("/")[1])
                except:
                    end_date_cf = field_na_checker("")
                if liscense_coded_up_cf not in [None, ""]:
                    if "codenotbroken" not in "".join(liscense_coded_up_cf.split()).lower():
                        every_prod["license_value"] = field_na_checker(liscense_coded_up_cf)
                    elif "Blinded" in liscense_reported_cf and liscense_reported_cf not in [None, ""]:
                        every_prod["license_value"] = field_na_checker(liscense_reported_cf.strip("Blinded"))
                    else:
                        every_prod["license_value"] = field_na_checker(liscense_reported_cf)
                every_prod["dosageForm_value"] = field_na_checker(dose_form_cf)
                every_prod["doseInformations"][0]["startDate"] = field_na_checker(start_date_cf)
                if "Ongoing" in end_date_cf:
                    every_prod["doseInformations"][0]["endDate"] = "Ongoing"
                else:
                    every_prod["doseInformations"][0]["endDate"] = field_na_checker(end_date_cf)
            except:
                print("check in concom first")
        elif every_prod["role_value"] == "Concomitant" and every_prod["license_value"]!=None:
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
                dose_date_cl = strip_characters(every_prod["regimen"].replace("23. OTHER RELEVANT HISTORY  continued",""))
                if "Case Version" in dose_date_cl:
                    try:
                        footer_start_pos = dose_date_cl.find("Case Version")
                        dose_date_cl = dose_date_cl[:footer_start_pos-18]
                    except:
                        pass
                every_prod["regimen"] = None
                try:
                    start_end_date = strip_characters(dose_date_cl.split("&")[0])
                    start_date_cl = ""
                    start_date_cl = strip_characters(start_end_date.split("/")[0])
                except:
                    print("check in cf start date")
                    pass
                try:
                    end_date_cl = ""
                    end_date_cl = strip_characters(start_end_date.split("/")[1])
                except:
                    print("check in cf start date")
                    pass
                if liscense_coded_up_cl not in ["", None]:
                    if "codenotbroken" not in "".join(liscense_coded_up_cl.split()).lower():
                        every_prod["license_value"] = field_na_checker(liscense_coded_up_cl)
                    elif "Blinded" in liscense_reported_cl and liscense_reported_cl not in [None, ""]:
                        every_prod["license_value"] = field_na_checker(liscense_reported_cl.strip("Blinded"))
                    else:
                        every_prod["license_value"] = field_na_checker(liscense_reported_cl)
                every_prod["dosageForm_value"] = field_na_checker(dose_form_cl)
                every_prod["doseInformations"][0]["startDate"] = field_na_checker(start_date_cl)
                if "Ongoing" in end_date_cl:
                    every_prod["doseInformations"][0]["endDate"] = "Ongoing"
                else:
                    every_prod["doseInformations"][0]["endDate"] = field_na_checker(end_date_cl)
            except:
                print("check in concom last page")
        elif every_prod["role_value"] == "Suspect" and every_prod["license_value"]!=None:
            try:
                try:
                    licence_val = strip_characters(every_prod["license_value"].replace("14-19. SUSPECT DRUG(S) continued","").replace("\n"," "))
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
                liscence_coded_sl = liscence_coded_sl.replace("  "," ")
                try:
                    liscence_form_sl = liscense_coded_form_sl.split(")")[-1]
                except:
                    liscence_form_sl = None
                if liscence_coded_sl not in ["", None]:
                    if "codenotbroken" not in "".join(liscence_coded_sl.split()).lower():
                        every_prod["license_value"] = field_na_checker(liscence_coded_sl)
                    elif liscense_reported_sl not in [None, ""] and "Blinded" in liscense_reported_sl:
                        every_prod["license_value"] = field_na_checker(liscense_reported_sl.strip("Blinded"))
                    else:
                        every_prod["license_value"] = field_na_checker(liscense_reported_sl)
                if every_prod["dosageForm_value"]:
                    dosageForm_value = every_prod["dosageForm_value"].replace("\n","")
                every_prod["dosageForm_value"] = None
                dose_freq = regex_match("^.*;", dosageForm_value)
                
                try:
                    if not("Blinded".lower() in dose_freq.lower()):
                        if "," in dose_freq:
                            comma_index = dose_freq.find(",")
                            comma_dose = dose_freq[:comma_index]
                            comma_freq = dose_freq[comma_index:]
                            every_prod["doseInformations"][0]["dose_inputValue"] = field_na_checker(strip_characters(comma_dose))
                            #if len(dose_freq.split(","))>1:
                            every_prod["doseInformations"][0]["frequency_value"] = field_na_checker(strip_characters(comma_freq))
                        else:
                            dose_freq = dose_freq.split(" ")
                            if len(dose_freq) > 1:
                                every_prod["doseInformations"][0]["dose_inputValue"] = field_na_checker(strip_characters(dose_freq[0] + " " + dose_freq[1]))
                            if len(dose_freq) >=3:
                                freq_val = ' '.join([str(v) for v in dose_freq[2:]])
                                every_prod["doseInformations"][0]["frequency_value"] = field_na_checker(strip_characters(freq_val))
                    if every_prod["doseInformations"][0]["dose_inputValue"]:
                        if "(" in every_prod["doseInformations"][0]["dose_inputValue"] and ")" not in every_prod["doseInformations"][0]["dose_inputValue"]:
                            every_prod["doseInformations"][0]["dose_inputValue"] = every_prod["doseInformations"][0]["dose_inputValue"] + ")"
                    every_prod["dosageForm_value"] = field_na_checker(strip_characters(liscence_form_sl))
                except:
                    pass
                '''
                try:
                    every_prod["doseInformations"][0]["dose_inputValue"] = field_na_checker(strip_characters(dose_freq.split(",")[0]))
                    if len(dose_freq.split(","))>1:
                        every_prod["doseInformations"][0]["frequency_value"] = field_na_checker(strip_characters(dose_freq.split(",")[1]))
                    every_prod["dosageForm_value"] = field_na_checker(strip_characters(liscence_form_sl))
                except:
                    pass
                '''
                dosageForm_value = re.sub(r'[^\x00-\x7F]+','',dosageForm_value)
                dosageForm_value = dosageForm_value.replace("\n", " ")
                dosageForm_value = dosageForm_value.replace("NISTRATION continued","")
                form = strip_characters(regex_match(";.*", dosageForm_value))
                every_prod["doseInformations"][0]["route_value"] = field_na_checker(form)
                dose_date = every_prod["regimen"].replace("\n", " ")
                every_prod["regimen"] = None
                try:
                    every_prod["doseInformations"][0]["startDate"] = field_na_checker(strip_characters(dose_date.split("/")[0].strip().split(" ")[0]))
                except:
                    every_prod["doseInformations"][0]["startDate"] = None
                    print("error in start date suspect last page")
                try:
                    end_date_sl = dose_date.split("/")[1].strip().split(" ")[0]
                    if "Ongoing" in end_date_sl:
                        every_prod["doseInformations"][0]["endDate"]= "Ongoing"
                    else:
                        every_prod["doseInformations"][0]["endDate"] =  field_na_checker(strip_characters(end_date_sl))
                except:
                    every_prod["doseInformations"][0]["endDate"] = None
                    print("check in end date suspect last page")
            except:
                print("check in suspect last page")
    return pvi_json, dose_dict
    
#first page suspect products dose information mapping
def first_suspect_dose(prod, dose_dict):
    if dose_dict["dose"]:
        dose_info =  dose_dict["dose"].split("||")
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
                        comma_freq = dose_freq[comma_index:]
                        dose_val = field_na_checker(strip_characters(comma_dose))
                        freq_val = field_na_checker(strip_characters(comma_freq))
                    else:
                        dose_freq = dose_freq.split(" ")
                        if len(dose_freq) > 1:
                            dose_val = field_na_checker(strip_characters(dose_freq[0] + " " + dose_freq[1]))
                        if len(dose_freq) >=3:
                            freq_val_before = ' '.join([str(v) for v in dose_freq[2:]])
                            freq_val = field_na_checker(strip_characters(freq_val_before))
                #if len(split_dose) == 2:
                #    only_dose = dose_val.split(" ")
                #    if len(only_dose) > 1:
                #        dose_val = only_dose[0] + " " + only_dose[1]
                #    if len(only_dose) >=3:
                #        freq_val = ' '.join([str(v) for v in only_dose[2:]])
                #elif len(split_dose)>2:
                #    freq_val = strip_characters(split_dose[2])  
            except:
                pass
            for every_prod_dose in prod:
                if every_prod_dose["role_value"] == "Suspect_first" and every_prod_dose["seq_num"] == seq_num_dose:
                    every_prod_dose["doseInformations"][0]["dose_inputValue"] = field_na_checker(dose_val)
                    every_prod_dose["doseInformations"][0]["frequency_value"] = field_na_checker(freq_val)
                    if every_prod_dose["doseInformations"][0]["dose_inputValue"]:
                        if "(" in every_prod_dose["doseInformations"][0]["dose_inputValue"] and ")" not in every_prod_dose["doseInformations"][0]["dose_inputValue"]:
                            every_prod_dose["doseInformations"][0]["dose_inputValue"] = every_prod_dose["doseInformations"][0]["dose_inputValue"] + ")"
    if dose_dict["route"]:
        route_info =  dose_dict["route"].split("||")
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
                    every_prod_dose["doseInformations"][0]["route_value"] = field_na_checker(route_val)
    if dose_dict["start_date"]:
        dates_info =  dose_dict["start_date"].split("||")
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
                    every_prod_dose["doseInformations"][0]["startDate"] = field_na_checker(start_date)
                    every_prod_dose["doseInformations"][0]["endDate"] = field_na_checker(end_date)
    if dose_dict["indication"]:
        indication_info =  dose_dict["indication"].split("||")
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
            if seq_num_indication == None:
                seq_num_indication = "0"
            else:
                seq_num_indication = seq_num_indication.group()
            for every_prod_dose in prod:
                if every_prod_dose["role_value"] == "Suspect_first" and every_prod_dose["seq_num"] == seq_num_indication:
                    every_prod_dose["indications"][0]["reportedReaction"] = field_na_checker(reported_val)
                    every_prod_dose["indications"][0]["reactionCoded"] = field_na_checker(coded_val)
    return prod
                
#merging dose information for repeting products
def merge_dose_info(products):
    prod_list = []
    for every_prod in products:
        check_flag = False
        for prod_in_list in prod_list:
            if every_prod["seq_num"] == prod_in_list["seq_num"]:
                check_flag = True
                if prod_in_list["doseInformations"][-1]["startDate"] == every_prod["doseInformations"][0]["startDate"] and prod_in_list["doseInformations"][-1]["endDate"] == every_prod["doseInformations"][0]["endDate"] and prod_in_list["doseInformations"][-1]["continuing"] == every_prod["doseInformations"][0]["continuing"]:
                    pass
                else:
                    prod_in_list["doseInformations"].extend(every_prod["doseInformations"])
                break
        if check_flag == False:
            prod_list.append(every_prod)
    return prod_list

#updating role type to suspect and concom
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

#updating product seq num         
def process_seqnum_to_int(pvi_json):
    seq = 1
    for every_prod in pvi_json["products"]:
        every_prod["seq_num"] = seq
        seq+=1
    return pvi_json

#main function for processing products
def postprocess_products(pvi_json):
    pvi_json, first_suspect_dose_dict = preprocess_productdata(pvi_json)
    suspect_prods, concom_prods, suspect_first, concom_first = role_value_based_prod_seperation(pvi_json)
    suspect_first = first_suspect_dose(suspect_first, first_suspect_dose_dict)
    suspect_first.extend(suspect_prods)
    concom_first.extend(concom_prods)
    suspect_first = merge_dose_info(suspect_first)
    concom_first = merge_dose_info(concom_first)
    suspect_first.extend(concom_first)
    products = change_continued_page_role_type(suspect_first)
    pvi_json["products"] = products
    pvi_json = process_seqnum_to_int(pvi_json)
    return pvi_json

#processing patient medical history
def update_pat_med_his(pvi_json):
    for every_med_his in pvi_json["patient"]["medicalHistories"]:
        try:
            reported_coded = field_na_checker(every_med_his["reportedReaction"].replace("23. OTHER RELEVANT HISTORY  contin","").replace("Description",""))
        except:
            reported_coded = every_med_his["reportedReaction"]
        every_med_his["reportedReaction"] = None
        if reported_coded:
            reported = ""
            coded = ""
            try:
                reported = strip_characters(reported_coded.split("(")[0])
                reported = re.sub(r'[^\x00-\x7F]+','',reported).replace("\n", " ")
                every_med_his["reportedReaction"] = field_na_checker(strip_characters(reported))
            except:
                print("check in med his 1")
            try:
                coded = regex_match("[(].*[)]", reported_coded)
                coded = re.sub(r'[^\x00-\x7F]+','',coded).replace("\n", " ")
                every_med_his["reactionCoded"] = field_na_checker(strip_characters(coded))
            except:
                print("check in med his 2")
        try:
            dates = field_na_checker(every_med_his["startDate"].replace("From/To Dates",""))
        except:
            print("check in med his 3")
            dates = every_med_his["startDate"]
        every_med_his["startDate"] = None
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
            history = field_na_checker(every_med_his["historyNote"].replace("Type of History / Notes",""))
        except:
            history = every_med_his["historyNote"]
        if history:
            every_med_his["historyNote"] = re.sub(r'[^\x00-\x7F]+','',history).replace("\n", " ")
        else:
            every_med_his["historyNote"] = field_na_checker("")
    i = 0
    med_his_list = pvi_json["patient"]["medicalHistories"]
    for every_his in med_his_list:
        if not every_his["reportedReaction"] and not every_his["reactionCoded"] and not every_his["startDate"] and not every_his["endDate"] and not every_his["historyNote"] :
            pvi_json["patient"]["medicalHistories"][i] = ""
        i+=1
    while "" in pvi_json["patient"]["medicalHistories"]:
        pvi_json["patient"]["medicalHistories"].remove("") 
    return pvi_json

#removing empty events
def update_empty_events(pvi_json):
    i = 0
    events_list = pvi_json["events"]
    for every_event in events_list:
        if not every_event["reactionCoded"] and not every_event["reportedReaction"] :
            pvi_json["events"][i] = ""
        i+=1
    while "" in pvi_json["events"]:
        pvi_json["events"].remove("")
    i=1
    for updated_event in pvi_json["events"]:
        updated_event["seq_num"] = i
        i+=1
    return pvi_json

#processing events section
def update_events(pvi_json, seriousness_flag):
    event_country = pvi_json["events"][0]["country"]
    if not event_country:
        if pvi_json["reporters"][0]["country"]:
            event_country = pvi_json["reporters"][0]["country"]
    if pvi_json["events"][0]["startDate"]:
        try:
            event_onset = strip_characters(pvi_json["events"][0]["startDate"].replace(" ",""))
        except:
            event_onset = field_na_checker("")
    seriousnes_final = []
    for event in range(len(pvi_json["events"])):
        for every_seriousness in range(len(pvi_json["events"][event]["seriousnesses"])):
            if pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"]==0:
                pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"] = None
            if pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"]=="Other":
                pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"] = "Other Medically Important Condition"
    for event in range(len(pvi_json["events"])):
        for every_seriousness in range(len(pvi_json["events"][event]["seriousnesses"])):
            if pvi_json["events"][event]["seriousnesses"][every_seriousness]["value"]!=None:
                seriousnes_final.append(pvi_json["events"][event]["seriousnesses"][every_seriousness])
    i = 1
    serious_empty = [{'value': None, 'value_acc': 0.95}]
    for event_index in range(len(pvi_json["events"])):
        pvi_json["events"][event_index]["seq_num"] = i
        i+=1
        coded = pvi_json["events"][event_index]["reactionCoded"]
        reported = pvi_json["events"][event_index]["reportedReaction"]
        if coded:
            try:
                pvi_json["events"][event_index]["reactionCoded"] = field_na_checker(strip_characters(coded))
            except:
                pvi_json["events"][event_index]["reactionCoded"] = field_na_checker("")
        if reported:
            try:
                pvi_json["events"][event_index]["reportedReaction"] = field_na_checker(strip_characters(reported))
                if "(" in pvi_json["events"][event_index]["reportedReaction"] and ")" not in pvi_json["events"][event_index]["reportedReaction"]:
                    pvi_json["events"][event_index]["reportedReaction"] = pvi_json["events"][event_index]["reportedReaction"] + ")"
            except:
                pvi_json["events"][event_index]["reportedReaction"] = field_na_checker("")
    pvi_json = update_empty_events(pvi_json)
    if seriousness_flag == "Yes":
        other_found = False
        for first_seriousness in seriousnes_final:
            if first_seriousness["value"] == "Other Medically Important Condition":
                other_found = True
        if other_found== False:
            seriousnes_final.append({'value': 'Other Medically Important Condition', 'value_acc': 0.95})
    if seriousnes_final:
        pvi_json["events"][0]["seriousnesses"] = seriousnes_final
    else:
        pvi_json["events"][0]["seriousnesses"] = serious_empty
    pvi_json["events"][0]["country"] = event_country
    pvi_json["events"][0]["startDate"] = event_onset
    if len(pvi_json["events"]) >1:
        for event_index in range(1, len(pvi_json["events"])):
            pvi_json["events"][event_index]["seriousnesses"] = serious_empty
    return pvi_json

#processing lab data
def update_labtest(pvi_json):
    for test in pvi_json["tests"]:
        test_seq = test["seq_num"]
        if test_seq:
            test["seq_num"] = field_na_checker(re.sub(r'[^\x00-\x7F]+','',test_seq).replace("\n", " ").replace("#",""))
        else:
            test["seq_num"] = None
        test_name = test["testName"]
        if test_name:
            test["testName"] = field_na_checker(re.sub(r'[^\x00-\x7F]+','',test_name).replace("\n", " ").replace("Test / Assessment / Notes",""))
        else:
            test["testName"] = None
        test_result = test["testResult"]
        if test_result:
            test["testResult"] = field_na_checker(re.sub(r'[^\x00-\x7F]+','',test_result).replace("F\n", " ").replace("\n", " ").replace("Results",""))
        else:
            test["testResult"] = None
        test_date = test["startDate"]
        if test_date:
            test["startDate"] = field_na_checker(re.sub(r'[^\x00-\x7F]+','',test_date).replace("\n", " ").replace("Date",""))
        else:
            test["startDate"] = None
        if test["testName"]:
            if "Results" in  test["testName"]:
                result_in_name = test["testName"].split("Results")
                try:
                    test["testName"] = field_na_checker(strip_characters(result_in_name[0]))
                except:
                    pass
                try:
                    test["testResult"] = field_na_checker(strip_characters(result_in_name[1]))
                except:
                    pass
            elif "positive" in test["testName"].lower():
                test_name_po = test["testName"]
                try:
                    result_start_pos = test_name_po.lower().find("positive")
                    test["testName"] = field_na_checker(strip_characters(test_name_po[:result_start_pos-1]))
                    test["testResult"] = field_na_checker(strip_characters(test_name_po[result_start_pos:]))
                except:
                    print("check in positive")
            elif "negative" in test["testName"].lower():
                test_name_po = test["testName"]
                try:
                    result_start_pos = test_name_po.lower().find("negative")
                    test["testName"] = field_na_checker(strip_characters(test_name_po[:result_start_pos-1]))
                    test["testResult"] = field_na_checker(strip_characters(test_name_po[result_start_pos:]))
                except:
                    print("check in negative")
            elif "normal" in test["testName"].lower():
                test_name_po = test["testName"]
                try:
                    result_start_pos = test_name_po.lower().find("normal")
                    test["testName"] = field_na_checker(strip_characters(test_name_po[:result_start_pos-1]))
                    test["testResult"] = field_na_checker(strip_characters(test_name_po[result_start_pos:]))
                except:
                    print("check in negative")
        test_highlow = test["testLow"]
        if test_highlow:
            test_highlow_up = field_na_checker(re.sub(r'[^\x00-\x7F]+','',test_highlow).replace("Normal High / Low","").replace("High / Low","").replace("N/A","").replace("\n", ":").replace("/", ":"))
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
        if every_test["seq_num"] == None and every_test["testName"] == None and every_test["testResult"] == None and every_test["startDate"] == None and every_test["testHigh"] == None and every_test["testLow"] == None:
            pvi_json["tests"][i]=""
        i+=1
    while '' in pvi_json["tests"]:
        pvi_json["tests"].remove('')
    i=1
    for each_lab in pvi_json["tests"]:
        try:
            each_lab["seq_num"] = int(each_lab["seq_num"])
        except:
            print("check in seq num setting for labdata")
    return pvi_json

def num_there(given_string):
    return any(str.isdigit() for str in given_string)

#processing patient name
def patient_name(pvi_json):
    patient = pvi_json["patient"]
    pat_name = patient["name"]
    patient["name"] = None
    if not field_na_checker(pat_name) :
        if patient["weight"] == None and patient["gender"]==None and patient["age"]["inputValue"]==None:
            pvi_json["patient"]["name"] = "Unknown"
            return pvi_json
    else:
        pat_name = re.sub(r'[^\x00-\x7F]+','',pat_name).replace("\n", " ")
        if "PRIVACY" in pat_name:
            pvi_json["patient"]["name"] = None
            return pvi_json
        elif patient["patientId"]:
            if patient["patientId"] in pat_name:
                pvi_json["patient"]["name"] = None
                return pvi_json
            else:
                pvi_json["patient"]["name"]  = field_na_checker(pat_name)
                return pvi_json
        else:
            pvi_json["patient"]["name"]  = field_na_checker(pat_name)
            return pvi_json
    return pvi_json

#processing patient weight
def patient_wegiht(pvi_json):
    weight = pvi_json["patient"]["weight"]
    if weight:
        weight_val = ""
        weight_unit = ""
        try:
            weight = re.sub(r'[^\x00-\x7F]+','',pvi_json["patient"]["weight"]).replace("\n", " ")
            weight_val = weight.split(" ")[0]
            weight_unit = weight.split(" ")[1]
        except:
            print("check in patient weight")
        pvi_json["patient"]["weight"] = field_na_checker(weight_val)
        pvi_json["patient"]["weightUnit"] = field_na_checker(weight_unit)
    return pvi_json

#processing patient age
def patient_age(pvi_json):
    age_dict = pvi_json["patient"]["age"]
    if age_dict["inputValue"]:
        pvi_json["patient"]["age"]["inputValue"] = re.sub(r'[^\x00-\x7F]+','',age_dict["inputValue"]).replace("\n", " ").replace("F","").replace("M","")
        pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"
        pvi_json["patient"]["age"]["inputValue_acc"] = None
        return pvi_json
    elif age_dict["inputValue_acc"]:
        if "PRIVACY" in age_dict["inputValue_acc"] or "PRIVAC" in age_dict["inputValue_acc"] or "PRIVA" in age_dict["inputValue_acc"]:
            pvi_json["patient"]["age"]["inputValue"] = None
            pvi_json["patient"]["age"]["ageType"] = None
            pvi_json["patient"]["age"]["inputValue_acc"] = None
            return pvi_json
        elif pvi_json["reporters"][0]["country"] in ["", None] and pvi_json["patient"]["weight"] in ["", None] and \
            pvi_json["patient"]["age"]["inputValue"] in ["", None] and pvi_json["patient"]["gender"] in ["", None]:
                pvi_json["patient"]["age"]["inputValue"] = strip_characters(pvi_json["patient"]["age"]["inputValue_acc"].replace(" ","").replace("--","-"))
                pvi_json["patient"]["age"]["ageType"] = "PATIENT_BIRTH_DATE"
                pvi_json["patient"]["age"]["inputValue_acc"] = None
                return pvi_json
    return pvi_json

#main function for processing patient details
def update_patient(pvi_json):
    try:
        pvi_json = patient_name(pvi_json) 
    except:
        print("check in patient name")
    try:
        pvi_json = patient_wegiht(pvi_json)
    except:
        print("check in patient weight")
    try:
        pvi_json = patient_age(pvi_json)
    except:
        print("check in patient age")
    return pvi_json

#processing receipt date
def receipt_date(pvi_json):
    if pvi_json["relevantTests_acc"] in ['ZIOPHARM', 'Inovio']:
        pvi_json["receiptDate"] = None
    pvi_json["relevantTests_acc"] = None
    return pvi_json

#processing refernce type
def referenceType(pvi_json):
    pvi_json["references"][0]["referenceType"] = "LP Case Number"
    return pvi_json

#processing source type
def update_report_source(pvi_json):
    val = pvi_json["project"]
    pvi_json["project"] = None
    if val:
        if "Study" in val and "literature" in val and "health professional" not in val and "other" not in val:
            pvi_json["sourceType"][0]["value"] = "Literature Study Trial"
        elif "Study" in val and "health professional" in val and "literature" not in val and "other"  in val:
            pvi_json["sourceType"][0]["value"] = "Study"
        elif "Study" in val and "health professional" in val and "literature" not in val and "other" not in val:
            pvi_json["sourceType"][0]["value"] = "Study"
        elif "Study" in val and "other" in val and "literature" not in val and "health professional" not in val:
            pvi_json["sourceType"][0]["value"] = "Study"
        elif "health professional" in val and "literature" in val and "Study" not in val and "other" not in val:
            pvi_json["sourceType"][0]["value"] = "Literature spontaneous"

        elif "Study" in val and "literature" not in val and "health professional" not in val and "other" not in val:
            pvi_json["sourceType"][0]["value"] = "Study"
        elif "Study" not in val and "literature" not in val and "health professional" in val and "other" not in val:
            pvi_json["sourceType"][0]["value"] = None
        elif "Study" not in val and "literature" in val and "health professional" not in val and "other" not in val:
            pvi_json["sourceType"][0]["value"] = "literature spontaneous"
        elif "Study" not in val and "literature" not in val and "health professional" not in val and "other" in val:
            pvi_json["sourceType"][0]["value"] = "Spontaneous"
    return pvi_json

#processing sendercase version
def sendercase_version(pvi_json):
    if pvi_json["senderCaseVersion"]:
        if "followup" in pvi_json["senderCaseVersion"]:
            if pvi_json["senderCaseVersion_acc"] and pvi_json["senderCaseVersion_acc"]!="1":
                pvi_json["senderCaseVersion"] = pvi_json["senderCaseVersion_acc"]
            else:
                pvi_json["senderCaseVersion"] = 2
    pvi_json["senderCaseVersion_acc"] = None
    if pvi_json["senderCaseVersion"]:
        pvi_json["senderCaseVersion"] = int(pvi_json["senderCaseVersion"])
    return pvi_json

#processing seriousness criteria
def other_serious_criteria(pvi_json):
    if pvi_json["summary"]["caseDescription_acc"]:
        if "Other Serious Criteria:" in pvi_json["summary"]["caseDescription_acc"]:
            pvi_json["summary"]["caseDescription_acc"] = None
            return "Yes"
    pvi_json["summary"]["caseDescription_acc"] = None
    return "No"

#processing patient study id
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
            if center_id_start_pos!=-1:
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

#processing patient death date
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

#processing reporter for last page
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
        pvi_json["reporters"][reporter_index]["middleName"]  = field_na_checker(reportername_parsed["middle"])
        pvi_json["reporters"][reporter_index]["lastName"] = field_na_checker(reportername_parsed["last"])
    pvi_json["reporters"][reporter_index]["givenName"] = None
    return pvi_json

#processing reporter address
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

#splitting reporters based on country
def reporter_split_based_on_country(pvi_json):
    reporter_address = {}
    country_list = ["afghanistan","albania","algeria","andorra","angola","antigua and barbuda","argentina","armenia","australia","austria","azerbaijan","the bahamas","bahrain","bangladesh","barbados","belarus","belgium","belize","benin","bhutan","bolivia","bosnia and herzegovina","botswana","brazil","brunei","bulgaria","burkina faso","burundi","cambodia","cameroon","canada","cape verde","central african republic","chad","chile","china","colombia","comoros","congo, republic of the","congo, democratic republic of the","costa rica","cote d\'ivoire","croatia","cuba","cyprus","czech republic","denmark","djibouti","dominica","dominican republic","east timor (timor-leste)","ecuador","egypt","el salvador","equatorial guinea","eritrea","estonia","ethiopia","fiji","finland","france","gabon","the gambia","georgia","germany","ghana","greece","grenada","guatemala","guinea","guinea-bissau","guyana","haiti","honduras","hungary","iceland","india","indonesia","iran","iraq","ireland","israel","italy","jamaica","japan","jordan","kazakhstan","kenya","kiribati","korea, north","korea, south","kosovo","kuwait","kyrgyzstan","laos","latvia","lebanon","lesotho","liberia","libya","liechtenstein","lithuania","luxembourg","macedonia","madagascar","malawi","malaysia","maldives","mali","malta","marshall islands","mauritania","mauritius","mexico","micronesia, federated states of","moldova","monaco","mongolia","montenegro","morocco","mozambique","myanmar (burma)","namibia","nauru","nepal","netherlands","new zealand","nicaragua","niger","nigeria","norway","oman","pakistan","palau","panama","papua new guinea","paraguay","peru","philippines","poland","portugal","qatar","romania","russia","rwanda","saint kitts and nevis","saint lucia","saint vincent and the grenadines","samoa","san marino","sao tome and principe","saudi arabia","senegal","serbia","seychelles","sierra leone","singapore","slovakia","slovenia","solomon islands","somalia","south africa","south sudan","spain","sri lanka","sudan","suriname","swaziland","sweden","switzerland","syria","taiwan","tajikistan","tanzania","thailand","togo","tonga","trinidad and tobago","tunisia","turkey","turkmenistan","tuvalu","uganda","ukraine","united arab emirates","united kingdom","united states of america","uruguay","uzbekistan","vanuatu","vatican city (holy see)","venezuela","vietnam","yemen","zambia","zimbabwe"]
    first_reporter_address = pvi_json["literatures"][0]["author"]
    first_reporter_name = ""
    first_reporter = False
    if first_reporter_address and "NAME AND ADDRESS WITHHELD" not in first_reporter_address:
        first_reporter = True
        first_reporter_address = first_reporter_address.replace("25b. NAME AND ADDRESS OF REPORTER", "").replace("(Continued on Additional Information Page)", "").replace("()", "")
        first_reporter_name = first_reporter_address.split("\n")[0]
        for country in country_list:
            cnt = first_reporter_address.lower().find(country)
            if cnt != -1:
                first_reporter_address = first_reporter_address[0:cnt+len(country)]
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
            second_reporter_address_all = second_reporter_address_all.replace("25b. NAME AND ADDRESS OF REPORTER", "").replace("(Continued on Additional Information Page)", "").replace("()", "").strip()
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

#processing case description
def update_summary(pvi_json):
    if pvi_json["literatures"][0]["vol"]:
        case_desc = pvi_json["literatures"][0]["vol"].replace("(Continued on Additional Information Page)","").replace("22. CONCOMITANT DRUG(S) AND DATES OF ADMINISTRATION continued","").replace("ADDITIONAL INFORMATION", "").replace("13. Relevant Tests","").replace("14-19. SUSPECT DRUG(S) continued","").replace("23. OTHER RELEVANT HISTORY  continued","").replace("15. DAILY DOSE(S); 18. THERAPY DATES (from/to);","").replace("DISABILITY OR INCAPACITY","").replace("LIFE","").replace("CONGENITAL ANOMALY","").replace("ANOMALY OTHER","").replace("THREATENING","").replace("CONGENITAL","").replace("7+13. DESCRIBE REACTION(S) continued","").replace("13. Lab Data","").replace("INVOLVED PERSISTENT OR SIGNIFICANT","").replace("OR SIGNIFICANT","").replace("OTHER","")
        pvi_json["literatures"][0]["vol"] = None
        try:
            if "Case Version" in case_desc:
                case_start_pos = case_desc.find("Case Version")
                case_desc = case_desc.replace(case_desc[case_start_pos-18:case_start_pos+21],"")
            if "Mfr. Control Number" in case_desc:
                mfr_start_pos = case_desc.find("Mfr. Control Number")
                case_desc = case_desc.replace(case_desc[mfr_start_pos-12:mfr_start_pos+60],"")
        except:
            pass
        case_desc = re.sub(r'[^\x00-\x7F]+','',case_desc)
        pvi_json["summary"]["caseDescription"] = case_desc
    return pvi_json

def recipt_date(pvi_json):
    if pvi_json["senderCaseVersion"]:
        if pvi_json["senderCaseVersion"] == 1:
            pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
        elif pvi_json["senderCaseVersion"]>1:
            pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
            pvi_json["receiptDate"] = None
    return pvi_json


def get_postprocessed_json(pvi_json, w1_json):
    try:
        pvi_json = update_labtest(pvi_json)
    except:
        print("issue at labtest - postprocessing")
    try:
        pvi_json = patient_study_id(pvi_json)
    except:
        print("issue at patientid and study id")
    try:
        pvi_json = update_patient(pvi_json)
    except:
        print("issue at patient - postprocessing")
    try:
        pvi_json = postprocess_products(pvi_json)
    except:
        print("issue at products - postprocessing")
    try:
        pvi_json = receipt_date(pvi_json)
    except:
        print("issue at receipt date - postprocessing")
    try:
        pvi_json = referenceType(pvi_json)
    except:
        print("issue at setting reference type")
    try:
        pvi_json = update_report_source(pvi_json)
    except:
        print("issue at report source")
    try:
        pvi_json = sendercase_version(pvi_json)
    except:
        print("issue at sender case version")
    try:
        check_flag = other_serious_criteria(pvi_json)
    except:
        print("issue at sender case id")
    try:
        pvi_json = update_events(pvi_json, check_flag)
        #print("events")
    except:
        print("issue at events - postprocessing")
    try:
        pvi_json = deathdate(pvi_json)
    except:
        print("issue at death date")
    try:
        pvi_json = reporter_split_based_on_country(pvi_json)
    except:
        print("issue at reporter address")
    try:
        pvi_json = update_pat_med_his(pvi_json)
    except:
        print("issue at pat med his")
    try:
        pvi_json = update_summary(pvi_json)
    except:
        print("issue at summary desc")
    try:
        pvi_json = recipt_date(pvi_json)
    except:
        print("issue at recipt date")
    return pvi_json
