def populate_lotnumber(pvi_json, w1_json):
    pvi_json['products'][0]['doseInformations'][0]['customProperty_batchNumber_value'] = [each_annot['value'] for each_annot in w1_json if each_annot['AnnotID'] == '10014'][0][0][-1]
    return pvi_json
    
def get_postprocessed_json(pvi_json, w1_json):
    try:
        pvi_json = populate_lotnumber(pvi_json, w1_json)
    except:
        print("issue populating lot number")
    return pvi_json
