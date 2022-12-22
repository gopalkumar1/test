import re
import datetime
import copy
import typing
import traceback
import pandas as pd
import json #remove

"""method which will be called from outside by generic for post processing the json"""


def process_dates(str):
	str = re.sub('[^0-9a-zA-Z]', '', str)
	possi = ["%d%m%y", "%d%m%Y", "%d%b%y", "%d%b%Y", "%d%B%y", "%d%B%Y", "%m%d%y", "%b%d%Y"]
	for i in possi:
		try:
			return datetime.datetime.strptime(str, i).strftime('%d-%b-%Y')
		except ValueError:
			pass

	possi2 = ["%b%Y", "%b%y", "%m%Y", "%m%y", "%B%Y", "%B%y"]
	for i in possi2:
		try:
			return datetime.datetime.strptime(str, i).strftime('%b-%Y')
		except ValueError:
			pass
	return None


def process_events(pvi_json):
	for event_index, event in enumerate(pvi_json["events"]):
		if event["startDate"] is not None:
			date = event["startDate"].replace("_", "").split("-")
			date = [each for each in date if each.strip() not in (None, "")]
			if len(date) == 1:
				date.insert(0, "01")
				date.insert(1, "01")
				date = process_dates("-".join(date))
				date = date.split("-")[-1]
				event["startDate"] = date
			elif len(date) == 2:
				date.insert(0, "01")
				date = process_dates("-".join(date))
				date = date.split("-")[1:]
				event["startDate"] = "-".join(date)
			else:
				event["startDate"] = process_dates("-".join(date))
	return pvi_json


def process_name(givenName):
	if givenName is None:
		return None, None, None
	else:
		name = givenName.split()
		title_list = ["dr", "mr", "mrs", "ms"]
		title, firstName, lastName = None, None, None
		for each in title_list:
			if len(name) == 1:
				if givenName.lower().startswith(each):
					title = name[0]
				else:
					firstName = name[0]
			elif len(name) == 2:
				if givenName.lower().startswith(each):
					title = name[0]
					firstName = name[1]
				else:
					firstName = name[0]
					lastName = name[1]
			else:
				if givenName.lower().startswith(each):
					title = name[0]
					firstName = name[1]
					lastName = " ".join(name[2:])
		return title, firstName, lastName


def process_reporters(pvi_json, extracted_df):
	# reporter_doctor, reporter_consent, preferred_contact = None, None, None
	# caseDescription, adminNotes = [], []
	# if pvi_json["summary"]["caseDescription"]:
	# 	caseDescription = pvi_json["summary"]["caseDescription"].split("\n")
	# if pvi_json["summary"]["adminNotes"]:
	# 	adminNotes = pvi_json["summary"]["adminNotes"].split("\n")
	# notes = caseDescription + adminNotes
	#
	# for each in notes:
	# 	if each.startswith("If the reporter is the patient"):
	# 		reporter_doctor = each.split("doctor?")[-1].strip()
	# 	if each.startswith("Reporter consent"):
	# 		reporter_consent = each.split("details?")[-1].strip()
	# 	if each.startswith("Preferred method"):
	# 		preferred_contact = each.split("contact:")[-1].strip()
	# reporter_doctor = True if reporter_doctor == "Yes" else False
	# reporter_consent = True if reporter_consent == "Yes" else False

	# pvi_json["reporters"].append(copy.deepcopy(pvi_json["reporters"][0]))
	#pvi_json["reporters"][0], pvi_json["reporters"][1] = pvi_json["reporters"][1], pvi_json["reporters"][0] #
	#pvi_json["reporters"][0]["consentToDisclosePII"], pvi_json["reporters"][1]["consentToDisclosePII"] = \
	#	pvi_json["reporters"][1]["consentToDisclosePII"], pvi_json["reporters"][0]["consentToDisclosePII"]

	#pvi_json["reporters"].pop(1) # new requirement came.
	# considering only 2 reporter list will be there.
	for reporter_index, reporter in enumerate(pvi_json["reporters"]):
		#if reporter_index == 0:
			# if reporter_consent:
			# 	# reporter["givenName"] = reporter["firstName"]
			# 	if reporter["givenName"] is not None:
			# 		reporter["givenName"] = reporter["givenName"].replace("_", "")
			# 	reporter["title"], reporter["firstName"], reporter["lastName"] = process_name(reporter["givenName"])
			# 	reporter["givenName"] = None
			# 	reporter["street"] = reporter["city"]
			# 	reporter["city"] = None
			# 	if preferred_contact == "Phone":
			# 		reporter["email"] = None
			# 	elif preferred_contact == "E-mail":
			# 		reporter["telephone"] = None
			# else:
			# 	for key, value in reporter.items():
			# 		if key != "qualification":
			# 			reporter[key] = None
		if reporter["givenName"]:
			reporter["givenName"] = reporter["givenName"].replace("_", "")
		reporter["title"], reporter["firstName"], reporter["lastName"] = process_name(reporter["givenName"])
		reporter["givenName"] = None

		if reporter["street"]:
			reporter["street"] = reporter["street"].replace("_", "")

		if extracted_df.loc["method_of_contact"]["value"][0] == '1' and \
				extracted_df.loc["method_of_contact"]["value"][1] == '0':
			reporter["telephone"] = reporter["email"]
			reporter["email"] = None
		elif extracted_df.loc["method_of_contact"]["value"][0] == '0' and \
				extracted_df.loc["method_of_contact"]["value"][1] == '1':
			reporter["telephone"] = None
	return pvi_json
