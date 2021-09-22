import subprocess
import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
import traceback
from log_file import logger
from os import path


def decode(password):
	logger.info("inside decode pass for: " + password)
	logger.info("init java done: ")
	password = subprocess.check_output(
		["java", "-jar", "/".join(path.dirname(path.abspath(__file__)).split("/") + ["extdata", "RXCODEC.jar"]),
		 password]).decode("ascii")[:-1]
	return password


def get_passwd(pass_header):
	if len(pass_header) == 0:
		passw = ""
	else:
		try:
			passw = decode(pass_header)
			logger.info("decoded pass: " + passw)
		except Exception as err:
			logger.error(err)
			logger.info(("\nstartTrace::::" + traceback.format_exc().strip() + "::::endTrace").replace("\n", "\n$"))
			passw = ""
	return passw


def validate_password(filepath, passw):
	logger.info("inside if_passwd_works: " + passw)
	x = {"code": None, "message": None}
	try:
		temp = pdfplumber.open(filepath, password=passw)
	except PDFPasswordIncorrect as err:
		logger.error(err)
		logger.info(("\nstartTrace::::" + traceback.format_exc().strip() + "::::endTrace").replace("\n", "\n$"))
		x["code"] = 6
		x["message"] = "pdf file is password protected. Kindly provide right password."
		return x
	except Exception as err:
		logger.error(err)
		logger.info(("\nstartTrace::::" + traceback.format_exc().strip() + "::::endTrace").replace("\n", "\n$"))
		x["code"] = 1
		x["message"] = "Can not open file. Please check password or file type."
		return x
	return x
