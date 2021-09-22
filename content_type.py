from log_file import logger, config, py_comm_comp
import pdfplumber
from PyPDF2 import PdfFileMerger, PdfFileReader
from pdf2image import convert_from_path
import pandas as pd
import re
import os
import shutil
import traceback
import docx
import csv
from os import path


def create_tiff(paths):
	shutil.rmtree(paths["imagepath"] + "/")
	os.mkdir(paths["imagepath"])
	output_tiff = paths["deskewpath"] + "/form.tiff"
	py_comm_comp.deskew_tiff_convert.deskew_tiff_convert_digital(paths["filepath"], output_tiff, paths["tmpdirpath"])
	input_tiff = paths["deskewpath"] + "/form.tiff"
	output_pdf = paths["ocrpath"] + "/form"
	py_comm_comp.hocr_pdf_generator.hocr_pdf_generator(input_tiff, output_pdf)


def discover_content_type(text):
	form_identification_path = config.get('api', 'form_identification_path')
	form_type = "UNKNOWN"
	config_file = "/".join(
		path.dirname(path.abspath(__file__)).split("/") + ["extdata", "config"]) + "/" + form_identification_path
	configdata = pd.read_csv(config_file, sep="|")
	leng = len(configdata)
	for i in range(leng):
		if text == "" or text is None:
			break
		pattern = (configdata.loc[i][1]).split(",")
		val_list = [False] * len(pattern)
		for j in range(len(pattern)):
			pattern[j] = re.sub("\"", "", pattern[j])
			pattern[j] = re.sub("\'", "", pattern[j])
			pattern[j] = pattern[j].strip()
			pattern[j] = re.sub("\s+", "\s*", pattern[j])
			pattern[j] = "\s*" + pattern[j] + "\s*"
			pattern[j] = re.compile(pattern[j])
			if re.search(pattern[j], text):
				val_list[j] = True
		if False not in val_list:
			form_type = configdata.loc[i][0]
			module_name = configdata.loc[i][2]
			break
	if form_type == "UNKNOWN":
		module_name = ""
	return [form_type, module_name]


def get_text(filename):
	doc = docx.Document(filename)
	fullText = [para.text for para in doc.paragraphs]
	return '\n'.join(fullText)

def get_text_from_txt(filename):
	txt_file = open(filename, "r")
	doc_text = txt_file.readlines()
	return "".join(doc_text)

def get_text_from_csv(filepath):
        with open(filepath, 'r') as csv_file:
                reader = csv.reader(csv_file)
                data = []
                for row in reader:
                        data.extend(row)
        digital_pdf = " ".join(data)
        return digital_pdf

def digitalpdf_data_extraction(paths, digital_text, scanned):
	digital_text = ["" if i is None else i for i in digital_text]
	content_type = "UNKNOWN"
	module_name = ""
	for index in range(len(digital_text)):
		disc_con_typ = discover_content_type(digital_text[index])
		logger.info("discovered content type" + disc_con_typ[0])
		if disc_con_typ[0] is not "UNKNOWN":
			logger.info("inside not unknown")
			content_type = disc_con_typ[0]
			module_name = disc_con_typ[1]
			digital_text = digital_text[index:len(digital_text)]
			# removing pages that did not have usable data
			if index > 0:
				mergeObj = PdfFileMerger()
				pdfObj = convert_from_path(paths["filepath"], first_page=index + 1, last_page=len(digital_text))
				for page in pdfObj:
					page.save(paths["inputpath"] + "/temp.pdf")
					temp = PdfFileReader(paths["inputpath"] + "/temp.pdf")
					mergeObj.append(temp)
				os.remove(paths["inputpath"] + "/temp.pdf")
				mergeObj.write(paths["filepath"])

			pages = pdfplumber.open(paths["filepath"]).pages
			if scanned:
				if len(pages) > 1:
					create_tiff(paths)
			break
	return [content_type, module_name, digital_text]


