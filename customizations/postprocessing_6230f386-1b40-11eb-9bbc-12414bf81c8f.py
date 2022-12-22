import re
from datetime import date, timedelta, datetime
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


def final_report_time(pvi_json):
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    try:
        if (pvi_json["receiptDate"]):
            date_utc = datetime.strptime(pvi_json["receiptDate"], '%a %b %d %H:%M:%S %Z %Y')
            date_est = date_utc - timedelta(hours=4)
            day = date_est.day
            mon = months[date_est.month - 1]
            yea = date_est.year
            pvi_json["receiptDate"] = str(day) + "-" + str(mon) + "-" + str(yea)
            pvi_json["mostRecentReceiptDate"] = pvi_json["receiptDate"]
    except:
        pass
    return pvi_json


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
    month_pattern = re.compile(r"\d{1,3}\smonths\sago")
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
            months_fullname = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

            date_pattern = re.compile(r"^[\d]{1,2}/[\d]{1,2}/[\d]{2,4}$")
            month_date_only_pattern = re.compile(r"^\w+\s\d{1,2}th|^\w+\s\d{1,2}rd|^\w+\s\d{1,2}st")
            #  'Jan 18, 2020'
            pattern_mmmmddyyyy = re.compile(r"^\w+\s\d{1,2},\s\d{1,4}")
            monthnumber_year_format = re.compile(r"^\d{1,2}/\d{2,4}")
            # partial dates  - supports mm/yyyy and mm/yy and m/yy
            date_pattern_partial = re.compile(r"^[\d]{1,2}/[\d]{2,4}$")
            M_DD_YY_pattern = re.compile(r"^\d{1}-\d{2}-\d{2}")
            date_pattern_new = re.compile(r"^[\d]{1,2}\s\w+\s[\d]{2,4}$")

            date_splt = form_date.split(" ")[0].lower()
            print(date_pattern.findall(form_date))

            if len(M_DD_YY_pattern.findall(form_date)) > 0:
                date_splt = form_date.split("-")
                mnth = months[int(date_splt[0].strip()) - 1]
                day = date_splt[1].strip()
                yr = date_splt[2].strip()
                date_output = day + "-" + mnth + "-20" + yr

            elif len(monthnumber_year_format.findall(form_date)) > 0 and len(form_date) == 7:
                mnth = int(form_date.split("/")[0].strip()) - 1
                yr = form_date.split("/")[1].strip()
                date_output = months[mnth] + "-" + yr

            elif len(month_date_only_pattern.findall(form_date)) > 0:
                splt = form_date.lower().split(" ")
                date_output = splt[1].strip(",").replace("st", "").replace("nd", "").replace("rd", "").replace("th", "") + "-" + months[months_fullname.index(splt[0])]
                currentMonth = datetime.now().month
                form_month = months_fullname.index(splt[0])
                year = "-2020"
                if form_month >= currentMonth:
                    year = "-2019"
                date_output = date_output + year

            elif len(pattern_mmmmddyyyy.findall(form_date)) > 0:
                splt = form_date.split(" ")
                date_output = splt[1].strip(",") + "-" + splt[0] + "-" + splt[2]

            elif date_splt in months_fullname:
                date_output = months[months_fullname.index(date_splt)] + "-" + str(form_date.split(" ")[1])
                if "," in form_date:
                    date_output = str(form_date.split(" ")[1]) + "-" + months[months_fullname.index(date_splt)] + "-" + form_date.split(",")[-1].strip()
                    date_output = date_output.replace(",", "").strip().replace(".", "/")

            elif len(date_pattern.findall(form_date)) > 0:
                date_segments = parser.parse(date_pattern.findall(form_date)[0])
                day = date_segments.day
                mon = months[date_segments.month - 1]
                yr = date_segments.year
                if int(day) < 10:
                    day = "0" + str(day)
                date_output = str(day) + "-" + str(mon) + "-" + str(yr)

            elif len(date_pattern_partial.findall(form_date)) > 0:
                mon = int(form_date.split("/")[0]) - 1
                yr = form_date.split("/")[-1]
                date_output = months[mon] + "-" + str(yr)

            elif len(date_pattern_new.findall(form_date)) > 0:
                day = form_date.split(" ")[0]
                mon = form_date.split(" ")[1].lower()
                yr = form_date.split(" ")[2]
                if mon in months_fullname:
                    index = months_fullname.index(mon)
                    mon = months[index]
                if len(day) == 1:
                    day = "0" + str(day)
                date_output = str(day) + "-" + str(mon) + "-" + str(yr)

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


