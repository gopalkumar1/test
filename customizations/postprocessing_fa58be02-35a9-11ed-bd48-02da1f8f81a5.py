import json
import traceback
import copy
import re
from fuzzywuzzy import fuzz
import pycountry
import pandas as pd
from postal.parser import parse_address
from nameparser import HumanName as hn
from datetime import datetime
from date_format import transform_date


class PostProcessJson():

    def __init__(self, extracted_df, pvi_json, ws1_json):
        self.extracted_df = extracted_df
        self.pvi_json = pvi_json
        self.inter_data = ws1_json

    def get_annotation_value(self, annotation, annotID):
        if annotID is not None:
            return self.extracted_df.loc[self.extracted_df['AnnotID'] == str(annotID), 'value'][0]
        else:
            return self.extracted_df.loc[annotation]['value']

    # Change all the copied reference block from PVI JSON values to None
    def change_reference_values_to_none(self, pvi_json):
        for key, value in pvi_json.items():
            if isinstance(value, dict):
                self.change_reference_values_to_none(value)
            elif isinstance(value, list):
                for val in value:
                    self.change_reference_values_to_none(val)
            else:
                pvi_json.update({key: None})
        return pvi_json

    # def field_na_checker(self,inp_string):
    #     if inp_string:
    #         return inp_string
    #     else:
    #         return None

    def break_address_into_components(address_str):
        parsed_address_tuple = parse_address(address_str)
        address_dict = {}
        for address_component in parsed_address_tuple:
            address_dict[address_component[1]] = address_component[0]
        for key, val in address_dict.items():
            if key == "country":
                address_dict[key] = val.upper()
            else:
                address_dict[key] = val.title()
        return address_dict

    # def populate_reporter_name(reporter_index, first_reporter_name):
    #     if first_reporter_name not in (None, ""):
    #         first_reporter_name = first_reporter_name.replace("=", "")
    #         first_reporter_name = first_reporter_name.replace(".", " ")
    #         first_reporter_name = first_reporter_name.replace(",", " ")
    #         reportername_parsed = hn(first_reporter_name)
    #         self.pvi_json["reporters"][reporter_index]["title"] = field_na_checker(reportername_parsed["title"])
    #         self.pvi_jsonpvi_json["reporters"][reporter_index]["firstName"] = field_na_checker(reportername_parsed["first"])
    #         self.pvi_jsonpvi_json["reporters"][reporter_index]["middleName"] = field_na_checker(reportername_parsed["middle"])
    #         self.pvi_jsonpvi_json["reporters"][reporter_index]["lastName"] = field_na_checker(reportername_parsed["last"])
    #     self.pvi_jsonpvi_json["reporters"][reporter_index]["givenName"] = None
    #     return self.pvi_json

    def reporter_last_page(second_reporter_address, country_list):
        second_reporter_address_list = second_reporter_address.split("\n")
        country_index = []
        start_index = 0
        for country in country_list:
            for indx in range(start_index, len(second_reporter_address_list)):
                if country.lower() in second_reporter_address_list[indx].lower():
                    country_index.append(indx)
        adr = {}
        for indx in range(len(country_index)):
            if indx == 0:
                adr[indx] = "\n".join(second_reporter_address_list[0:country_index[indx] + 1])
            elif indx < len(country_index) - 1:
                adr[indx] = "\n".join(second_reporter_address_list[country_index[indx - 1] + 1:country_index[indx]])
            else:
                adr[indx] = "\n".join(second_reporter_address_list[country_index[indx - 1] + 1:])
        return adr

    def populate_reporter_adr(self, reporter_address, row_index):
        street = ""
        street = reporter_address.get("house_number", "")
        street = street + " " + reporter_address.get("house", "").strip()
        street = street + " " + reporter_address.get("road", "").strip()
        self.pvi_json["reporters"][row_index]["street"] = street
        self.pvi_json["reporters"][row_index]["city"] = reporter_address.get("city", None)
        self.pvi_json["reporters"][row_index]["state"] = reporter_address.get("state", None)
        self.pvi_json["reporters"][row_index]["postcode"] = reporter_address.get("postcode", None)
        if "country" in reporter_address.keys():
            if reporter_address["country"]:
                self.pvi_json["reporters"][row_index]["country"] = reporter_address["country"]
        return self.pvi_json

    @staticmethod
    def field_na_checker(inp_string):
        if inp_string:
            return inp_string
        else:
            return None

    def populate_reporter_name(self, reporter_index, first_reporter_name):
        if first_reporter_name not in (None, ""):
            first_reporter_name = first_reporter_name.replace("=", "")
            first_reporter_name = first_reporter_name.replace(".", " ")
            first_reporter_name = first_reporter_name.replace(",", " ")
            reportername_parsed = hn(first_reporter_name)
            title = reportername_parsed["title"]
            first_name = reportername_parsed["first"]
            middle_name = reportername_parsed["middle"]
            last_name = reportername_parsed["last"]
            # first_name = self.field_na_checker(first_name)

            self.pvi_json["reporters"][reporter_index]["title"] = self.field_na_checker(reportername_parsed["title"])
            self.pvi_json["reporters"][reporter_index]["firstName"] = self.field_na_checker(
                reportername_parsed["first"])
            self.pvi_json["reporters"][reporter_index]["middleName"] = self.field_na_checker(
                reportername_parsed["middle"])
            self.pvi_json["reporters"][reporter_index]["lastName"] = self.field_na_checker(reportername_parsed["last"])
        self.pvi_json["reporters"][reporter_index]["givenName"] = None
        return self.pvi_json

    def source_type(self):
        study, health_professional = self.get_annotation_value(annotation=None, annotID=10024)
        literature = self.get_annotation_value(annotation=None, annotID=10028)[0]
        authority, other = self.get_annotation_value(annotation=None, annotID=10029)

        study = True if study == '1' else False
        health_professional = True if health_professional == '1' else False
        literature = True if literature == '1' else False
        authority = True if authority == '1' else False
        other = True if other == '1' else False

        source_type = None
        if study or study and health_professional or study and other:
            source_type = 'Study'
        elif study and literature:
            source_type = 'Literature Study'
        elif health_professional or health_professional and other:
            source_type = 'Spontaneous'
        elif literature or literature and health_professional or literature and other:
            source_type = 'Literature Spontaneous'

        self.pvi_json['sourceType'][0]['value'] = source_type

    def report_type(self):
        # initial = self.get_annotation_value(annotation=None, annotID=10026)
        followup = self.get_annotation_value(annotation=None, annotID=10027)[0]

        if followup == '1':
            self.pvi_json['mostRecentReceiptDate'], self.pvi_json['receiptDate'] = self.pvi_json['receiptDate'], None

    def break_address_into_components(self, address_str):
        parsed_address_tuple = parse_address(address_str)
        address_dict = {}
        for address_component in parsed_address_tuple:
            address_dict[address_component[1]] = address_component[0]
        for key, val in address_dict.items():
            if key == "country":
                address_dict[key] = val.upper()
            else:
                address_dict[key] = val.title()
        return address_dict

    def reporter_split_based_on_country(self):
        reporter_address = {}
        country_list = ["afghanistan", "albania", "algeria", "andorra", "angola", "antigua and barbuda", "argentina",
                        "armenia", "australia", "austria", "azerbaijan", "the bahamas", "bahrain", "bangladesh",
                        "barbados",
                        "belarus", "belgium", "belize", "benin", "bhutan", "bolivia", "bosnia and herzegovina",
                        "botswana",
                        "brazil", "brunei", "bulgaria", "burkina faso", "burundi", "cambodia", "cameroon", "canada",
                        "cape verde", "central african republic", "chad", "chile", "china", "colombia", "comoros",
                        "congo, republic of the", "congo, democratic republic of the", "costa rica", "cote d\'ivoire",
                        "croatia", "cuba", "cyprus", "czech republic", "denmark", "djibouti", "dominica",
                        "dominican republic", "east timor (timor-leste)", "ecuador", "egypt", "el salvador",
                        "equatorial guinea", "eritrea", "estonia", "ethiopia", "fiji", "finland", "france", "gabon",
                        "the gambia", "georgia", "germany", "ghana", "greece", "grenada", "guatemala", "guinea",
                        "guinea-bissau", "guyana", "haiti", "honduras", "hungary", "iceland", "india", "indonesia",
                        "iran",
                        "iraq", "ireland", "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan", "kenya",
                        "kiribati", "korea, north", "korea, south", "kosovo", "kuwait", "kyrgyzstan", "laos", "latvia",
                        "lebanon", "lesotho", "liberia", "libya", "liechtenstein", "lithuania", "luxembourg",
                        "macedonia",
                        "madagascar", "malawi", "malaysia", "maldives", "mali", "malta", "marshall islands",
                        "mauritania",
                        "mauritius", "mexico", "micronesia, federated states of", "moldova", "monaco", "mongolia",
                        "montenegro", "morocco", "mozambique", "myanmar (burma)", "namibia", "nauru", "nepal",
                        "netherlands", "new zealand", "nicaragua", "niger", "nigeria", "norway", "oman", "pakistan",
                        "palau", "panama", "papua new guinea", "paraguay", "peru", "philippines", "poland", "portugal",
                        "qatar", "romania", "russia", "rwanda", "saint kitts and nevis", "saint lucia",
                        "saint vincent and the grenadines", "samoa", "san marino", "sao tome and principe",
                        "saudi arabia",
                        "senegal", "serbia", "seychelles", "sierra leone", "singapore", "slovakia", "slovenia",
                        "solomon islands", "somalia", "south africa", "south sudan", "spain", "sri lanka", "sudan",
                        "suriname", "swaziland", "sweden", "switzerland", "syria", "taiwan", "tajikistan", "tanzania",
                        "thailand", "togo", "tonga", "trinidad and tobago", "tunisia", "turkey", "turkmenistan",
                        "tuvalu",
                        "uganda", "ukraine", "united arab emirates", "united kingdom", "united states of america",
                        "uruguay", "uzbekistan", "vanuatu", "vatican city (holy see)", "venezuela", "vietnam", "yemen",
                        "zambia", "zimbabwe"]
        first_reporter_address = self.pvi_json["literatures"][0]["author"]
        first_reporter_name = ""
        first_reporter = False
        if first_reporter_address and "NAME AND ADDRESS WITHHELD" not in first_reporter_address:
            first_reporter = True
            first_reporter_address = first_reporter_address.replace("25b. NAME AND ADDRESS OF REPORTER", "").replace(
                "(Continued on Additional Information Page)", "").replace("()", "")
            first_reporter_name = first_reporter_address.split("\n")[0]
            for country in country_list:
                cnt = first_reporter_address.lower().find(country)
                if cnt != -1:
                    first_reporter_address = first_reporter_address[0:cnt + len(country)]
                    break
            if first_reporter_name:
                self.pvi_json = self.populate_reporter_name(0, first_reporter_name)
                first_reporter_address = first_reporter_address.replace(first_reporter_name, "").strip()
            else:
                first_reporter_address = first_reporter_address.strip()
            reporter_address = self.break_address_into_components(first_reporter_address)
            self.pvi_json = self.populate_reporter_adr(reporter_address, 0)
        second_reporter_address_all = self.pvi_json["literatures"][0]["title"]
        if second_reporter_address_all:
            if "NAME AND ADDRESS WITHHELD" not in second_reporter_address_all:
                second_reporter_address_all = second_reporter_address_all.replace("25b. NAME AND ADDRESS OF REPORTER",
                                                                                  "").replace(
                    "(Continued on Additional Information Page)", "").replace("()", "").strip()
            if first_reporter:
                reporter_all = [self.pvi_json["reporters"][0]]
            else:
                reporter_all = []
            lastpage_reporter_adr = reporter_last_page(second_reporter_address_all, country_list)
            for addr in lastpage_reporter_adr.keys():
                if first_reporter_name not in lastpage_reporter_adr[addr]:
                    name = lastpage_reporter_adr[addr].split("\n")[0]
                    lastpage_addr_all = " ".join(lastpage_reporter_adr[addr].split("\n")[1:])
                    address_dict = self.break_address_into_components(lastpage_addr_all)
                    reporter_sec = self.populate_reporter_name(empty_repo(), 0, name)
                    reporter_sec = self.populate_reporter_adr(reporter_sec, address_dict, 0)
                    reporter_all.append(reporter_sec["reporters"][0])
            if reporter_all:
                self.pvi_json["reporters"] = reporter_all
        self.pvi_json["literatures"][0]["author"] = None
        self.pvi_json["literatures"][0]["title"] = None

    def parse_patient_name(self):
        if self.pvi_json['patient']["name"]:
            self.pvi_json['patient']["name"] = self.pvi_json['patient']["name"].strip()
            if " " in self.pvi_json['patient']["name"]:
                name = self.pvi_json['patient']["name"].split()
                name[0] = name[0][0:2].strip()
                name[1] = name[1][0:2].strip()
                self.pvi_json['patient']["name"] = " ".join(name)

    def parse_patient_dob(self):
        if self.pvi_json['patient']['patientDob'] and self.pvi_json['patient']['patientDob'].lower() in ['unk',
                                                                                                         'unknown']:
            self.pvi_json['patient']['patientDob'] = None
        elif self.pvi_json['patient']['patientDob'] and self.pvi_json['patient']['patientDob'].lower() in ['privacy']:
            self.pvi_json['patient']['additionalNotes'] = "Date of birth: " + self.pvi_json['patient']['patientDob']
            self.pvi_json['patient']['patientDob'] = None

    def parse_patient_age(self):
        if self.pvi_json['patient']['age']['inputValue']:
            self.pvi_json['patient']['age']['inputValue'] = self.pvi_json['patient']['age']['inputValue'].replace("(",
                                                                                                                  "").replace(
                ")", "")

    def parse_medHis_details(self):
        final_medHis = []
        for medhis in self.pvi_json['patient']['medicalHistories']:
            if medhis['reportedReaction']:
                final_medHis.append(medhis)
        for medhis in final_medHis:
            if medhis['continuing'] and medhis['continuing'].lower() not in ['yes', 'no']:
                medhis['continuing'] = None
        self.pvi_json['patient']['medicalHistories'] = final_medHis

    def parse_test_resultunit(self):
        for test in self.pvi_json['tests']:
            if test['testResultUnit']:
                test['testResultUnit'] = re.sub(r"^\d+.\d+|^\d+", "", test['testResultUnit'].strip(" { } ( ) \ / ; . [ ] , - : < %"))
                test['testResultUnit'] = test['testResultUnit'].strip(" { } ( ) \ / ; . [ ] , - : < %")
            if not test["testResult"] and test['testResultUnit']:
                test['testResult'], test["testResultUnit"] = test["testResultUnit"], None

    def remove_null_and_junk_test(self):
        self.pvi_json['tests'] = [test for test in self.pvi_json['tests'] if test['testName'] and test['testName'] not in ['Test Name']]
        self.pvi_json['references'][0]['referenceNotes'] = 'Duplicate Number'
    def parse_patient_details(self):
        try:
            self.parse_patient_name()
        except:
            traceback.print_exc()
        try:
            self.parse_patient_dob()
        except:
            traceback.print_exc()
        try:
            self.parse_patient_age()
        except:
            traceback.print_exc()
        try:
            self.parse_medHis_details()
        except:
            traceback.print_exc()

    def parse_test_details(self):
        try:
            self.parse_test_resultunit()
        except:
            traceback.print_exc()
        try:
            self.remove_null_and_junk_test()
        except:
            traceback.print_exc()

    def post_process(self):
        try:
            self.source_type()
        except:
            traceback.print_exc()
        try:
            self.reporter_split_based_on_country()
        except:
            traceback.print_exc()
        try:
            self.report_type()
        except:
            traceback.print_exc()

    @staticmethod
    def make_entry_none(input_data):
        for key, value in input_data.items():
            if isinstance(value, dict):
                PostProcessJson.make_entry_none(value)
            elif isinstance(value, list):
                for val in value:
                    PostProcessJson.make_entry_none(val)
            else:
                input_data.update({key: None})
        return input_data

    @staticmethod
    def find_start_bracket(input_string):
        regex = re.compile(r"\s[(][A-Z]{1,}")
        group = re.search(regex, input_string)
        if group is not None:
            index = group.span()
        else:
            index = None
        return index

    @staticmethod
    def find_end_bracket(input_string):
        regex = re.compile(r"[)]$")
        group = re.search(regex, input_string)
        if group is not None:
            index = group.span()
        else:
            index = None
        return index

    @staticmethod
    def parse_con_licence_value(input_cols):
        licence_value = None
        for col in input_cols:
            index = PostProcessJson.find_start_bracket(col)
            end_index = PostProcessJson.find_end_bracket(col)
            if (index is not None) and (end_index is not None):
                licence_value = col[index[0] + 2: end_index[1]-1]
                break
        if licence_value is not None:
            return licence_value.replace("\n", " ")
        else:
            return licence_value
    # def parse_con_licence_value(input_cols):
    #     licence_value = None
    #     # caps_regex = re.compile(r"[A-Z]{3,}")
    #     # caps_regex = r"[A-Z]{2,}(?:[;|\s])"
    #     caps_regex = r"^([A-Z]{1,}(?:[;|\s|,])){1,}"
    #     for col in input_cols:
    #         index = PostProcessJson.find_start_bracket(col)
    #         if index is not None:
    #             first_str = col[0:index[0]]
    #             matches = re.finditer(caps_regex, first_str, re.MULTILINE)
    #             indexes = []
    #             for matchNum, match in enumerate(matches, start=1):
    #                 indexes.append(match.start())
    #                 indexes.append(match.end())
    #             if len(indexes)>0:
    #                 licence_value = first_str[min(indexes):max(indexes)].strip()
    #                 break
    #             # words = re.findall(caps_regex, first_str)
    #             # if len(words) > 1:
    #             #     licence_value = " ".join(words)
    #             #     break
    #             else:
    #                 licence_value = None
    #                 break
    #     if licence_value is not None:
    #         return licence_value.replace("\n", " ")
    #     else:
    #         return licence_value

    @staticmethod
    def parse_licence_value(input_cols):
        licence_value = None
        for col in input_cols:
            index = PostProcessJson.find_start_bracket(col)
            if index is not None:
                licence_value = col[index[0] + 2:index[1]]
                break
        if licence_value is not None:
            return licence_value.replace("\n", " ")
        else:
            return licence_value

    @staticmethod
    def parse_dose_description(input_cols, index):
        input_value = False
        description = None
        freq_regex = re.compile(
            r"(?:week|day|month|year|daily|quarterly|hour|hourly|weekly|monthly|yearly|since|Since)")
        numeric_regex = re.compile(r"\d+")
        if len(input_cols) > 4:
            description_value = input_cols[2]
            descriptions = description_value.split(";")
            if index <= len(descriptions) - 1:
                des = descriptions[index]
                digits = re.findall(freq_regex, des)
                if len(digits) > 0:
                    description = des
                else:
                    digits = re.findall(numeric_regex, des)
                    if len(digits) > 0:
                        description = des
                        input_value = True
            else:
                des = descriptions[len(descriptions) - 1]
                digits = re.findall(freq_regex, des)
                if len(digits) > 0:
                    description = des
                else:
                    digits = re.findall(numeric_regex, des)
                    if len(digits) > 0:
                        description = des
                        input_value = True
        if description is not None and len(description) > 2:
            return description.strip().replace("\n", " "), input_value
        else:
            return None, input_value

    @staticmethod
    def make_regex(input_str):
        return r"^"+input_str+"$"

    @staticmethod
    def parse_route_information(input_cols, index):
        route_info = None
        route_found = False
        possible_unk_list = ["Unknown", "Unk", "AKSU"]
        possible_route_information = ["Endotracheopulmonary",
"Epilesional use",
"Gastric use",
"Gastroenteral use",
"Gingival use",
"Inhalation use",
"Intestinal use",
"Intrabursal use",
"Intracameral use",
"Int chol pancreatic",
"Intraglandular use",
"Intraosseous use",
"Intraportal use",
"Laryngopharyngeal",
"Nail use",
"Ocular use",
"Oromucosal use",
"Periosseous use",
"Peritumoral use",
"Post juxtascleral",
"Route of admin NA",
"Skin scarification",
"Intracanalicular",
"Intracavitary",
"Electro-osmosis",
"Enteral",
"Extracorporeal",
"Infiltration",
"Interstitial",
"Intra-abdominal",
"Intrabiliary",
"Intrabronchial",
"Intrabursal",
"Intracartilaginous",
"Intracaudal",
"Intracoronal, dental",
"Intracranial",
"Intraductal",
"Intraduodenal",
"Intradural",
"Intraepicardial",
"Intraepidermal",
"Intraesophageal",
"Intragastric",
"Intragingival",
"Intraileal",
"Intralingual",
"Intraluminal",
"Intramammary",
"Intranodal",
"Intraomentum",
"Intraovarian",
"Intraprostatic",
"Intraruminal",
"Intrasinal",
"Intraspinal",
"Intratendinous",
"Intratesticular",
"Intratubular",
"Intratympanic",
"Intravascular",
"Intraventricular",
"Intravitreal",
"Irrigation",
"Laryngeal",
"Nasogastric",
"Not applicable",
"Percutaneous",
"Peridural",
"Periodontal",
"Soft tissue",
"Subarachnoid",
"Subgingival",
"Submucosal",
"Subretinal",
"Transendocardial",
"Transmucosal",
"Transtracheal",
"Transtympanic",
"Ureteral",
"Auricular",
"Buccal",
"Cutaneous",
"Dental",
"Endocervical",
"Endosinusial",
"Endotracheal",
"Epidural",
"Extra-amniotic",
"Hemodialysis",
"Int corp caver",
"Intra-amniotic",
"Intra-arterial",
"Intra-articular",
"Intra-uterine",
"Intracardiac",
"Intracavernous",
"Intracerebral",
"Intracervical",
"Intracisternal",
"Intracorneal",
"Intracoronary",
"Intradermal",
"Intradiscal",
"Intrahepatic",
"Intralesional",
"Intralymphatic",
"Intramedullar",
"Intrameningeal",
"Intramuscular",
"Intraocular",
"Intrapericard",
"Intraperitoneal",
"Intrapleural",
"Intrasynovial",
"Intratumor",
"Intrathecal",
"Intrathoracic",
"Intratracheal",
"IV bolus",
"IV drip",
"Intravenous",
"Intravesical",
"Iontophoresis",
"Nasal",
"Occlusive",
"Ophthalmic",
"Oral",
"Oropharingeal",
"Other",
"Parenteral",
"Periarticular",
"Perineural",
"Rectal",
"Respiratory",
"Retrobulbar",
"Subconjunctival",
"Subcutaneous",
"Subdermal",
"Sublingual",
"Topical",
"Transdermal",
"Transmammary",
"Transplacental",
"Unknown",
"Urethral",
"Vaginal"]
        if len(input_cols) >= 5:
            route = input_cols[4]
            routes = route.split(";")
            if index <= len(routes) - 1:
                route_info = routes[index].strip().replace("\n", " ")
            else:
                route_info = routes[len(routes) - 1].strip().replace("\n", " ")
        if route_info is not None:
            for route_value in possible_route_information:
                route_regex = re.compile(PostProcessJson.make_regex(route_value))
                if route_regex.match(route_info):
                    route_info = route_value
                    route_found = True
                    break
        if route_info is not None:
            for route_value in possible_unk_list:
                ratio = fuzz.ratio(route_info.lower(), route_value.lower())
                if ratio >= 70:
                    route_info = None
                    route_found = False
                    break

        return route_info, route_found

    @staticmethod
    def parse_lot_number(input_cols, index):
        lot_number = None
        possible_unk_list = ["Unknown", "Unk"]
        if len(input_cols) >= 7:
            lot_value = input_cols[3]
            lot_values = lot_value.split(";")
            if index <= len(lot_values)-1:
                lot_number = lot_values[index].strip()
            else:
                lot_number = lot_values[len(lot_values)-1].strip()
        if lot_number is not None:
            for unk in possible_unk_list:
                ratio = fuzz.ratio(lot_number.lower(), unk.lower())
                if ratio >= 70:
                    lot_number = None
                    break
        return lot_number

    @staticmethod
    def parse_threrapy_duration(input_cols, index):
        duration = None
        possible_unk_list = ["Unknown", "Unk", "AKSU"]
        if len(input_cols) >= 8:
            date = input_cols[7]
            dates = date.split(";")
            if index <= len(dates) - 1:
                duration = dates[index].strip()
            else:
                duration = dates[len(dates) - 1].strip()
        if duration is not None:
            if len(duration) > 1:
                for unk in possible_unk_list:
                    ratio = fuzz.ratio(duration.lower(), unk.lower())
                    if ratio >= 70:
                        duration = None
                        break
            else:
                duration = None
        if duration is not None:
            duration = duration.replace("(s)", "s")
        return duration


    def parse_indications(self, input_cols):
        indications = []
        if len(input_cols) >= 6:
            indication = input_cols[5]
            all_indications = indication.split(";")
            for index in range(len(all_indications)):
                dummy_indications = PostProcessJson.make_entry_none(self.pvi_json["products"][0]["indications"][0])
                dummy_indications["reactionCoded"] = all_indications[index]
                dummy_indications["reportedReaction"] = all_indications[index]
                indications.append(copy.deepcopy(dummy_indications))
        if len(indications)==0:
            dummy_indications = PostProcessJson.make_entry_none(self.pvi_json["products"][0]["indications"][0])
            indications.append(copy.deepcopy(dummy_indications))
        return indications


    @staticmethod
    def parse_start_end_date(input_cols, index):
        start_date = None
        end_date = None
        possible_unk_list = ["Unknown", "Unk", "AKSU"]
        if len(input_cols) >= 7:
            date = input_cols[6]
            dates = date.split(";")
            if index <= len(dates) - 1:
                comp_date = dates[index].strip()
            else:
                comp_date = dates[len(dates) - 1].strip()
            st_end_date = comp_date.split("/")
            if len(st_end_date) == 2:
                start_date = st_end_date[0].strip().replace("\n", "")
                end_date = st_end_date[1].strip().replace("\n", "")
        if start_date is not None:
            for unk in possible_unk_list:
                ratio = fuzz.ratio(start_date.lower(), unk.lower())
                if ratio >= 70:
                    start_date = None
                    break
        if end_date is not None:
            for unk in possible_unk_list:
                ratio = fuzz.ratio(end_date.lower(), unk.lower())
                if ratio >= 70:
                    end_date = None
                    break
        if start_date is not None:
            start_date = transform_date(start_date, "%d-%b-%Y", "%d-%b-%Y")
        if end_date is not None:
            end_date = transform_date(end_date, "%d-%b-%Y", "%d-%b-%Y")
        return start_date, end_date
    def parse_suspect_drug(self):
        all_suspect_drugs = None
        for annot in self.inter_data:
            column_header = ["name", "threrapy dates", "dosage", "lot", "Indication", "22.","administration", "concomitant"]
            if annot["AnnotID"] == "10012":
                all_suspect_drugs = []
                all_values = annot["value"]
                count = 0
                for value in all_values:  # Iterate all list of suspect products
                    header_count = 0
                    is_header = False
                    for col in value:
                        for pos in column_header:
                            if pos in col.lower():
                                header_count = header_count + 1
                            if header_count >= 2:
                                is_header = True
                                break
                        if is_header:
                            break
                    if not is_header:
                        entries = []
                        # no_of_entries = 1
                        for index, col_value in enumerate(value[2:]):
                            if index == 3:
                                continue
                            entries.append(len(col_value.split(";")))
                        max_entries = max(entries)
                        no_of_entries = max_entries
                        # ent_pointer = max_entries
                        # while ent_pointer != 1:
                        #     ent_count = entries.count(ent_pointer)
                        #     if ent_count > 2:
                        #         no_of_entries = max_entries
                        #         break
                        #     ent_pointer = ent_pointer - 1
                        dummy_product = PostProcessJson.make_entry_none(self.pvi_json["products"][0])
                        dummy_product["role_value"] = "suspect"
                        dummy_product["seq_num"] = count
                        count = count + 1
                        empty_dose_info = copy.deepcopy(dummy_product["doseInformations"][0])
                        licence_value = PostProcessJson.parse_licence_value(value)
                        dummy_product["license_value"] = licence_value
                        dose_informations = []
                        for i in range(no_of_entries):
                            dose_info = copy.deepcopy(empty_dose_info)
                            dose_description, input_value = PostProcessJson.parse_dose_description(value, i)
                            if input_value:
                                dose_info["dose_inputValue"] = dose_description
                            else:
                                dose_info["description"] = dose_description
                            route_info, route_found = PostProcessJson.parse_route_information(value, i)
                            if route_info is not None:
                                if not route_found:
                                    if dose_info["description"] is not None:
                                        dose_info["description"] = dose_info["description"] + ", " + route_info
                                    else:
                                        dose_info["description"] = route_info
                                    dose_info["route_value"] = None
                                else:
                                    dose_info["route_value"] = route_info
                            else:
                                dose_info["route_value"] = None
                            start_date, end_date = PostProcessJson.parse_start_end_date(value, i)
                            dose_info["startDate"] = start_date
                            dose_info["endDate"] = end_date
                            lot_number = PostProcessJson.parse_lot_number(value, i)
                            dose_info["customProperty_batchNumber_value"] = lot_number
                            theray_duration = PostProcessJson.parse_threrapy_duration(value, i)
                            dose_info["duration"] = theray_duration
                            dose_informations.append(copy.deepcopy(dose_info))
                        dummy_product["doseInformations"] = dose_informations
                        indications = self.parse_indications(value)
                        dummy_product["indications"] = indications
                        all_suspect_drugs.append(copy.deepcopy(dummy_product))
        return all_suspect_drugs

    def parse_concommitant_drugs(self):
        all_concommitent_drugs = None
        for annot in self.inter_data:
            column_header = ["name", "threrapy dates", "dosage", "lot", "Indication", "22.","administration", "concomitant"]
            if annot["AnnotID"] == "10043":
                all_concommitent_drugs = []
                all_values = annot["value"]
                count = 1
                for value in all_values:  # Iterate all list of suspect products
                    header_count = 0
                    is_header = False
                    for col in value:
                        for pos in column_header:
                            if pos in col.lower():
                                header_count = header_count + 1
                            if header_count >= 2:
                                is_header = True
                                break
                        if is_header:
                            break
                    if not is_header:
                        entries = []
                        # no_of_entries = 1
                        for index, col_value in enumerate(value[2:]):
                            if index == 3:
                                continue
                            entries.append(len(col_value.split(";")))
                        max_entries = max(entries)
                        no_of_entries = max_entries
                        # ent_pointer = max_entries
                        # while ent_pointer != 1:
                        #     ent_count = entries.count(ent_pointer)
                        #     if ent_count > 2:
                        #         no_of_entries = max_entries
                        #         break
                        #     ent_pointer = ent_pointer - 1
                        dummy_product = PostProcessJson.make_entry_none(self.pvi_json["products"][0])
                        dummy_product["role_value"] = "Concomitant"
                        dummy_product["seq_num"] = count
                        count = count + 1
                        empty_dose_info = copy.deepcopy(dummy_product["doseInformations"][0])
                        licence_value = PostProcessJson.parse_con_licence_value(value)
                        # licence_value = PostProcessJson.parse_licence_value(value)
                        dummy_product["license_value"] = licence_value
                        dose_informations = []
                        for i in range(no_of_entries):
                            dose_info = copy.deepcopy(empty_dose_info)
                            dose_description, input_value = PostProcessJson.parse_dose_description(value, i)
                            if input_value:
                                dose_info["dose_inputValue"] = dose_description
                            else:
                                dose_info["description"] = dose_description
                            route_info, route_found = PostProcessJson.parse_route_information(value, i)
                            if route_info is not None:
                                if not route_found:
                                    if dose_info["description"] is not None:
                                        dose_info["description"] = dose_info["description"] + ", " + route_info
                                    else:
                                        dose_info["description"] = route_info
                                    dose_info["route_value"] = None
                                else:
                                    dose_info["route_value"] = route_info
                            else:
                                dose_info["route_value"] = None
                            start_date, end_date = PostProcessJson.parse_start_end_date(value, i)
                            dose_info["startDate"] = start_date
                            dose_info["endDate"] = end_date
                            lot_number = PostProcessJson.parse_lot_number(value, i)
                            dose_info["customProperty_batchNumber_value"] = lot_number
                            theray_duration = PostProcessJson.parse_threrapy_duration(value, i)
                            dose_info["duration"] = theray_duration
                            dose_informations.append(copy.deepcopy(dose_info))
                        dummy_product["doseInformations"] = dose_informations
                        indications = self.parse_indications(value)
                        dummy_product["indications"] = indications
                        all_concommitent_drugs.append(copy.deepcopy(dummy_product))
        return all_concommitent_drugs

    def parse_product_section(self):
        all_products = []
        try:
            suspect_drugs = self.parse_suspect_drug()
            all_products.extend(suspect_drugs)
        except:
            traceback.print_exc()
        try:
            concommitent_drugs = self.parse_concommitant_drugs()
            all_products.extend(concommitent_drugs)
        except:
            traceback.print_exc()
        if len(all_products)==0:
            dummy_product = PostProcessJson.make_entry_none(self.pvi_json["products"][0])
            all_products.append(dummy_product)
        self.pvi_json["products"] = all_products

    @staticmethod
    def date_pattern_check(text):
        # pattern to check date patterns: uu-Jan-2022/UNK , uu-Uuu-2022/UNK , UNK/UNK
        # Return Boolean
        regex_pattern = r'(((uu|\d\d)-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Uuu)-\d\d\d\d)|UNK)\/(((uu|\d\d)-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Uuu)-\d\d\d\d)|UNK)'
        if re.search(regex_pattern, text):
            return True
        return False

    def each_event_separator(self, event_data_list):
        separate_events_list = []
        for row in event_data_list:
            # each_event_data = ''
            if not self.date_pattern_check(row):  # create new event
                separate_events_list.append(row)
            else:  # append to existing one i.e. last created event
                if separate_events_list:
                    if self.date_pattern_check(separate_events_list[-1]):
                        separate_events_list.append(row)
                    else:
                        separate_events_list[-1] = separate_events_list[-1] + ' ' + row
                else:
                    separate_events_list.append(row)

        return separate_events_list

    @staticmethod
    def get_event_outcome(each_event_text):
        outcome = None
        code_list = ['Fatal', 'Not recovered', 'Recovered', 'Recovered/Resolved with sequelae', 'Recovering', 'Unknown']
        outcome_mapping = ['Fatal', 'Not Recovered/Not Resolved/Ongoing', 'Recovered/Resolved', 'Recovered/Resolved with sequelae', 'Recovering/Resolving', 'Unknown']

        for index, code in enumerate(code_list):
            if code in each_event_text:
                outcome = outcome_mapping[index]
                break
        return outcome

    def extract_event_fields(self, each_event_text, sample_event_dict):
        event_dict = copy.deepcopy(sample_event_dict)
        try:
            rr = re.search(r'\[.*?\]', each_event_text).group()
        except:
            rr = None
        if rr:
            event_dict['reactionCoded'] = rr.strip('[]')
            event_dict['reportedReaction'] = event_dict['reactionCoded']

            start_date_regex_pattern = r'(((uu|\d\d)-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Uuu)-\d\d\d\d)|UNK)\/'
            try:
                start_date = re.search(start_date_regex_pattern, each_event_text).group()
            except:
                start_date = None
            if start_date:
                event_dict['startDate'] = start_date.strip('/')
            end_date_regex_pattern = r'\/(((uu|\d\d)-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Uuu)-\d\d\d\d)|UNK)'
            try:
                end_date = re.search(end_date_regex_pattern, each_event_text).group()
            except:
                end_date = None
            if end_date:
                event_dict['endDate'] = end_date.strip('/')

            event_dict['outcome'] = self.get_event_outcome(each_event_text)
        else:
            return None
        return event_dict

    def parse_event_details(self):
        # seriousness = copy.deepcopy(self.pvi_json['events'][0]['seriousnesses'])
        event_country = self.pvi_json['events'][0]['country']

        final_event_section = []
        sample_event_dict = copy.deepcopy(self.change_reference_values_to_none(self.pvi_json['events'][0]))

        event_data_list = self.get_annotation_value(annotation='7+13 DESCRIBE REACTIONS', annotID=None)
        separate_events_list = self.each_event_separator(event_data_list)

        for each_event_row in separate_events_list:
            if each_event_row:
                each_event_dict = self.extract_event_fields(each_event_row, sample_event_dict)
                if each_event_dict:
                    final_event_section.append(each_event_dict)

        # other_seriousness = self.get_annotation_value(annotation='8-12_Check_CB', annotID=None)
        # if not any(other_seriousness):
        #     final_event_section[0]['seriousnesses'] = seriousness

        final_event_section[0]['country'] = event_country
        self.pvi_json['events'] = final_event_section

        seriousness_cb_data = self.get_annotation_value(annotation='8-12_Check_CB', annotID=None)
        combined_seriousness = []
        mapped_code_list = ['Death', 'Life Threatening', 'Hospitalization', 'Disability', 'Congenital Anomaly', 'Other']
        for index, each in enumerate(seriousness_cb_data):
            if each == '1':
                combined_seriousness.append({'value': mapped_code_list[index], 'value_acc': 0.95})
        if combined_seriousness:
            self.pvi_json['events'][0]['seriousnesses'] = combined_seriousness

    def parse_country_name(self):
        event_country_code = self.pvi_json['events'][0]['country']
        if event_country_code:
            event_country_full = pycountry.countries.get(alpha_2=event_country_code).name

            for index, item in enumerate(self.pvi_json['events']):
                  item['country'] = event_country_full

            reporter_country_code = self.pvi_json['reporters'][0]['country']
            if reporter_country_code:
                reporter_country_full = pycountry.countries.get(alpha_2=reporter_country_code).name
            else:
                reporter_country_full = event_country_full
            for index, item in enumerate(self.pvi_json['reporters']):
                item['country'] = reporter_country_full

    @staticmethod
    def date_format_update(given_date):
        if given_date and given_date.lower() not in ["unk", "un", "unknown"]:
            given_date = given_date.replace('-', '').replace('Uuu', '').replace('uu', '')
            dd_mmm_yyyy = re.compile(r"\d{2}[A-Za-z]{3}\d{4}")
            d_mmm_yyyy = re.compile(r"\d{1}[A-Za-z]{3}\d{4}")
            mmm_yyyy = re.compile(r"[A-Za-z]{3}\d{4}")
            yyyy = re.compile(r"\d{4}")

            dd_mmm_yyyy_ptn = re.findall(dd_mmm_yyyy, given_date)
            d_mmm_yyyy_ptn = re.findall(d_mmm_yyyy, given_date)
            mmm_yyyy_ptn = re.findall(mmm_yyyy, given_date)
            yyyy_ptn = re.findall(yyyy, given_date)
            if len(dd_mmm_yyyy_ptn) > 0:
                try:
                    date_obj = datetime.strptime(given_date, "%d%b%Y").strftime("%d-%b-%Y")
                    given_date = date_obj
                except:
                    given_date = None

            elif len(d_mmm_yyyy_ptn) > 0:
                try:
                    date_obj = datetime.strptime(given_date, "%d%b%Y").strftime("%d-%b-%Y")
                    given_date = "0" + date_obj
                except:
                    given_date = None

            elif len(mmm_yyyy_ptn) > 0:
                try:
                    date_obj = datetime.strptime(given_date, "%b%Y").strftime("%b-%Y")
                    given_date = date_obj
                except:
                    given_date = None
            elif len(yyyy_ptn) > 0:
                try:
                    date_obj = datetime.strptime(given_date, "%Y").strftime("%Y")
                    given_date = date_obj
                except:
                    given_date = None
            else:
                given_date = None
        else:
            given_date = None
        return given_date

    def transform_pvi_json_date_fields(self):
        for event in self.pvi_json['events']:
            event['startDate'] = self.date_format_update(event['startDate'])
            event['endDate'] = self.date_format_update(event['endDate'])
        for product in self.pvi_json['products']:
            for dose in product['doseInformations']:
                dose['startDate'] = self.date_format_update(dose['startDate'])
                dose['endDate'] = self.date_format_update(dose['endDate'])
        for test in self.pvi_json['tests']:
            test['startDate'] = self.date_format_update(test['startDate'])


