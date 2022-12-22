#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 11 17:52:25 2020

@author: aditya
"""
from pathlib import Path
from postal import parser as pp
# from nameparser import HumanName as hn
from dateutil import parser
from datetime import date, timedelta, datetime
import re
import pandas as pd
import copy
import string
import ast


## NNI form


def date_final(date_extracted):
    #    print("\n\\ndate_final-date_extracted=",date_extracted,'-- type =',type(date_extracted))
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

    year = date_extracted.year
    month = date_extracted.month
    day = date_extracted.day
    #    date_extracted = str(day) + "-" + months[int(month)] + "-" + str(year)
    date_extracted = str(day) + "-" + months[int(month) - 1] + "-" + str(year)
    #    print("f=",date_extracted)
    #    except:
    #        date_extracted = None
    return date_extracted


def approx_date(given_date_in_form):
    month_pattern = re.compile(r"\w+\s\d{1,3}\smonths\sago")
    day_pattern = re.compile(r"\d{1,3}\sdays\sago")
    week_pattern = re.compile(r"\d{1,3}\sweeks\sago")
    date_extracted = given_date_in_form

    if len(day_pattern.findall(given_date_in_form)) > 0:
        value_pattern = re.compile(r"\d{1,3}")
        days_before = value_pattern.findall(given_date_in_form)
        date_extracted = date.today() - timedelta(int(days_before[0]))

    elif len(week_pattern.findall(given_date_in_form)) > 0:
        value_pattern = re.compile(r"\d{1,3}")
        months_before = value_pattern.findall(given_date_in_form)
        date_extracted = date.today() - timedelta(int(months_before[0]) * 4)

    elif len(month_pattern.findall(given_date_in_form)) > 0:
        value_pattern = re.compile(r"\d{1,3}")
        months_before = value_pattern.findall(given_date_in_form)
        date_extracted = date.today() - timedelta(int(months_before[0]) * 30)

    if type(date_extracted) != str:
        date_extracted = date_final(date_extracted)

    return date_extracted


def date_format(form_date):
    # date = '10/10/2020', date = "december 2020"
    #  date = "10/10/20"    date = "10-10-20"   date = "10.10.20"
    #  date = "10/2020"  date = "1.2000"     date = "1.20"  date ="June 10, 2019"
    # June 19th,  04/2020
    date_output = form_date

    if form_date:
        if "ago" in form_date:
            # months ago, weeks ago, days ago format
            date_output = approx_date(form_date)
        else:
            form_date = form_date.strip()
            form_date = form_date.replace("-", "/")
            form_date = form_date.replace(".", "/")

            months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
            months_fullname = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
                               "october", "november", "december"]

            date_pattern = re.compile(r"^[\d]{1,2}/[\d]{1,2}/[\d]{2,4}$")
            month_date_only_pattern = re.compile(r"^\w+\s\d{1,2}th|^\w+\s\d{1,2}rd|^\w+\s\d{1,2}st")
            #  'Jan 18, 2020'
            pattern_mmmmddyyyy = re.compile(r"^\w+\s\d{1,2},\s\d{1,4}")
            monthnumber_year_format = re.compile(r"^\d{1,2}/\d{2,4}$")
            # partial dates  - supports mm/yyyy and mm/yy and m/yy
            date_pattern_partial = re.compile(r"^[\d]{1,2}/[\d]{2,4}$")
            M_DD_YY_pattern = re.compile(r"^\d{1}-\d{2}-\d{2}")
            daymonthnumber_year_format1 = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")  # 21/04/2020

            space_pattenn = re.compile(r"^\d{1,2}\s\w+\s\d{2,4}$")  # 24 APR 2020

            date_splt = form_date.split(" ")[0].lower()

            if len(M_DD_YY_pattern.findall(form_date)) > 0:
                date_splt = form_date.split("-")
                mnth = months[int(date_splt[0].strip()) - 1]
                day = date_splt[1].strip()
                yr = date_splt[2].strip()
                date_output = day + "-" + mnth + "-20" + yr

            elif len(space_pattenn.findall(form_date)) > 0:
                dt = str(form_date.split(" ")[0].strip())
                mnth = form_date.split(" ")[1].strip()
                yr = form_date.split(" ")[2].strip()
                if len(yr) == 2:
                    yr = "20" + yr
                if len(dt) == 1:
                    dt = "0" + dt
                date_output = dt + "-" + mnth + "-" + yr

            elif len(daymonthnumber_year_format1.findall(form_date)) > 0:
                dt = str(form_date.split("/")[0].strip())
                mnth = int(form_date.split("/")[1].strip()) - 1
                yr = form_date.split("/")[2].strip()
                if len(yr) == 2:
                    yr = "20" + yr
                if len(dt) == 1:
                    dt = "0" + dt
                date_output = dt + "-" + months[mnth] + "-" + yr

            elif len(monthnumber_year_format.findall(form_date)) > 0:
                mnth = int(form_date.split("/")[0].strip()) - 1
                yr = form_date.split("/")[1].strip()
                if len(yr) == 2:
                    yr = "20" + yr
                date_output = months[mnth] + "-" + yr

            elif len(month_date_only_pattern.findall(form_date)) > 0:
                splt = form_date.lower().split(" ")
                date_output = splt[1].strip(",").replace("st", "").replace("nd", "").replace("rd", "").replace("th",
                                                                                                               "") + "-" + \
                              months[months_fullname.index(splt[0])]
                currentMonth = datetime.now().month
                form_month = months_fullname.index(splt[0])
                year = "-2020"
                if form_month >= currentMonth:
                    year = "-2019"
                date_output = date_output + year

            elif len(pattern_mmmmddyyyy.findall(form_date)) > 0:
                splt = form_date.split(" ")
                if splt[0].upper() in months:
                    date_output = splt[1].strip(",") + "-" + splt[0] + "-" + splt[2]
                elif splt[0].lower() in months_fullname:
                    date_output = splt[1].strip(",") + "-" + months[months_fullname.index(splt[0].lower())] + "-" + \
                                  splt[2]

            elif date_splt in months_fullname:
                date_output = months[months_fullname.index(date_splt)] + "-" + str(form_date.split(" ")[1])
                if "," in form_date:
                    date_output = str(form_date.split(" ")[1]) + "-" + months[months_fullname.index(date_splt)] + "-" + \
                                  form_date.split(",")[-1].strip()
                    date_output = date_output.replace(",", "").strip().replace(".", "/")

            elif len(date_pattern.findall(form_date)) > 0:
                date_segments = parser.parse(date_pattern.findall(form_date)[0])
                day = date_segments.day
                mon = months[date_segments.month - 1]
                yr = date_segments.year
                if int(day) < 10:
                    day = "0" + str(day)
                if len(yr) == 2:
                    yr = "20" + yr
                date_output = str(day) + "-" + str(mon) + "-" + str(yr)

            elif len(date_pattern_partial.findall(form_date)) > 0:
                mon = int(form_date.split("/")[0]) - 1
                yr = form_date.split("/")[-1]
                if len(yr) == 2:
                    yr = "20" + yr
                date_output = months[mon] + "-" + str(yr)
            else:
                date_output = form_date

    output = None
    if date_output:
        output = date_output.upper().replace("/", "-")
        if output:
            op_splt = output.split("-")
            if len(op_splt) == 3:
                if len(op_splt[0]) == 1:
                    output = '0' + output
                if len(op_splt[2]) == 2:
                    output = output.split("-")[0] + "-" + output.split("-")[1] + "-20" + output.split("-")[2]
            if len(op_splt) == 2:
                if len(op_splt[0]) == 1:
                    output = '0' + output
                if len(op_splt[1]) == 2:
                    output = output.split("-")[0] + "-20" + output.split("-")[-1]

    mon_space_yyyy = re.compile(r"^\w+\s\d{4}")
    find_ptn1 = mon_space_yyyy.findall(output)
    if len(find_ptn1) > 0:
        output = output.split(" ")[0] + "-" + output.split(" ")[1]
        output = output.upper()

    return output


def product_doseinfo_start_stop_date_handling(pvi_json):
    # \w+\s\d{1,2}st|\w+\s\d{1,2}nd|\w+\s\d{1,2}rd|\w+\s\d{1,2}th  -> June 20th,  June 1st,   june 2nd
    dt_ptn = re.compile(r"^\d+\s\w+\s\d{4}\s*/\s*\d+\s\w+\s\d{4}$")
    yyyy_ptn = re.compile(r"^\d{4}$")
    yyyy_slash_yyyy_ptn = re.compile(r"^\d{4}\s*/\s*\d{4}$")

    dot_ptn = re.compile(r"^\d{1,2}[.]\d{1,2}[.]\d{2,4}-\d{1,2}[.]\d{1,2}[.]\d{2,4}$")  # 7.11.19-1.3.2020
    dot_and_slash_ptn = re.compile(r"^\d{1,2}[.]\d{1,2}[.]\d{2,4}/\d{1,2}[.]\d{1,2}[.]\d{2,4}$")  # 7.11.19/1.3.2020

    ptn_new = re.compile(r"^\d{1,2}-\d{1,2}-\d{2}\s*/\s*\d{1,2}-\d{1,2}-\d{2}$")  # 05-24-20/5-21-20

    empty_slash_ptn = re.compile(r"^\d{1,2}\s\w+\s\d{2,4}\s*/\s*\d{1,2}\s\w+\s\d{2,4}$")  # 24 Apr 2020/21 May 2020

    for prod in pvi_json["products"]:
        prod_indx = pvi_json["products"].index(prod)
        for doseinfo in prod["doseInformations"]:
            doseinfo_indx = prod["doseInformations"].index(doseinfo)
            # -----------
            if doseinfo["customProperty_batchNumber_value"]:
                batchno = doseinfo["customProperty_batchNumber_value"].split("||")[0].strip()
                expiry_date = doseinfo["customProperty_batchNumber_value"].split("||")[1]
                if expiry_date:
                    expiry_date = expiry_date.strip()
                    expiry_date = date_format(expiry_date)
                if batchno in ["", "Don't know", "No", "Did not report", "don't know",
                               "no", "did not report"]:
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx][
                        "customProperty_batchNumber_value"] = "UNKNOWN" + "||" + expiry_date
                else:
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx][
                        "customProperty_batchNumber_value"] = str(batchno) + "||" + expiry_date
            # -----------

            if doseinfo["startDate"]:
                if len(dot_and_slash_ptn.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("/")
                    sdate = dt_splt[0].strip().split(".")[1] + '-' + dt_splt[0].strip().split(".")[0] + "-" + \
                            dt_splt[0].strip().split(".")[2]
                    edate = dt_splt[1].strip().split(".")[1] + '-' + dt_splt[1].strip().split(".")[0] + "-" + \
                            dt_splt[1].strip().split(".")[2]
                    #                    print("space_slash=",edate)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(sdate)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(edate)

                elif len(empty_slash_ptn.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("/")

                    sdate = dt_splt[0].strip().split(" ")[0] + '-' + dt_splt[0].split(" ")[1] + "-" + \
                            dt_splt[0].split(" ")[2]
                    edate = dt_splt[1].strip().split(" ")[0] + '-' + dt_splt[1].strip().split(" ")[1] + "-" + \
                            dt_splt[1].strip().split(" ")[2]

                    #                    print("space_slash=",edate)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = sdate.upper()
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = edate.upper()

                elif len(ptn_new.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("/")
                    sdate = dt_splt[0].strip().split("-")[1] + '/' + dt_splt[0].strip().split("-")[0] + "/" + \
                            dt_splt[0].strip().split("-")[2]
                    edate = dt_splt[1].strip().split("-")[1] + '/' + dt_splt[1].strip().split("-")[0] + "/" + \
                            dt_splt[1].strip().split("-")[2]

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(sdate)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(edate)

                elif len(dot_ptn.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("-")

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(
                        dt_splt[0])
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(
                        dt_splt[1])

                elif len(yyyy_slash_yyyy_ptn.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("/")

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = dt_splt[0].upper()
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = dt_splt[1].upper()
                elif len(yyyy_ptn.findall(doseinfo["startDate"])):
                    # YYYY
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = doseinfo[
                        "startDate"]

                elif len(dt_ptn.findall(doseinfo["startDate"])):
                    # 12 Aug 2019/13 Sep 2019
                    sdate = doseinfo.split("/")[0].strip()
                    sdate = sdate.split(" ")[0] + "-" + sdate.split(" ")[1] + "-" + sdate.split(" ")[2]
                    edate = doseinfo.split("/")[1].strip()
                    edate = edate.split(" ")[0] + "-" + edate.split(" ")[1] + "-" + edate.split(" ")[2]

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = sdate.upper()
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = edate.upper()
                # "started June 10, 2019"
                elif "started" in doseinfo["startDate"] or "starting" in doseinfo["startDate"]:
                    print("in started")
                    print("start date=",
                          pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"])
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(
                        doseinfo["startDate"].replace("started", "").replace("starting", "").strip())
                elif "started" in doseinfo["startDate"] and doseinfo["startDate"].count("/") == 1:
                    date_splt = doseinfo["startDate"].replace("started", "").strip().split("/")
                    start_date = date_splt[0]
                    end_date = date_splt[1]

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(
                        start_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(
                        end_date)
                #                "started"  not in d and d.count("/") == 1
                elif "started" not in doseinfo["startDate"] and doseinfo["startDate"].count("/") == 1:
                    # Start / Stop Date: 25-FEB-2020 / 26-FEB-2020
                    start_date = doseinfo["startDate"].split("/")[0]
                    end_date = doseinfo["startDate"].split("/")[1]
                    if end_date:
                        end_date = end_date.strip()
                    #                    print("start_date=",start_date,"end_date=",end_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(
                        start_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(
                        end_date)

                elif "Don’t know" in doseinfo["startDate"]:
                    # Start / Stop Date: Don't know
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = ""

                elif "," in doseinfo["startDate"] and "started" not in doseinfo["startDate"]:
                    if doseinfo["startDate"].count(",") == 1:
                        # 12-02-2020,13-02-2020
                        start_end_dates = doseinfo["startDate"].split(",")
                        pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(
                            start_end_dates[0])
                        if doseinfo["startDate"]:
                            if doseinfo["startDate"].strip().endswith("ongoing"):
                                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = None
                                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["continuing"] = "Yes"
                        else:
                            pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(
                                start_end_dates[1])
                else:
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(
                        doseinfo["startDate"])
    return pvi_json


def reporter_name(pvi_json):
    for reporter in pvi_json["reporters"]:
        f_name = None
        m_name = None
        l_name = None
        title = None
        indx = pvi_json["reporters"].index(reporter)
        givenname = reporter["givenName"]

        if givenname in ["<NAME REMOVED>", "<REMOVED NAME>", "", "blank"]:
            pvi_json["reporters"][indx]["givenName"] = "Unknown"
            pvi_json["reporters"][indx]["firstName"] = "Unknown"
            #            pvi_json["reporters"][indx]["middleName"] = "UNKNOWN"
            pvi_json["reporters"][indx]["lastName"] = "Unknown"

        elif givenname != None and givenname != "<NAME REMOVED>" and givenname != "<REMOVED NAME>" and givenname != "blank":
            if givenname.startswith("Dr.") == True or givenname.startswith("Dr") == True:
                givenname = givenname.replace("Dr.", "").strip()

            givenname = givenname.split(" ")
            if len(givenname) == 2:
                f_name = givenname[0].replace(",", "")
                l_name = givenname[-1]

            elif len(givenname) == 3:
                f_name = givenname[0].replace(",", "")
                m_name = givenname[1]
                l_name = givenname[-1]

            #            pvi_json["reporters"][indx]["title"] = title
            pvi_json["reporters"][indx]["firstName"] = f_name
            if l_name:
                if l_name == "MD":
                    m_name = m_name + " " + l_name
                    pvi_json["reporters"][indx]["middleName"] = m_name
                else:
                    pvi_json["reporters"][indx]["middleName"] = m_name
                    pvi_json["reporters"][indx]["lastName"] = l_name

    return pvi_json


def patient_name(pvi_json):
    if pvi_json["patient"]["name"]:
        if pvi_json["patient"]["name"].strip() in ["<INITIALS REMOVED>", "<removed initials>", "<REMOVED INITIALS>",
                                                   "<REMOVED NAME>", "<removed name>", "not reported", "<name removed>",
                                                   "<NAME REMOVED>", "n/a"]:
            pvi_json["patient"]["name"] = "UNKNOWN"
    else:
        pvi_json["patient"]["name"] = "UNKNOWN"

    return pvi_json


def patient_age(pvi_json):
    input_val = pvi_json["patient"]["age"]["inputValue"]
    agegroup_pattern = re.compile(r"\d{1,3}'s|\d{1,3}’s|[\d]{1,3}\u2019s")  # \u2019 is unicode  for single quote
    agerange_pattern = re.compile(r"^>\d{1,3}")
    age_group = agegroup_pattern.findall(str(input_val))
    age_range = agerange_pattern.findall(str(input_val))
    dob_pattern = re.compile(r"\d{2}-\w+-\d{2,4}")
    dob_pattern_finder = dob_pattern.findall(str(input_val))

    age_ptn = re.compile(r"\d{2} Years")  # 50 Years
    age_ptn_finder = age_ptn.findall(str(input_val))

    years_old = re.compile(r"\w+\s\d{2}\syears old")
    year_old_ptn = years_old.findall(str(input_val))

    ddmyy = re.compile(r"\d{1,2}\\\d{1,2}\\\d{2,4}")  # dd/mormm/yyoryyyy
    ddmyy_ptn = ddmyy.findall(str(input_val))

    if input_val:
        if len(ddmyy_ptn) > 0:
            pvi_json["patient"]["age"]["inputValue"] = date_format(ddmyy_ptn[0])
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_BIRTH_DATE"
        elif len(age_group) > 0:
            # 30's
            pvi_json["patient"]["age"]["inputValue"] = age_group[0].replace("’s", "").replace("'s", "")
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_AGE_GROUP"  # "PATIENT_ON_SET_AGE"
        elif len(dob_pattern_finder) > 0:
            pvi_json["patient"]["age"]["inputValue"] = dob_pattern_finder[0]
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_BIRTH_DATE"
        elif len(year_old_ptn) > 0:
            age = pvi_json["patient"]["age"]["inputValue"].strip()
            getage = re.compile(r"\d{2}")
            agefound = getage.findall(age)
            pvi_json["patient"]["age"]["inputValue"] = agefound[0] + " years"
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"
        elif len(age_ptn_finder) > 0:
            pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue"].strip()
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"
        elif input_val.strip().isnumeric():
            pvi_json["patient"]["age"]["inputValue"] = pvi_json["patient"]["age"]["inputValue"].strip() + " years"
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"
        elif len(dob_pattern_finder) == 0 and len(age_ptn_finder) == 0 and input_val.strip().isnumeric() == False:
            pvi_json["patient"]["age"]["inputValue"] = input_val
            pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"

        elif len(age_range) > 0:
            #            print("\n\n inside age range")
            #            print(age_range)
            #        age = ">30 years"
            if age_range[0]:
                pvi_json["patient"]["age"]["inputValue"] = age_range[0].replace(">", "").strip() + " years"
                pvi_json["patient"]["age"]["ageType"] = "PATIENT_ON_SET_AGE"

    return pvi_json


def dose_stop_date(pvi_json):
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    months_fullname = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                       "november", "december"]

    for prod in pvi_json["products"]:
        prod_indx = pvi_json["products"].index(prod)
        for doseinfo in prod["doseInformations"]:
            doseinfo_indx = prod["doseInformations"].index(doseinfo)
            #            sdate = pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"]
            edate = pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"]

            if edate:
                edate = date_format(edate)
                if len(edate.split("-")) == 3:
                    if edate.split("-")[1].lower() in months_fullname:
                        mon = months[months_fullname.index(edate.split("-")[1].lower())]
                        edate = edate.split("-")[0] + "-" + mon + "-" + edate.split("-")[2]
                elif len(edate.split("-")) == 2:
                    if edate.split("-")[0].lower() in months_fullname:
                        mon = months[months_fullname.index(edate.split("-")[0].lower())]
                        edate = edate.split("-")[0] + "-" + mon + "-" + edate.split("-")[1]

                print("edate=", edate, "\n")
                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = edate.upper()

            #            if sdate:
            #                if "still taking therapy" in sdate.lower().strip() or "no change" in sdate.lower().strip() or "ongoing" in sdate.lower().strip() or "currently taking" in sdate.lower().strip():
            #                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = None
            #                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["continuing"] = "Yes"
            if edate:
                if "still taking therapy" in edate.lower().strip() or "no change" in edate.lower().strip() or "ongoing" in edate.lower().strip() or "currently taking" in edate.lower().strip():
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = None
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["continuing"] = "Yes"

    return pvi_json


def get_address(address_str):
    address = pp.parse_address(address_str)
    address_dict = {}
    for addr_segment in address:
        addr_key = addr_segment[1]
        if addr_key == 'house':
            addr_key = 'building'
        if addr_key == 'house_number':
            addr_key = 'building_number'
        if addr_key == 'road':
            addr_key = 'street'

        address_dict[addr_key] = addr_segment[0]
    address_dict = convert_case(address_dict)
    return address_dict


def convert_case(address_dict):
    for key, val in address_dict.items():
        if key == "country":
            address_dict[key] = val.upper()
        else:
            address_dict[key] = val.title()
    return address_dict


def reporter_address(pvi_json):
    for rep in pvi_json["reporters"]:
        if bool(rep["country"]) == True or rep["country"] != "" or rep[
            "country"] != None:  # rporter country holds entire address so apply address parser
            indx = pvi_json["reporters"].index(rep)
            if rep["country"]:
                address = pd.DataFrame(pp.parse_address(rep["country"]))
                #                print("\naddress=",address)
                if not address.empty:
                    house_number = address[address[1] == 'house_number']
                    house = address[address[1] == 'house']
                    road = address[address[1] == 'road']
                    street = address[address[1] == 'street']
                    city = address[address[1] == 'city']
                    state = address[address[1] == 'state']
                    country = address[address[1] == 'country']
                    postcode = address[address[1] == 'postcode']

                    street_info = ""
                    if not house_number.empty:
                        street_info = street_info + house_number.iloc[0][0]
                    if not house.empty:
                        street_info = street_info + house.iloc[0][0]
                        street_info = street_info.strip()
                    if not road.empty:
                        street_info = street_info + " " + road.iloc[0][0]
                        street_info = street_info.strip()

                    if not street.empty:
                        street_info = street_info + " " + street.iloc[0][0]
                        street_info = street_info.strip()

                    pvi_json["reporters"][indx]['street'] = street_info.title()

                    if not city.empty:
                        pvi_json["reporters"][indx]['city'] = city.iloc[0][0].title()
                    if not state.empty:
                        pvi_json["reporters"][indx]['state'] = state.iloc[0][0].upper()

                    if not postcode.empty:
                        pvi_json["reporters"][indx]['postcode'] = postcode.iloc[0][0]

                    pvi_json["reporters"][indx]['country'] = ""

                    if not country.empty:
                        pvi_json["reporters"][indx]['country'] = country.iloc[0][0].upper()

    return pvi_json


def increment_product_seq_no(pvi_json):
    for prod in pvi_json["products"]:
        prodindx = pvi_json["products"].index(prod)
        pvi_json["products"][prodindx]["seq_num"] = prodindx + 1
    return pvi_json


def handling_same_products_doseinfo(pvi_json):
    all_products = copy.deepcopy(pvi_json["products"])
    prod_names = []
    for prod in all_products:
        prod_names.append(prod["license_value"])

    prod_names = list(set(prod_names))

    grouping_prod = {}
    for name in prod_names:
        for indx in range(0, len(all_products)):
            if name == all_products[indx]["license_value"]:
                val = indx
                if name in grouping_prod.keys():
                    existing_val = grouping_prod[name]
                    grouping_prod[name] = str(existing_val) + ":" + str(val)
                else:
                    grouping_prod[name] = str(val)

    grouping_doseinfo = []
    for key in grouping_prod.keys():
        val = grouping_prod[key].split(":")
        #        print(val)
        if len(val) == 1:
            grouping_doseinfo.append(pvi_json["products"][int(val[0])])
        elif len(val) > 1:
            for indx in range(0, len(val)):
                if indx == 0:
                    partial = pvi_json["products"][int(val[indx])]
                else:
                    #                    print('partial=',partial)
                    dose = pvi_json["products"][int(val[indx])]["doseInformations"][0]
                    info = partial["doseInformations"]
                    info.append(dose)
                    partial["doseInformations"] = info

            grouping_doseinfo.append(partial)

    pvi_json["products"] = grouping_doseinfo

    return pvi_json


def expiry_date_new(given_date):
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    months_fullname = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                       "november", "december"]

    dt_ptn = re.compile(r"^\d+\s\w+\s\d{4}\s*$")  # 01 jan 2010

    yyyy_ptn = re.compile(r"^\d{4}$")  # YYYY

    dot_ptn = re.compile(r"^\d{1,2}[.]\d{1,2}[.]\d{2,4}")  # 7.11.19

    ptn_new = re.compile(r"^\d{1,2}-\d{1,2}-\d{2,4}\s*$")  # 05-24-20

    ptn_2 = re.compile(r"^\d{1,2}\s\w+\s\d{4}")  # 24 Apr 2020

    mnth_yyyy = re.compile(r"^\w+[-]\d{4}$")  # "JAN-2020"

    if len(dt_ptn.findall(given_date)) > 0:  # 01 jan 2010
        dt = str(given_date.split(" ")[0])
        mon = given_date.split(" ")[1]
        yr = str(given_date.split(" ")[2])
        if len(dt) == 1:
            dt = "0" + dt
        if len(yr) == 2:
            yr = "20" + yr

        if mon.lower() in months_fullname:
            df_final = dt + "-" + months[months_fullname.index(mon.lower())] + "-" + yr
        elif mon.upper() in months:
            df_final = dt + "-" + mon.upper() + "-" + yr
        else:
            df_final = dt + "-" + mon.upper() + "-" + yr

    elif len(yyyy_ptn.findall(given_date)) > 0:
        df_final = given_date

    elif len(dot_ptn.findall(given_date)) > 0:  # 7.11.19
        mon = int(given_date.split(".")[0])
        dt = str(given_date.split(".")[1])
        yr = str(given_date.split(".")[2])
        if len(yr) == 2:
            yr = "20" + yr

        if len(dt) == 1:
            dt = "0" + dt
        df_final = dt + "-" + months[mon - 1] + "-" + yr

    elif len(ptn_new.findall(given_date)) > 0:  # 05-24-20
        mon = int(given_date.split("-")[0])
        dt = str(given_date.split("-")[1])
        yr = str(given_date.split("-")[2])
        if len(yr) == 2:
            yr = "20" + yr
        if len(dt) == 1:
            dt = "0" + dt
        df_final = dt + "-" + months[mon - 1] + "-" + yr

    elif len(ptn_2.findall(given_date)) > 0:  # 24 Apr 2020
        dt = str(given_date.split(" ")[0])
        mon = given_date.split(" ")[1]
        yr = str(given_date.split(" ")[2])

        if len(yr) == 2:
            yr = "20" + yr

        if len(dt) == 1:
            dt = "0" + dt
        if mon.lower() in months_fullname:
            mon = months[months_fullname.index(mon.lower()) - 1]
        elif mon.upper() in months:
            mon = mon.upper()

        df_final = dt + "-" + mon + "-" + yr

    elif len(mnth_yyyy.findall(given_date)) > 0:  # Apr 2020
        mon = given_date.split("-")[0]
        yr = str(given_date.split("-")[1])
        df_final = mon.upper() + "-" + str(yr)

    else:
        df_final = given_date.upper()
    return df_final


def get_postprocessed_json(pvi_json, key_val_json):
    print("\n\npvi_json = ", pvi_json, "\n\n")
    print("key_val_json = ", key_val_json)
    try:
        pvi_json = patient_name(pvi_json)
    except Exception as e:
        print("ERROR IN patient_name : \n", e)
        pass
    try:
        pvi_json = patient_age(pvi_json)
    except Exception as e:
        print("ERROR IN patient_age : \n", e)
        pass
    try:
        pvi_json = reporter_name(pvi_json)
    except Exception as e:
        print("ERROR IN reporter_name: \n", e)
        pass
    try:
        pvi_json = reporter_address(pvi_json)
    except Exception as e:
        print("ERROR IN reporter_address : \n", e)
        pass

    try:
        print("in dose infor")
        pvi_json = product_doseinfo_start_stop_date_handling(pvi_json)
    except Exception as e:
        print("ERROR IN product_doseinfo_start_stop_date_handling : \n", e)
        pass

    try:
        pvi_json = dose_stop_date(pvi_json)  # keep it here only
    except Exception as e:
        print("ERROR IN dose_stop_date : \n", e)
        pass

    pvi_json = handling_same_products_doseinfo(pvi_json)
    pvi_json = increment_product_seq_no(pvi_json)

    pvi_json["sourceType"][0]["value"] = "Spontaneous"

    pvi_json["summary"]["caseDescription"] = pvi_json["summary"]["caseDescription"].replace("<empty>", "")

    print("\n\npvi_json = ", pvi_json, "\n\n")

    return pvi_json