"""
12 Aug 2019/13 Sep 2019
"started June 10, 2019"
25-FEB-2020 / 26-FEB-2020
Don't know
12-02-2020,13-02-2020
'Jan 18, 2020'
'10/10/2020',  "december 2020"
"10/10/20"
"10-10-20"
"10.10.20"
"10/2020"
"1.2000"
"1.20"
"June 10, 2019"
June 19th,  04/2020
3 months ago, 2 weeks ago, ongoing, currently taking, still taking therapy

"""


def product_doseinfo_start_stop_date_handling(pvi_json):
    # \w+\s\d{1,2}st|\w+\s\d{1,2}nd|\w+\s\d{1,2}rd|\w+\s\d{1,2}th  -> June 20th,  June 1st,   june 2nd    
    dt_ptn = re.compile(r"^\d+\s\w+\s\d{4}\s*/\s*\d+\s\w+\s\d{4}$")
    yyyy_ptn = re.compile(r"^\d{4}$")
    yyyy_slash_yyyy_ptn = re.compile(r"^\d{4}\s*/\s*\d{4}")

    dot_ptn = re.compile(r"^\d{1,2}[.]\d{1,2}[.]\d{2,4}-\d{1,2}[.]\d{1,2}[.]\d{2,4}")  # 7.11.19-1.3.2020

    ptn_new = re.compile(r"^\d{1,2}-\d{1,2}-\d{2}\s*/\s*\d{1,2}-\d{1,2}-\d{2}$")  # 05-24-20/5-21-20

    for prod in pvi_json["products"]:
        prod_indx = pvi_json["products"].index(prod)
        for doseinfo in prod["doseInformations"]:
            doseinfo_indx = prod["doseInformations"].index(doseinfo)
            if doseinfo["customProperty_batchNumber_value"] in ["", "Don't know", "No", "Did not report", "don't know", "no", "did not report"]:
                pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["customProperty_batchNumber_value"] = "UNKNOWN"

            if doseinfo["startDate"]:
                if len(ptn_new.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("/")
                    sdate = dt_splt[0].split("-")[1] + '/' + dt_splt[0].split("-")[0] + "/" + dt_splt[0].split("-")[2]
                    edate = dt_splt[1].split("-")[1] + '/' + dt_splt[1].split("-")[0] + "/" + dt_splt[1].split("-")[2]

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(sdate)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(edate)

                elif len(dot_ptn.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("-")

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(dt_splt[0])
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(dt_splt[1])

                elif len(yyyy_slash_yyyy_ptn.findall(doseinfo["startDate"])) > 0:
                    dt_splt = doseinfo["startDate"].split("/")

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = dt_splt[0].upper()
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = dt_splt[1].upper()
                elif len(yyyy_ptn.findall(doseinfo["startDate"])):
                    # YYYY
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = doseinfo["startDate"]

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
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(doseinfo["startDate"].replace("started", "").replace("starting", "").strip())
                elif "started" in doseinfo["startDate"] and doseinfo["startDate"].count("/") == 1:
                    date_splt = doseinfo["startDate"].replace("started", "").strip().split("/")
                    start_date = date_splt[0]
                    end_date = date_splt[1]

                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(start_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(end_date)
                #                "started"  not in d and d.count("/") == 1
                elif "started" not in doseinfo["startDate"] and doseinfo["startDate"].count("/") == 1:
                    # Start / Stop Date: 25-FEB-2020 / 26-FEB-2020
                    start_date = doseinfo["startDate"].split("/")[0]
                    end_date = doseinfo["startDate"].split("/")[1]
                    if end_date:
                        end_date = end_date.strip()
                    #                    print("start_date=",start_date,"end_date=",end_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["startDate"] = date_format(start_date)
                    pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(end_date)

                elif "Don’t know" in doseinfo["startDate"]:
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
                    if pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"]:
                        pvi_json["products"][prod_indx]["doseInformations"][doseinfo_indx]["endDate"] = date_format(doseinfo["endDate"])

    return pvi_json


def processReporterExtractedName(pvi_json):
    titles = ['dr', 'mr', 'mrs', 'miss', 'ms']
    for reporter in pvi_json["reporters"]:
        if reporter["givenName"]:
            reporterGivenName = reporter["givenName"].split()
            print("reporterGivenName=", reporterGivenName)
            print("given = ", reporter["givenName"])

            if reporter["givenName"].replace('.', '').split()[0].lower() in titles:
                reporterGivenNameLength = len(reporterGivenName)
                if reporterGivenNameLength == 1:
                    reporter["title"] = reporterGivenName[0]
                elif reporterGivenNameLength == 2:
                    reporter["title"] = reporterGivenName[0]
                    reporter["firstName"] = reporterGivenName[1]
                else:
                    reporter["title"] = reporterGivenName[0]
                    reporter["firstName"] = reporterGivenName[1]
                    reporter["lastName"] = ' '.join(reporterGivenName[2:])
            else:
                reporterGivenNameLength = len(reporterGivenName)
                if reporterGivenNameLength == 1:
                    reporter["firstName"] = reporterGivenName[0]
                else:
                    reporter["firstName"] = reporterGivenName[0]
                    reporter["lastName"] = ' '.join(reporterGivenName[1:])
    return pvi_json

def event_dates_format(pvi_json):
    events_all = []
    for event in pvi_json["events"]:
        print("s=",event["startDate"])
        print("e=", event["endDate"])
        sdate = event["startDate"]
        edate = event["endDate"]
        if event["startDate"]:
            sdate = date_format(event["startDate"])
        if event["endDate"]:
            edate = date_format(event["endDate"])
            print("edate=", edate)
        event["startDate"] = sdate
        event["endDate"] = edate

        events_all.append(event)
    print("events_all=",events_all)
    pvi_json["events"] = events_all

    return pvi_json

def get_postprocessed_json(pvi_json, key_val_json):
    print("\n\npvi_json = ", pvi_json, "\n\n")

    try:
        pvi_json = final_report_time(pvi_json)
    except Exception as e:
        print("ERROR IN final_report_time : \n", e)
        pass

    try:
        pvi_json = product_doseinfo_start_stop_date_handling(pvi_json)
    except Exception as e:
        print("ERROR IN product_doseinfo_start_stop_date_handling : \n", e)
        pass

    try:
        pvi_json = processReporterExtractedName(pvi_json)
    except Exception as e:
        print("ERROR IN processReporterExtractedName : \n", e)
        pass

    if pvi_json["patient"]["name"]:
        if pvi_json["patient"]["name"].lower() == 'you':
            pvi_json["patient"]["name"] = pvi_json["reporters"][0]["givenName"]
        else:
            pvi_json["patient"]["name"] = None

    if pvi_json["patient"]["age"]["inputValue"]:
        if 'month' not in pvi_json["patient"]["age"]["inputValue"].lower():
            age_digit = int(round(float(pvi_json["patient"]["age"]["inputValue"])))
            pvi_json["patient"]["age"]["inputValue"] = str(age_digit) + " Years"

    if pvi_json["summary"]["adminNotes"]:
        if len(pvi_json["reporters"]) == 2 and pvi_json["summary"]["adminNotes"].lower() == 'no':
            del pvi_json["reporters"][1]

    pvi_json["summary"]["adminNotes"] = None

    try:
        pvi_json = event_dates_format(pvi_json)
    except Exception as e:
        print("ERROR IN event_dates_format : \n", e)
        pass

    return pvi_json