def get_postprocessed_json(pvi_json, ws1_json):
    extracted_df = pd.DataFrame(ws1_json)
    extracted_df.set_index("class", inplace=True)
    ppj = PostProcessJson(extracted_df, pvi_json, ws1_json)
    try:
        ppj.post_process()
    except:
        traceback.print_exc()
    try:
        ppj.parse_patient_details()
    except:
        traceback.print_exc()
    try:
        ppj.parse_test_details()
    except:
        traceback.print_exc()
    try:
        ppj.parse_event_details()
    except:
        traceback.print_exc()
    try:
        ppj.parse_country_name()
    except:
        traceback.print_exc()
    try:
        ppj.parse_product_section()
    except:
        traceback.print_exc()
    try:
        ppj.transform_pvi_json_date_fields()
    except:
        traceback.print_exc()
    return pvi_json


# # pvi_json = json.load(open('/home/lt-gandharvp/Desktop/a52/pvi.json'))
# ws1_json = json.load(open('/home/rxlogix/Downloads/gfp-forms/ORION/Nordic_CIOMS/620_inter.json'))
# pvi_json = json.load(open('/home/rxlogix/Downloads/gfp-forms/ORION/Nordic_CIOMS/620_post0.json'))
# print(json.dumps(get_postprocessed_json(pvi_json,ws1_json)))

