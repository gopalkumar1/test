from log_file import logger, config
from password_code import get_passwd, validate_password
from content_type import find_content_type
from structured_code import structured_form_parsing
from unstructured_code import unstructured_form_parsing
from pdf2image import pdfinfo_from_path
import subprocess as sp
import os
from PyPDF2 import PdfFileWriter as pfw, PdfFileReader as pfr
import gc
from shutil import rmtree
import traceback


def flush_dir(paths):
	logger.info("now cleaning temp directories")
	rmtree(paths["inputpath"])
	rmtree(paths["imagepath"])
	rmtree(paths["deskewpath"])
	rmtree(paths["ocrpath"])
	rmtree(paths["cbimagepath"])
	rmtree(paths["tmpdirpath"])


def flag_setter(spam_flag, structuredParsing_flag, unstructuredParsing_flag):
	if len(spam_flag) == 0 or spam_flag.lower() != "false" or spam_flag == None:
		spam_flag = True
	else:
		spam_flag = False
	if len(structuredParsing_flag) == 0 or structuredParsing_flag.lower() != "false" or structuredParsing_flag is None:
		structuredParsing_flag = True
	else:
		structuredParsing_flag = False
	if len(
			unstructuredParsing_flag) == 0 or unstructuredParsing_flag.lower() != "false" or unstructuredParsing_flag is None:
		unstructuredParsing_flag = True
	else:
		unstructuredParsing_flag = False
	return [spam_flag, structuredParsing_flag, unstructuredParsing_flag]


def decrypt_pdf(paths, pdf_info, passwd):
	if pdf_info["Encrypted"][:3] == "yes":
		# removing password and saving unprotected file
		alias = (paths["inputpath"] + "/protected_form.pdf")
		os.rename(paths["filepath"], alias)
		sp.run(["pdftk", alias, "input_pw", passwd, "output", paths["filepath"]])
		sp.run(["rm", alias])


def process_forms(paths, params):
	logger.info("list of all paths is ", paths)
	logger.info("list of all params is ", params)
	x = {}
	# setting flag value
	flags = flag_setter(params["spam_flag"], params["structuredParsing_flag"], params["unstructuredParsing_flag"])

	spam_flag = flags[0]
	structuredParsing_flag = flags[1]
	unstructuredParsing_flag = flags[2]

	# checking password
	logger.info("Pass header is: %s" % params["pass_header"])
	passwd = get_passwd(params["pass_header"])
	logger.info("decoded pass is: %s" % passwd)

	if params["doc_type"] == "application/pdf":
		response = validate_password(paths["filepath"],passwd)
		logger.info(response)

		if response['code'] is not None and response['message'] is not None:
			flush_dir(paths)
			return response
		try:
			pdf_info = pdfinfo_from_path(paths["filepath"], userpw=passwd)
			decrypt_pdf(paths, pdf_info, passwd)

			if pdf_info["Pages"] > int(config.get('api', 'max_file_pages')):
				temp_var = pfw()
				for i in range(16):
					temp_var.addPage((pfr(paths["filepath"], 'rb')).getPage(i))
				with open((paths["inputpath"] + "/trimmed_form.pdf"), 'wb') as f:
					temp_var.write(f)
				os.rename(paths["inputpath"] + "/trimmed_form.pdf", paths["filepath"])
		except:
			pass

	result = find_content_type(paths, params["doc_type"])
	logger.info(result)
	if type(result) is not list:
		flush_dir(paths)
		return result

	content_type = result[0]
	module_name = result[1]
	text = result[2]
	# parsing
	if content_type in ["UNKNOWN",""," "]:
		response = unstructured_form_parsing(paths, text[0], unstructuredParsing_flag, spam_flag)
		flush_dir(paths)
		return response

	# code for structured from parsing
	if not structuredParsing_flag:
		x["model_type"] = content_type
		x["code"] = 5
		x["message"] = "Form is medwatch or CIOMS."
		flush_dir(paths)
		return x
	else:
		response = structured_form_parsing(paths, content_type, module_name)
		flush_dir(paths)
		return response
