import os
import pdfplumber
import pytesseract
from commonComponents1.pviClassModule import *
import traceback
from os import path
import re
import spacy
import configparser
import requests
from log_file import logger, config, py_comm_comp, pqc_ae_model, spam_model

try:
	from PIL import Image
except ImportError:
	import Image


def process_text(paths,text):
	temp_str = "Subject :"
	text = re.sub("\s*(\\n)*Subject\s*:\s*.*", "", text)
	text = re.sub("\s*(\\n)*From\s*:\s*.*>", "", text)
	text = re.sub("\s*(\\n)*Received\s*Date\s*:\s*.*", "", text)
	text = re.sub("\s*(\\n)*To\s*:\s*.*>", "", text)
	if os.path.exists(paths["ocrpath"] + "/test.txt"):
		os.remove(paths["ocrpath"] + "/test.txt")
	file = open(paths["ocrpath"] + "/test.txt", "w")
	text = text.encode('ascii', 'ignore').decode('ascii')
	file.write(str(text))
	file.close()
	return text


def checkMalfunctions(text, py_path):
	text = re.sub("\s+", " ", text)
	MALFUNCTION_KEYWORDS = config.get('unstructured', 'MALFUNCTION_KEYWORDS')
	config_unstructured = configparser.ConfigParser()
	config_unstructured.read(py_path + "/config/prediction_config.ini")
	model_path = py_path + "/models/en_med_astragenica" #+ config_unstructured.get('SectionOne', 'pqc_models')
	nlp = spacy.load(model_path)
	doc = nlp(text)
	labels, mal_values = [], []
	for ents in doc.ents:
		labels.append(ents.label_)
		mal_values.append(ents.text)

	if "MALFUNCTIONS" in labels:
		for i in MALFUNCTION_KEYWORDS:
			for j in mal_values:
				if i.lower() in j.lower():
					return True
	return False


def check_pqc(paths, text):
	py_path = "/".join(path.dirname(path.abspath(__file__)).split("/")[:-1] + ["unstructured", "extdata"])
	if os.path.exists(paths["ocrpath"] + "/pqc-ae.txt"):
		os.remove(paths["ocrpath"] + "/pqc-ae.txt")
	file = open(paths["ocrpath"] + "/pqc-ae.txt", "w")
	file.write(str(text))
	file.close()
	logger.info("text going in pqc-ae is : ", text)
	py_comm_comp.pqc_ae_detect.pqc_ae_detector(paths["ocrpath"] + "/pqc-ae.txt", pqc_ae_model,
											   paths["ocrpath"] + "/result_pqc_ae.json")
	result_json = paths["ocrpath"] + "/result_pqc_ae.json"
	with open(result_json, "r") as data:
		z = json.load(data)
	# t = json.dumps(t)
	logger.info(z)
	case_category = z["label"]
	case_category_accu = z["label_accu"]
	logger.info("case_category_accu is --------------------", case_category_accu)
	case_category = case_category.split("-")
	logger.info("case_category value is ")
	logger.info(case_category)
	category_flag = False
	if case_category == ["MI"] or checkMalfunctions(text, py_path):
		category_flag = True
	logger.info("category flag value is ")
	logger.info(category_flag)
	if len(case_category) > 0:
		for every_category in range(len(case_category)):
			if case_category[every_category] == "AE":
				case_category[every_category] = "AE Case"
			elif case_category[every_category] == "MI":
				case_category[every_category] = "Medical Inquiry"
	return case_category, case_category_accu, category_flag


def process_json(x):
	y = pviJSON.__addWithValuesToDictObject__(x)
	for value in ["products", "events"]:
		if value in y.keys():
			if len(y[value]) < 1:
				logger.info("no %s exist" % value)
				del y[value]
			else:
				products_list = [count_nan(each, 0, 0) for each in y[value]]
				y[value] = [y[value][i] for i in range(len(products_list)) if
							products_list[i][1] != products_list[i][2]]
				if len(y[value]) < 1:
					logger.info("no %s exist" % value)
					del y[value]
	return y


def count_nan(jsonFile, total_count, nan_count):
	jsonFile = pviJSON(jsonFile)
	keys = jsonFile.keys()
	for key in keys:
		if key == "seq_num":
			continue
		if type(jsonFile[key]) in (dict, pviJSON):
			jsonFile.update(pviJSON({key: count_nan(pviJSON(jsonFile[key]), total_count, nan_count)[0]}))
		elif type(jsonFile[key]) in (list, pviList):
			jsonFile[key] = pviList(jsonFile[key])
			for i in range(len(jsonFile[key])):
				jsonFile[key].insert(i, pviJSON(count_nan(pviJSON(jsonFile[key][i]), total_count, nan_count)[0]))
				jsonFile[key].pop(i + 1)
		else:
			total_count = total_count + 1
			if str(jsonFile[key]).lower() in ("nan", "none", "", "n/a"):
				nan_count = nan_count + 1
	return jsonFile, total_count, nan_count


