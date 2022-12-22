import json
import fuzzywuzzy
import re
import copy
import numpy
import pandas
import boto3
import requests
from dateutil import parser

""" for post prcessing and manipulating the json by calling a web service outside this file """
def response_from_external_ws(url, request_type, input_param=None):
    """ for sending json , body-formdata as input for request, use
    requests.post(url,json = input_param , data = input_param )"""

    if request_type == "post":
        response = requests.post(url)
    elif request_type == "get":
        response = requests.get(url)

    return response


"""method which will be called from outside by generic for post processing the json"""
def get_postprocessed_json(pvi_json, extracted_json):
    """ for post prcessing and manipulating the json by calling a web service outside this file
    formdata = {'key':value}
    pvi_json = response_from_external_ws(url ,"get" , input_param = pvi_json)
    pvi_json = response_from_external_ws(url ,"post" , input_param = pvi_json)  """

    #pvi_json = response_from_external_ws(url, "get")

    return pvi_json
