
import copy

def handling_suspect_product(pvi_json,extracted_data_json): 
    all_products = []
    for text in extracted_data_json:
        if text['class']=='Suspect Products Information':
            all_products = text['value']
            break
        
    prod_empty = {'actionTaken': {'value': None, 'value_acc': 0.95},
     'concentration': [{'unit': None, 'value': None}],
     'dosageForm_value': None,
     'doseInformations': [{'continuing': None,
       'customProperty_batchNumber_value': None,
       'customProperty_expiryDate': None,
       'description': None,
       'dose_inputValue': None,
       'duration': None,
       'endDate': None,
       'frequency_value': None,
       'route_value': None,
       'startDate': None}],
     'indications': [{'reactionCoded': None, 'reportedReaction': None}],
     'ingredients': [{'strength': None,
       'strength_acc': None,
       'unit': None,
       'unit_acc': None,
       'value': None,
       'value_acc': 0.95}],
     'license_value': None,
     'regimen': None,
     'role_value': 'suspect',
     'seq_num': 1}
        
    suspect_prod_all = []
    for prod_index in range(len(all_products)):
        prod = copy.deepcopy(prod_empty)
        prod_name = all_products[prod_index][0].replace("Product 2","").replace("Product 1","").replace("\n"," ").replace("\\n"," ").replace(" ","")
        if prod_name:
            prod_name = prod_name.strip()
        prod["license_value"] = prod_name
        prod["dosageForm_value"] = all_products[prod_index][1].replace("\n","")
        prod["doseInformations"][0]["startDate"] = all_products[prod_index][2].replace(" ","").replace("\n","")
        prod["doseInformations"][0]["endDate"] = all_products[prod_index][3].replace(" ","").replace("\n","")
        prod["actionTaken"]["value"] = all_products[prod_index][4].replace("\n","")
        prod["doseInformations"][0]["frequency_value"] = all_products[prod_index][5].replace("\n","")
        prod["doseInformations"][0]["description"] = all_products[prod_index][5].replace("\n","")
        prod["doseInformations"][0]["route_value"] = all_products[prod_index][6].replace("\n","")     
        prod["indications"][0]["reportedReaction"] = all_products[prod_index][7].replace("\n","")
        prod["doseInformations"][0]["customProperty_batchNumber_value"] = all_products[prod_index][8].replace("\n","")
        prod["role_value"] = "suspect"
        prod['seq_num'] = prod_index
        suspect_prod_all.append(prod)
    
    seqnum = len(all_products)
    for p_index in range(len(pvi_json["products"])):
        tmp = pvi_json["products"][p_index]
        tmp['seq_num'] = seqnum
        suspect_prod_all.append(tmp)
        seqnum += 1
    pvi_json["products"] = suspect_prod_all
    
    patient_name = pvi_json["patient"]["name"].replace("'","").replace("|","")
    pvi_json["patient"]["name"] = patient_name
    
    patient_dob = pvi_json["patient"]["age"]["inputValue"].replace(" ","").replace("\n","")
    pvi_json["patient"]["age"]["inputValue"] = patient_dob

    patient_weight = pvi_json["patient"]["weight"].replace("'","").replace("|","")
    pvi_json["patient"]["weight"] = patient_weight

    reporter_all = []
    for repo in pvi_json["reporters"]:
        email = repo["email"]
        print(email)
        email = email.replace("Faxor email:","").replace("Fax or email:","").replace("Faxoremail:","").replace("Fax oremail:","")
        if email:
            email = email.strip()
        repo["email"] = email
        reporter_all.append(repo)
    
    pvi_json["reporters"] = reporter_all
    
    
    return pvi_json
        

def eventdescriptions(pvi_json,extracted_data_json):
    desc = pvi_json["summary"]["caseDescription"]
    for data in extracted_data_json:
        if data['class'] == "Events Description":
            if desc:
                desc = desc + " Events Description:" + data["value"][0].replace("9. Event(s) Description: Chronological summary of reported events from section 5","").replace("\n"," ") + "."
            else:
                desc = "Events Description:" + data["value"][0].replace("9. Event(s) Description: Chronological summary of reported events from section 5","").replace("\n"," ") + "."
            break
    pvi_json["summary"]["caseDescription"] = desc
    
    return pvi_json

def get_postprocessed_json(pvi_json,extracted_data_json):
    all_products = []
    for prod in pvi_json["products"]:
        if "concomitant" in prod['role_value']:
            dose_all = []
            for dose in prod["doseInformations"]:
                dose["customProperty_batchNumber_value"] = None
                dose_all.append(dose)
            prod["doseInformations"] = dose_all
        all_products.append(prod)
    
    pvi_json = handling_suspect_product(pvi_json,extracted_data_json)
    pvi_json = eventdescriptions(pvi_json,extracted_data_json)
    
    return pvi_json