def spam_identification(x, y, spam_flag,text,paths):
	if (not ("products" in y.keys() and "events" in y.keys()) or (
			len(y["products"]) == 1 and y["products"][0].license_value is None)):
		logger.info("no product or event exists")
		if not spam_flag:
			x = {
				"code": 2,
				"message": "Spam detection is set False. Form may or may not contain valid case data."
			}
			return x
		if os.path.exists(paths["ocrpath"] + "/spam.txt"):
			os.remove(paths["ocrpath"] + "/spam.txt")
		file = open(paths["ocrpath"] + "/spam.txt", "w")
		file.write(str(text))
		file.close()
		logger.info("text going in spam is : ", text)
		py_comm_comp.spam_detect.spam_detector(paths["ocrpath"] + "/spam.txt", spam_model, paths["ocrpath"] + "/result.json")
		result_json = paths["ocrpath"] + "/result.json"
		with open(result_json, "r") as data:
			t = json.load(data)
		logger.info(t)
		if t["label"] == "spam" or (len(y["products"]) == 1 and y["products"][0].license_value is None):
			x["code"] = 4
			x["message"] = "spam"
			try:
				x["spam_acc"] = float("%.2f" % t["label_accu"])  # still dont know what 2 does in as.numeric(.., 2)
			except:
				x["spam_acc"] = None
			return x
	return x

def unstructured_form_parsing(paths, text, unstructuredParsing_flag, spam_flag):
	logger.info("unstructured parsing in progress")

	x = {"code": None, "message": None, "spam_acc": None}

	try:
		if text.strip() == "":
			pdfObj = pdfplumber.open(paths["filepath"])
			pagesObj = pdfObj.pages
			for page in pagesObj:
				if page.page_number == 1:
					fileName = paths["ocrpath"] + "/ocred_text.txt"
					file = open(fileName, "rb")
					text = file.read().decode("ASCII")
					os.remove(fileName)
					logger.info(text)
				else:
					# do ocr and append text
					logger.info("unstructured: doing ocr for extended pages, page_num: " + page)
					imageObj = page.to_image(resolution=300)
					imageObj.save(paths["imagepath"] + "/form.tiff", format="tiff")
					fileName = paths["ocrpath"] + "/ocred.txt"
					file = open(fileName, "w")
					file.write(str(pytesseract.image_to_string(Image.open(paths["imagepath"] + "/form.tiff"))))
					file.close()
					fileName = paths["ocrpath"] + "/ocred_text.txt"
					file = open(fileName, "rb")

		text = process_text(paths,text)
		case_category, case_category_accu, category_flag = check_pqc(paths, text)
		'''for normal unstructured'''
		#		unstructured.unstructure_pipeline.unstruct_prediction(paths["ocrpath"] + "/test.txt", paths["ocrpath"] + "/unsoutput.json", py_path, category_flag)
		#		for unstructured api
		cioms_flag = None
		url_unst1 = config.get('unstructured', 'unstructure_api_url')
		print("----------------------------------------"+url_unst1)
		config_path_uns = "/home/ubuntu/pvi-form-engine/structuredForms/py_generic/extdata/config/config.json"
		config_json_uns = json.load(open(config_path_uns))
		url_unst = config_json_uns["base-generic-url"] + ":" + "9888/unstruct/live"
		print("----------------------------------------"+url_unst)
		#requests.post(url_unst, headers={"input_file": paths["ocrpath"] + "/test.txt",
		#								 "output_file": paths["ocrpath"] + "/unsoutput.json",
		#								 "PQC_FLAG": str(category_flag), "cioms_flag": str(cioms_flag)})
		files = {'file2': open(paths["ocrpath"] + "/test.txt",'rb')}
		x = requests.post(url_unst,files=files,headers={"PQC_FLAG": str(category_flag), "cioms_flag": str(cioms_flag)})
		x = x.json()
		#try:
		#	with open(paths["ocrpath"] + "/unsoutput.json") as data:
		#		x = json.load(data)
		#except:
		#	with open("/".join(path.dirname(path.abspath(__file__)).split("/")[:-3] + ["temp1.json"])) as data:
		#		x = json.load(data)
		logger.info("x from JSON")
		logger.info(x)

		y = process_json(x)
		x = spam_identification(x, y, spam_flag,text,paths)
		if x["message"] == "spam" or x["code"] == 2:
			return x
		x["code"] = 6
		x["message"] = "Non Form AE Case"
		if case_category_accu >= 0.98:
			x["categories"] = case_category
		return x

	except Exception:
		logger.info(("\nstartTrace::::" + traceback.format_exc().strip() + "::::endTrace").replace("\n", "\n$"))
		x = {
			"code": 3,
			"message": "error came parsing unstructured AE or checking for spam"
		}
		return x
