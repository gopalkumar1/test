import importlib
from importlib import util
import traceback
from log_file import logger, config
from os import path


def structured_form_parsing(paths, content_type, module_name):
	logger.info("parsing structured form")
	x = {"code": None, "content_type": None, "module_name": None, "message": None}
	try:
		logger.info("Content type is " + content_type)
		logger.info("Module name is " + module_name)
		logger.info("going for if condition")
		allowed_form = config.getboolean("forms", content_type)
		if not allowed_form:
			return {"code": 1, "content_type": content_type, "module_name": module_name,
					"message": "Form is recognized from the config file but is not allowed"}
		# loads python modules for specific forms based on identification
		ImportModuleName = "py_" + module_name
		ImportModulePath = "/".join(
			path.dirname(path.abspath(__file__)).split("/")[:-1] + ["structuredForms", ImportModuleName, "__init__.py"])

		# checks for module in site-packages first if not found then searches local git repository for module (easier for development purposes)
		spec = importlib.util.find_spec(ImportModuleName)
		if spec is None:
			spec = util.spec_from_loader(ImportModuleName,
										 importlib.machinery.SourceFileLoader(ImportModuleName, ImportModulePath))
		logger.info(spec)
		if spec is None:
			logger.info("case where no module dir exists")
			x["code"] = 5
			x["module_name"] = module_name
			x["message"] = "Form is recognized from the config file but the module is missing"
		else:
			try:
				# if module is found then loads the module and executed parseFromModule() in main.py for that function
				# new modules created must have parseFromModule() in main.py with one argument for temporary directory path
				imported_module = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(imported_module)
				if module_name == "generic":
					x = imported_module.main.parseFromModule(paths["tmpdirpath"], content_type)
				else:
					x = imported_module.main.parseFromModule(paths["tmpdirpath"])
					x["model_type"] = content_type
					x["module_name"] = module_name
				logger.info("completed parsing in " + module_name)
				if x["message"] == "error in Parsing":
					x["code"] = 1
					x["message"] = "This AE form is not configure"
					x["model_type"] = None
					x["module_name"] = None
				else:
					x["code"] = 5
					x["message"] = "Form is recognized from the config file and parsed using module"
			except Exception as err:
				logger.info("parseFromModule missing in the " + module_name + " package")
				logger.error(err)
				logger.error(
					("\nstartTrace::::" + traceback.format_exc().strip() + "::::endTrace").replace("\n", "\n$"))
				x["code"] = 3
				x["module_name"] = module_name
				x["message"] = "generic-form-parser api is off"
		return x
	except Exception as err:
		logger.error(err)
		logger.error(("\nstartTrace::::" + traceback.format_exc().strip() + "::::endTrace").replace("\n", "\n$"))
		x["code"] = 3
		x["message"] = "AE form failed to Parse"
		return x