'''
		elif reporter_index == 1:
			if reporter["givenName"]:
				reporter["givenName"] = reporter["givenName"].replace("_", "")

			if reporter["givenName"]:
				reporter["title"], reporter["firstName"], reporter["lastName"] = process_name(reporter["givenName"])
				reporter["givenName"] = None
				if reporter["street"]:
					reporter["street"] = reporter["street"].replace("_", "")
				reporter["city"] = None
				reporter["email"] = None
				reporter["telephone"] = None
				reporter["qualification"] = "Physician" # todo requirement?
			else:
				pvi_json["reporters"].pop(1)
		# if not reporter_doctor:
		# 	pvi_json["reporters"].pop(-1) # todo no need to pass -1
'''


def process_receiptDate(pvi_json):
	if pvi_json["receiptDate"] is not None:
		pvi_json["receiptDate"] = process_dates(pvi_json["receiptDate"].replace("_", ""))
		pvi_json["mostRecentReceiptDate"] = None
	return pvi_json


def process_patient(pvi_json):
	if pvi_json["patient"]["age"]["inputValue"]:
		pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue"].replace("_", "").replace(
			"years", "Years")

	if pvi_json["patient"]["age"]["inputValue"]:
		if "year" in pvi_json["patient"]["age"]["inputValue"].lower():
			pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"
			pvi_json['patient']['patientDob'] = None
		else:
			pvi_json["patient"]["age"]["ageType"] = "PATIENT_AGE_GROUP"
			if pvi_json["patient"]["age"]["inputValue"]:
				pvi_json['patient']['patientDob'] = pvi_json["patient"]["age"]["inputValue"]
				pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue_acc"]

		if pvi_json["patient"]["age"]["inputValue_acc"]:
			if pvi_json["summary"]["additionalNotes"]:
				pvi_json["summary"]["additionalNotes"] = pvi_json["summary"]["additionalNotes"] + "\n Age Group: " + \
														 pvi_json["patient"]["age"]["inputValue_acc"]
			else:
				pvi_json["summary"]["additionalNotes"] = None
	else:
		if pvi_json["patient"]["age"]["inputValue_acc"]:
			pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue_acc"]
			pvi_json["patient"]["age"]["ageType"] = "PATIENT_AGE_GROUP"
	pvi_json["patient"]["age"]["inputValue_acc"] = None

	if pvi_json["patient"]["weight"]:
		pvi_json["patient"]["weight"] = pvi_json["patient"]["weight"].replace("_", "")
		if pvi_json["patient"]["weight"].strip() == "":
			pvi_json["patient"]["weight"] = None

	if pvi_json["patient"]["height"]:
		pvi_json["patient"]["height"] = pvi_json["patient"]["height"].encode("utf-8").decode("unicode-escape").encode("latin-1").decode("utf-8")
		pvi_json["patient"]["height"] = pvi_json["patient"]["height"].replace("_", "")
		if pvi_json["patient"]["height"].strip() == "":
			pvi_json["patient"]["height"] = None

	if pvi_json["patient"]["weightUnit"] is not None:
		if pvi_json["patient"]["weightUnit"].lower() == "kg":
			pvi_json["patient"]["weightUnit"] = "Kgs"

	if pvi_json["patient"]["heightUnit"] is not None:
		if pvi_json["patient"]["heightUnit"] == "meters":
			pvi_json["patient"]["heightUnit"] = "Cms"
			if pvi_json["patient"]["height"] is not None:
				pvi_json["patient"]["height"] = str(int(pvi_json["patient"]["height"])*100)
		else:
			pvi_json["patient"]["heightUnit"] = "Inches"
			if pvi_json["patient"]["height"] is not None:
				height_list = pvi_json["patient"]["height"].split("\u2019")
				height_list = [int(each) for each in height_list if each not in ("", None, " ")] #
				if len(height_list) == 1:
					height = height_list[0]*12
				else:
					height = height_list[0]*12+height_list[1]
				pvi_json["patient"]["height"] = str(height)

	pvi_json["patient"]["country"] = pvi_json["events"][0]["country"]
	#Patient initial  Unknown (New requirement for CRP)
	pvi_json["patient"]["name"] = "Unknown"

	return pvi_json


