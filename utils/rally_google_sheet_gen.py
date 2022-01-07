#!/usr/bin/env python
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# Rally generates a json file with data about atomic actions duration from each iteration.
# These atomic actions often occur multiple times within one iteration.
# This script allows a user to generate a CSV file and also has an option to
# generate a Google Sheet about individual resource
# duration through the Rally json file. To use the script to upload the CSV file to Google Sheets,
# a Google Drive service account is required.
# The script sends an email to the email id of the user with the Google sheet
# if the --uploadgooglesheet option is enabled.

# To generate only a CSV file and not upload to Google Sheets :

#    $ source .browbeat-venv/bin/activate && cd utils
#    $ python rally_google_sheet_gen.py -c <path to csv file to write locally>
#      -j <path to rally json file> -a <atomic action(Eg.: nova.boot_server>

# To generate a CSV file and upload to Google Sheets :

#    $ source .browbeat-venv/bin/activate && cd utils
#    $ python rally_google_sheet_gen.py -c <path to csv file to write locally>
#      -j <path to rally json file> -a <atomic action(Eg.: nova.boot_server> -g
#      -s <path to google service account json credentials file>
#      -e <email id of user> -n <name of google sheet to be created>

import json
import csv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import cellFormat
from gspread_formatting import format_cell_range
from gspread_formatting import set_column_width
import argparse

def convert_rally_json_to_csv(json_file_path, atomic_action, csv_file_path):
    """Convert rally json data to csv file containing atomic action data
    :param json_file_path: str, path to rally json file
    :param atomic_action: str, atomic action to generate duration data
    :param csv_file_path: str, path to write csv file
    """
    json_file = open(json_file_path)
    json_data = json.load(json_file)

    with open(csv_file_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',',
                               quotechar='|', quoting=csv.QUOTE_MINIMAL)

        csvwriter.writerow(["Resource Number", "Duration(in seconds)"])
        resource_number = 1

        for iteration in json_data[0]["result"]:
            for atomic_action_json in iteration["atomic_actions"]:
                if atomic_action in atomic_action_json:
                    atomic_action_duration = iteration["atomic_actions"][atomic_action_json]
                    csvwriter.writerow([resource_number, atomic_action_duration])
                    resource_number += 1

    print("CSV file {} generated successfully.".format(csv_file_path))

def push_to_gsheet(csv_file_path, google_svc_acc_key, email_id):
    """Push csv file to Google Sheets
    :param csv_file_path: str, path to csv file
    :param google_svc_acc_key: str, path to json credentials for google service account
    :param email_id: str, email id of user who will be given edit access to google sheet
    """
    fmt = cellFormat(
        horizontalAlignment="RIGHT"
    )
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(google_svc_acc_key, scope)
    gc = gspread.authorize(credentials)

    sh = gc.create(params.sheetname)
    sh.share(email_id, perm_type="user", role="writer")
    spreadsheet_id = sh.id
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{sh.id}"
    with open(csv_file_path, "r") as f:
        gc.import_csv(spreadsheet_id, f.read())
    worksheet = sh.get_worksheet(0)
    format_cell_range(worksheet, "1:1000", fmt)
    set_column_width(worksheet, "A", 290)
    set_column_width(worksheet, "B", 190)
    set_column_width(worksheet, "C", 400)
    print(f"Google Spreadsheet link -> {spreadsheet_url}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--csvfilepath", help="Path to create CSV file",
        nargs='?', required=True, dest="csvfilepath"
    )
    parser.add_argument(
        "-j", "--jsonfilepath", help="Rally JSON file path to scrape output from",
        nargs='?', required=True, dest="jsonfilepath",
    )
    parser.add_argument(
        "-a", "--atomicaction", help="Atomic action to generate duration data",
        nargs='?', required=True, dest="atomicaction",
    )
    parser.add_argument(
        '-g', '--uploadtogooglesheets', action='store_true', required=False,
        help='Flag to enable csv file upload to Google Sheets', dest="uploadtogooglesheets"
    )
    parser.add_argument(
        "-n", "--sheetname", help="Google Sheet name",
        nargs='?', required=False, dest="sheetname"
    )
    parser.add_argument(
        "-s", "--googlesvcacckey", help="Google service account credentials",
        nargs='?', required=False, dest="googlesvcacckey",
    )
    parser.add_argument(
        "-e", "--emailid", help="Email id to send result sheet",
        nargs='?', required=False, dest="emailid",
    )
    params = parser.parse_args()

    if(params.uploadtogooglesheets and
       (params.sheetname is None or params.googlesvcacckey is None or params.emailid is None)):
        parser.error("{} requires {} and {} and {}.".format("--uploadtogooglesheets",
                                                            "--sheetname",
                                                            "--googlesvcacckey",
                                                            "--emailid"))

    convert_rally_json_to_csv(params.jsonfilepath, params.atomicaction,
                              params.csvfilepath)
    if params.uploadtogooglesheets:
        push_to_gsheet(params.csvfilepath, params.googlesvcacckey, params.emailid)