def scannedpdf_data_extraction(paths,scanned):
	logger.info("deskew and hocr generator for unknown content type")
	create_tiff(paths)
	pdf = pdfplumber.open(paths["ocrpath"] + "/form.pdf")
	pages = pdf.pages
	content_type = "UNKNOWN"
	module_name = ""
	complete_ocr_text = ""
	for page in pages:
		ocr_text = page.extract_text()
		complete_ocr_text = complete_ocr_text + "\n" + ocr_text
		content_type_module_name = discover_content_type(ocr_text)
		logger.info("discovered content type " + content_type_module_name[0])
		if content_type_module_name[0] is not "UNKNOWN":
			content_type = content_type_module_name[0]
			module_name = content_type_module_name[1]
			text = ocr_text
			logger.info("OCR_text_content_type: " + content_type)
			if page.page_number >= 2:
				mergeObj = PdfFileMerger()
				pdfObj = convert_from_path(paths["filepath"], first_page=page.page_number)
				for tmp_page in pdfObj:
					tmp_page.save(paths["inputpath"] + "/out_form.pdf")
					temp = PdfFileReader(paths["inputpath"] + "/out_form.pdf")
					mergeObj.append(temp)
				os.remove(paths["inputpath"] + "/out_form.pdf")
				mergeObj.write(paths["filepath"])

			break
	return [content_type, module_name, complete_ocr_text]


def find_content_type(paths, doc_type):
	x = {"code": None, "message": None}
	# checks for module in site-packages first if not found then searches local git repository for module (easier for development purposes)

	if doc_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
		logger.info("file type is docx")
		digital_text = get_text(paths["inputpath"] + "/form.docx")
		logger.info(digital_text)
		disc_con_typ = discover_content_type(digital_text)
		logger.info("discovered content type")
		logger.info(disc_con_typ)
		if disc_con_typ[0] is not "UNKNOWN":
			logger.info("inside not unknown")
			content_type = disc_con_typ[0]
			module_name = disc_con_typ[1]
			return [content_type, module_name, digital_text]

	elif doc_type == "text/plain":
		logger.info("file type is txt")
		digital_text = get_text_from_txt(paths["inputpath"] + "/form.txt")
		logger.info(digital_text)
		disc_con_typ = discover_content_type(digital_text)
		logger.info("discovered content type")
		logger.info(disc_con_typ)
		if disc_con_typ[0] is not "UNKNOWN":
			logger.info("inside not unknown")
			content_type = disc_con_typ[0]
			module_name = disc_con_typ[1]
			return [content_type, module_name, digital_text]
	elif doc_type == "text/csv":
                logger.info("file type is csv")
                digital_text = get_text_from_csv(paths["inputpath"] + "/form.csv")
                logger.info(digital_text)
                disc_con_typ = discover_content_type(digital_text)
                logger.info("discovered content type")
                logger.info(disc_con_typ)
                if disc_con_typ[0] is not "UNKNOWN":
                        logger.info("inside not unknown")
                        content_type = disc_con_typ[0]
                        module_name = disc_con_typ[1]
                        return [content_type, module_name, digital_text]

	else:
		scanned = False
		logger.info("file type is docx")
		digital_text = []
		try:
			pdf = pdfplumber.open(paths["filepath"])
		except:
			return {"code": 1, "message": "password protected switch is off"}
		for page in pdf.pages:
			digital_text.append(page.extract_text())
		if None in digital_text:
			scanned = True

		out_digital = digitalpdf_data_extraction(paths,digital_text, scanned)
		if out_digital[0] is not "UNKNOWN":
			return out_digital

		if not config.getboolean('document_type', 'scanned_pdf') and scanned:
			x["code"] = -1
			x["message"] = "scanned pdf not allowed"

		out_scanned = scannedpdf_data_extraction(paths, scanned)
		if len(out_scanned[2]) < len(out_digital[2]):
			out_scanned[2] = out_digital[2]

	return out_scanned
