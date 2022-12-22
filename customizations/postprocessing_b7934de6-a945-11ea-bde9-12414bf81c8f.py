#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 11 17:52:25 2020

@author: aditya
"""
from nameparser import HumanName as hn
from dateutil import parser
import re


## NNI form

#str = "1/1/15"
#all = re.findall(r"^[\d]{1,2}/[\d]{1,2}/[\d]{2,4}$", str)
#
#for s in all:
#    print(s)



def date_format(date):
    
    # date = '10/10/2020', date = "december 2020"
    #  date = "10/10/20"    date = "10-10-20"   date = "10.10.20"
    #  date = "10/2020"  date = "1.2000"     date = "1.20"  date ="June 10, 2019"
    date_output = date
    
    if date:
        date = date.strip()
        date = date.replace("-","/")
        date = date.replace(".","/")
    
        months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        months_fullname = ["january","february","march","april","may","june","july","august","september","october","november","december"]
        
        date_pattern = re.compile(r"^[\d]{1,2}/[\d]{1,2}/[\d]{2,4}$")
        #  'Jan 18, 2020'
        pattern_mmmmddyyyy = re.compile(r"\w+\s\d{1,2},\s\d{1,4}")
        
        # partial dates  - supports mm/yyyy and mm/yy,mm/yy and m/yy
        date_pattern_partial = re.compile(r"^[\d]{1,2}/[\d]{2,4}$")
        date_splt = date.split(" ")[0].lower()
        
        if len(pattern_mmmmddyyyy.findall(date)) > 0:
            splt = date.split(" ")
            date_output = splt[1].strip(",") + "-" + splt[0] + "-" + splt[2]
        
        elif date_splt in months_fullname:
            date_output = months[months_fullname.index(date_splt)] + "-" + str(date.split(" ")[1])
            if "," in date:
                date_output =  str(date.split(" ")[1]) + "-" + months[months_fullname.index(date_splt)] + "-" + date.split(",")[-1].strip()
                date_output = date_output.replace(",","").strip().replace(".","/")
                   
        elif len(date_pattern.findall(date)) > 0:
            date_segments = parser.parse(date_pattern.findall(date)[0])
            day = date_segments.day
            mon = months[date_segments.month-1]
            yr = date_segments.year
            if int(day) < 10:
                day = "0" + str(day)        
            date_output = str(day) + "-" + str(mon) + "-" + str(yr)
        
        elif len(date_pattern_partial.findall(date)) > 0:
            mon = int(date.split("/")[0])
            yr = date.split("/")[-1]
            date_output = months[mon] + "-" + str(yr)
        else:
            date_output = date

    return date_output.upper().replace("/","-")


def product_doseinfo_start_stop_date_handling(pvi_json):
    for prod in pvi_json["products"]:
        prod_indx = pvi_json["products"].index(prod)
        for doseinfo in prod["doseInformations"]:
            doseinfo_indx = prod["doseInformations"].index(doseinfo)
            if doseinfo["customProperty_batchNumber_value"] == "Don't know":
                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["customProperty_batchNumber_value"]=""               
                
#            "started June 10, 2019"
            if doseinfo["startDate"]:
                if "started" in doseinfo["startDate"] or "starting" in doseinfo["startDate"]:
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(doseinfo["startDate"].replace("started","").replace("starting","").strip())
                if "started" in doseinfo["startDate"] and doseinfo["startDate"].count("/") == 1:
    #                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(doseinfo["startDate"].replace("started","").strip())
                    date_splt = doseinfo["startDate"].replace("started","").strip().split("/")
                    start_date = date_splt[0] 
                    end_date = date_splt[1]
                    
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(start_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(end_date)        
#                "started"  not in d and d.count("/") == 1
                if  "started"  not in doseinfo["startDate"] and doseinfo["startDate"].count("/") == 1:
                    # Start / Stop Date: 25-FEB-2020 / 26-FEB-2020
                    start_date = doseinfo["startDate"].split("/")[0]
                    end_date = doseinfo["startDate"].split("/")[1]
                    if end_date:
                        end_date = end_date.strip()
                    print("start_date=",start_date,"end_date=",end_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(start_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(end_date)        
            
                if "Don’t know" in doseinfo["startDate"]:
                    # Start / Stop Date: Don't know
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = ""
                    
                elif "," in doseinfo["startDate"] and "started" not in doseinfo["startDate"]:
                    if doseinfo["startDate"].count(",") == 1:
                        # 12-02-2020,13-02-2020
                        start_end_dates = doseinfo["startDate"].split(",")
                        pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(start_end_dates[0])
                        if doseinfo["startDate"]:
                            if doseinfo["startDate"].strip().endswith("ongoing"):
                                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = None
                                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["continuing"] = "Yes"
                        else:
                            pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(start_end_dates[1])
                else:
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(doseinfo["startDate"])
                                     
    return pvi_json

def reporterphone(pvi_json):
    for repo in pvi_json["reporters"]:
        if repo["telephone"]:
            pvi_json["reporters"][pvi_json["reporters"].index(repo)]["telephone"] = repo["telephone"].replace("-","")    
    return pvi_json

def reporter_name(pvi_json):
    for reporter in pvi_json["reporters"]:
        indx = pvi_json["reporters"].index(reporter)
        givenname = reporter["givenName"]
        
        if givenname == "<NAME REMOVED>":
            pvi_json["reporters"][indx]["firstName"] = ""
            pvi_json["reporters"][indx]["middleName"] = ""
            pvi_json["reporters"][indx]["lastName"] = ""               
        
        if givenname != None and givenname != "<NAME REMOVED>":
            repo_title = givenname.split(",")
            if repo_title:
                if len(repo_title)>1 and repo_title[-1].strip() in ["MD","Dr","DR","MD.","Dr.","DR.","MD,","Dr,","DR,"]:
                    repo_title = repo_title[-1].strip()
                    givenname = givenname.replace(repo_title,"").strip()
                    pvi_json["reporters"][indx]["title"] = repo_title

                elif len(repo_title)>1 and repo_title[0].strip() in ["MD","Dr","DR","MD.","Dr.","DR.","MD,","Dr,","DR,"]:
                    repo_title = repo_title[0].strip()
                    givenname = givenname.replace(repo_title,"").strip()
                    pvi_json["reporters"][indx]["title"] = repo_title
                elif givenname.startswith("Dr.") or givenname.startswith("DR."):
                    repo_title = "Dr"
                    givenname = givenname.replace("Dr.","").strip()
                    pvi_json["reporters"][indx]["title"] = repo_title
    
            elif givenname.startswith("Dr.") or givenname.startswith("DR."):
                repo_title = "Dr"
                givenname = givenname.replace("Dr.","").strip()
                pvi_json["reporters"][indx]["title"] = repo_title
            
            elif givenname.startswith("Dr,") or givenname.startswith("DR,"):
                repo_title = "Dr"
                givenname = givenname.replace("Dr.","").strip()
                pvi_json["reporters"][indx]["title"] = repo_title

#            name_breakup = hn(givenname)
#            if name_breakup.title:
#                pvi_json["reporters"][indx]["title"] = name_breakup.title
            
#            pvi_json["reporters"][indx]["firstName"] = name_breakup.first
#            pvi_json["reporters"][indx]["middleName"] = name_breakup.middle
#            pvi_json["reporters"][indx]["lastName"] = name_breakup.last
            if givenname:
                givenname = givenname.replace(",","").split(" ")
                f_name = ""
                m_name = ""
                l_name = ""
                
                if len(givenname)==3:
                    f_name = givenname[0]
                    m_name = givenname[1]
                    l_name = givenname[2]
                elif len(givenname)==2:
                    f_name = givenname[0]
                    l_name = givenname[1]
                else:
                    f_name = "".join(givenname)
               
                pvi_json["reporters"][indx]["firstName"] = f_name
                pvi_json["reporters"][indx]["middleName"] = m_name
                pvi_json["reporters"][indx]["lastName"] = l_name               
                    
    return pvi_json

def patient_name(pvi_json):
    if pvi_json["patient"]["name"]:
        if pvi_json["patient"]["name"].strip() in ["<INITIALS REMOVED>","<initials removed>","<removed name>","<name removed>","<NAME REMOVED>","<REMOVED NAME>"]:
    #        pvi_json["patient"]["name"] = "Privacy"         
            pvi_json["patient"]["name"] = None
    return pvi_json

def patient_age(pvi_json):
    input_val = pvi_json["patient"]["age"]["inputValue"]
    agegroup_pattern = re.compile(r"^[\d]{1,3}\u2019s")  #\u2019 is unicode
    agerange_pattern = re.compile(r"^>\d{1,3}")
    age_group = agegroup_pattern.findall(str(input_val))    
    age_range = agerange_pattern.findall(str(input_val))
    
    if input_val:
        if input_val.strip().isnumeric():
            pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue"].strip()
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"                
        elif len(age_group)>0:
#            print("\n\n inside age group")
#            print(age_group)
            #30's 
            pvi_json["patient"]["age"]["inputValue"] = age_group[0].strip("’s").strip("'s")
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE_GROUP"
        elif len(age_range)>0:     
#            print("\n\n inside age range")
#            print(age_range)                   
    #        age = ">30 years"
            if age_range[0]:
                pvi_json["patient"]["age"]["inputValue"] = age_range[0].replace(">","").strip()
                pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE_RANGE"

    return pvi_json



def fax_no(pvi_json):
    for reporter in pvi_json["reporters"]:
        fax = reporter["fax"]    
        #    fax = "1-609-514-8049 / 1-609-419-3146"
        if fax:
            if "/" in fax:
                fax = fax.split("/")   
                indx = pvi_json["reporters"].index(reporter)
                pvi_json["reporters"][indx]["fax"] = fax[0]
        
    return pvi_json

#def Events_start_stop_date(pvi_json):  
#    for event in pvi_json["events"]:
#        indx = pvi_json["events"].index(event)
#        if event["startDate"]:
#            startdate = date_format(event["startDate"])
#            pvi_json["events"][indx]["startDate"] = startdate
#        if event["endDate"]:
#            enddate = date_format(event["endDate"])
#            pvi_json["events"][indx]["endDate"] = enddate    
#    return pvi_json
    

def get_postprocessed_json(pvi_json):
    print("\n\n",pvi_json,"\n\n")
    pvi_json = reporterphone(pvi_json)
#    pvi_json = fax_no(pvi_json)
    pvi_json = patient_name(pvi_json)
    pvi_json = patient_age(pvi_json)
    pvi_json = reporter_name(pvi_json)
#    pvi_json = Events_start_stop_date(pvi_json)
    pvi_json = product_doseinfo_start_stop_date_handling(pvi_json)
    
    return pvi_json

# pvi_json = reading_json('/home/aditya/generic_poc/inputs/pdf/new_mnk/output_test.json')

# new_pvi_json = get_postprocessed_json(pvi_json)