def get_template(sample_dict: dict, template_dict: dict, count: int):
	if count == 0:
		template_dict = sample_dict.copy()
	for key, value in sample_dict.items():
		if type(value) is list:
			for each in value:
				template_dict = get_template(each, template_dict, count + 1)
		elif type(value) is dict:
			template_dict = get_template(value, template_dict, count + 1)
		else:
			if not key.endswith("acc"):
				sample_dict[key] = None
	return template_dict


def process_products(pvi_json):
	pvi_json["products"][-1]["license_value"] = pvi_json["products"][-1]["license_value"].replace("_", "")
	other_product_data = pvi_json["products"][-1] if pvi_json["products"][-1]["license_value"] else None
	del pvi_json["products"][-1]

	if pvi_json["products"][0]["license_value"]:
		primary_product_nameList = pvi_json["products"][0]["license_value"].strip().split("\n")

		for each in range(len(primary_product_nameList) - 1):
			template_product = get_template(copy.deepcopy(pvi_json["products"][0]), {}, 0)
			pvi_json["products"].append(template_product)

		for prod_index, product in enumerate(primary_product_nameList):
			pvi_json["products"][prod_index]["license_value"] = product.strip()
			pvi_json["products"][prod_index]["seq_num"] = prod_index + 1
			pvi_json["products"][prod_index]["role_value"] = "suspect"

		if pvi_json["products"][0]["doseInformations"][0]["description"] is not None:
			doseDescription = pvi_json["products"][0]["doseInformations"][0]["description"].split("\n")
			doseDescription.pop(0)

			for i in range(len(pvi_json["products"])):
				pvi_json["products"][i]["doseInformations"][0]["description"] = doseDescription[i]

		if pvi_json["products"][0]["doseInformations"][0]["startDate"] is not None:
			pvi_json["products"][0]["doseInformations"][0]["startDate"] = process_dates(
				pvi_json["products"][0]["doseInformations"][0]["startDate"].split("\n")[0].replace("_", ""))
		if pvi_json["products"][0]["doseInformations"][0]["endDate"] is not None:
			pvi_json["products"][0]["doseInformations"][0]["endDate"] = process_dates(
				pvi_json["products"][0]["doseInformations"][0]["endDate"].replace("_", ""))
	else:
		del pvi_json["products"][0]

	if other_product_data:
		pvi_json["products"].append(other_product_data)
	return pvi_json


def process_study(pvi_json):
	pvi_json["sourceType"] = [{"value": "Non-Interventional Trial", "value_acc": 0.95}]
	return pvi_json


def process_treatment(pvi_json):
	if pvi_json["summary"]["caseDescription"] and pvi_json["summary"]["adminNotes"]:
		caseDescription = pvi_json["summary"]["caseDescription"].split("\n")
		for desc in caseDescription:
			if desc.startswith("Did the person take"):
				index = caseDescription.index(desc)
				desc = desc.split("?")[0] + " : " + pvi_json["summary"]["adminNotes"].replace("_", "") + " "
				caseDescription[index] = desc
				pvi_json["summary"]["adminNotes"] = None
				# break

		pvi_json["summary"]["caseDescription"] = "\n".join(caseDescription)
	return pvi_json


def get_postprocessed_json(pvi_json, extracted_data_json):
	extracted_df = pd.DataFrame(extracted_data_json)
	extracted_df.set_index("class", inplace=True)
	print("inside postprocessing file")
	try:
		pvi_json = process_events(pvi_json)
	except:
		traceback.print_exc()
	try:
		pvi_json = process_reporters(pvi_json, extracted_df)
	except:
		traceback.print_exc()
	try:
		pvi_json = process_receiptDate(pvi_json)
	except:
		traceback.print_exc()
	try:
		pvi_json = process_patient(pvi_json)
	except:
		traceback.print_exc()
	try:
		pvi_json = process_products(pvi_json)
	except:
		traceback.print_exc()
	try:
		pvi_json = process_study(pvi_json)
	except:
		traceback.print_exc()
	try:
		pvi_json = process_treatment(pvi_json)
	except:
		traceback.print_exc()
	return pvi_json


# extracted_json = json.load(open('/home/rxlogix/Downloads/postprocessing/r2docx/inter_3.json')) #remove
# pvi_json = json.load(open('/home/rxlogix/Downloads/postprocessing/r2docx/post0_3.json')) #remove
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_json))) #remove

# extracted_json = json.load(open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/sdea-1-inter.json')) #remove
# pvi_json = json.load(open('/home/rx-sandeshs/backendservice/utility/template/form_configurations/postprocessing_json/sdea-1-outer.json')) #remove
# print(json.dumps(get_postprocessed_json(pvi_json, extracted_json))) #remove
