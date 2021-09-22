from os import path, mkdir
from flask import request, Flask, jsonify
import uuid
from pprint import pprint
from log_file import logger, config
import traceback
from pvi_api import process_forms
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
app.config["DEBUG"] = True


def init_dir(path):
	logger.info("creating temp directories")
	paths = {"tmpdirpath": path,
			 "inputpath": path + "/input",
			 "ocrpath": path + "/ocr",
			 "deskewpath": path + "/deskew",
			 "imagepath": path + "/image",
			 "cbimagepath": path + "/cb_images"}
	try:
		mkdir(paths["tmpdirpath"])
		mkdir(paths["inputpath"])
		mkdir(paths["inputpath"] + "/sample_dir")
		mkdir(paths["imagepath"])
		mkdir(paths["cbimagepath"])
		mkdir(paths["deskewpath"])
		mkdir(paths["ocrpath"])
		mkdir(paths["ocrpath"] + "/ext_sec_data")
	except OSError:
		logger.info("Creation of the directory %s failed" % path)
		logger.critical(("\nstartTrace::::" + traceback.format_exc().strip() + "::::endTrace").replace("\n", "\n$"))
	else:
		logger.info("Successfully created the directory %s " % path)
	return paths


def verify_file_size(filepath):
	max_size = int(config.get('api', 'max_file_size')) * 1024 * 1024  # reading in MB converting to bytes
	file_size = path.getsize(filepath)
	logger.info("Size of the file is " + str(file_size))
	if file_size > max_size:
		return False
	return True


def processing_headers(req, params):
	if "spamParsing" in req:
		params["spam_flag"] = (req['spamParsing']).lower()
	if "structuredParsing" in req:
		params["structuredParsing_flag"] = (req['structuredParsing']).lower()
	if "unstructuredParsing" in req:
		params["unstructuredParsing_flag"] = (req['unstructuredParsing']).lower()
	if "Password" in req:
		params["pass_header"] = req["Password"]

	return params


def file_type(paths, file):
	pdf = bool(config.get('document_type', 'pdf'))
	docx = bool(config.get('document_type', 'docx'))
	txt = bool(config.get('document_type', 'txt'))
	csv = bool(config.get('document_type', 'csv'))
	if file.filename.endswith(".docx") and docx:
		doc_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
		paths["filepath"] = paths["inputpath"] + "/form.docx"
		file.save(paths["filepath"])
	elif file.filename.endswith(".pdf") and pdf:
		doc_type = "application/pdf"
		paths["filepath"] = paths["inputpath"] + "/form.pdf"
		file.save(paths["filepath"])
		#file.save(paths["/home/ubuntu/temp/form.pdf"])
	elif (file.filename.endswith(".txt") or file.filename.endswith(".TXT")) and txt:
		doc_type = "text/plain"
		paths["filepath"] = paths["inputpath"] + "/form.txt"
		file.save(paths["filepath"])
	elif (file.filename.endswith(".csv") or file.filename.endswith(".CSV")) and csv:
		doc_type = "text/csv"
		paths["filepath"] = paths["inputpath"] + "/form.csv"
		file.save(paths["filepath"])
	else:
		return {"code": -1, "message": "file type not allowed"}
	return doc_type


@app.route('/upload/live', methods=['POST'])
def run_ml_api():
	try:
		x = {}
		upload_folder = config.get('api', 'upload_folder')
		path = upload_folder + str(uuid.uuid4())

		if len(request.files) == 0:
			x["code"] = -1
			x["message"] = "no file received"
			return jsonify(x)
		print("identified")
		file = request.files[(list(request.files))[0]]
		paths = init_dir(path)
		doc_type_or_x = file_type(paths, file)
		logger.info(doc_type_or_x)
		print("file type done")
		if type(doc_type_or_x) is dict:
			return jsonify(doc_type_or_x)
		doc_type = doc_type_or_x
		print("doc type is identified")
		file_size_validity = verify_file_size(paths["filepath"])
		print("bbefore size")
		if file_size_validity == False:
			x["code"] = -1
			x["message"] = "File size exceeded"
		else:
			params = {"spam_flag": "", "structuredParsing_flag": "", "unstructuredParsing_flag": "", "doc_type": doc_type,"pass_header": ""}
			req = request.headers
			params = processing_headers(req, params)
			x = process_forms(paths, params)
			logger.info(x)

		return jsonify(x)
	except:
		return jsonify({"code":1, "message":"file not suported"})


def run_pvi_api():
	url = config.get('api_url', 'url')
	port = config.get('api_url', 'port')
	app.run(url, int(port))


@app.route('/static/<path:path>', methods=['GET'])
def send_static(path):
	return send_from_directory('static', path)


SWAGGER_URL = '/swagger'
API_URL = '/static/unstructured_swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
	SWAGGER_URL,
	API_URL,
	config={
		'app_name': "Unstructured Parser"
	}
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)

if __name__ == "__main__":
	run_pvi_api()
