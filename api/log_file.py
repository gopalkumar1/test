import logging
from logging.config import fileConfig
from logging.handlers import TimedRotatingFileHandler
from os import path
import configparser
import importlib

py_path = "/".join(path.dirname(path.abspath(__file__)).split("/") + ["extdata"])

log_file_name = py_path + "/logdir/pvi-form-engine.log"
fileConfig(
	path.join("/".join(path.dirname(path.abspath(__file__)).split("/") + ["extdata", "config"]), "log_config.ini"),
	disable_existing_loggers=True)
logger = logging.getLogger("apiLogger")

file_handler = TimedRotatingFileHandler(log_file_name, "D", 3, 10)

logger.addHandler(file_handler)
config = configparser.ConfigParser()
config.read(py_path + "/config/config.ini")

ImportModuleName = "py_comm_comp"
ImportModulePath = "/".join(path.dirname(path.abspath(__file__)).split("/")[:-1] + [ImportModuleName, "__init__.py"])
spec = importlib.util.find_spec(ImportModuleName)
if spec is None:
	spec = importlib.util.spec_from_loader(ImportModuleName,
										   importlib.machinery.SourceFileLoader(ImportModuleName, ImportModulePath))
pqc_ae_model = spec.submodule_search_locations[0] + "/extdata/model/quantized_category.ftz"
spam_model = spec.submodule_search_locations[0] + "/extdata/model/model_spam.ftz"
py_comm_comp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(py_comm_comp)
