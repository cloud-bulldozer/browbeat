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

# To generate only CSV files and not upload to Google Sheets :

#    $ source .browbeat-venv/bin/activate && cd utils
#    $ python rally_google_sheet_gen.py -c -f <path to directory to write csv file locally>
#      -j <path to rally json file>
#      -a <space separated list of atomic actions(Eg.: boot_server create_network)>

# To only upload to Google Sheets and not generate CSV files :

#    $ source .browbeat-venv/bin/activate && cd utils
#    $ python rally_google_sheet_gen.py
#      -j <path to rally json file>
#      -a <space separated list of atomic actions(Eg.: boot_server create_network)> -g
#      -s <path to google service account json credentials file>
#      -e <email id of user> -n <name of google sheet to be created>

# To only upload to Google Sheets along with SLA failures and not generate CSV files :

#    $ source .browbeat-venv/bin/activate && cd utils
#    $ python rally_google_sheet_gen.py
#      -j <path to rally json file>
#      -a <space separated list of atomic actions(Eg.: boot_server create_network)> -g
#      -v <space separated list of max durations as per SLA criteria(Eg.: 10 20 120)>
#         Note: The ordering of the max durations must match the ordering of atomic actions.
#      -s <path to google service account json credentials file>
#      -e <email id of user> -n <name of google sheet to be created>


# To generate a CSV file and upload to Google Sheets :

#    $ source .browbeat-venv/bin/activate && cd utils
#    $ python rally_google_sheet_gen.py -c -f <path to directory to write csv file locally>
#      -j <path to rally json file>
#      -a <space separated list of atomic actions(Eg.: boot_server create_network)> -g
#      -s <path to google service account json credentials file>
#      -e <email id of user> -n <name of google sheet to be created>

import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import cellFormat
from gspread_formatting import format_cell_range
from gspread_formatting import set_column_width
from gspread_dataframe import set_with_dataframe
import argparse

def add_atomic_action_data_to_df(json_file_paths, atomic_action, df_dict, df_sla_fail_dict,
                                 sla_duration, sla_enabled):
    """Convert rally json data to csv file containing atomic action data
    :param json_file_path: str, list containing paths to rally json files
    :param atomic_action: str, atomic action to generate duration data
    :param df_dict: dict, dict of dataframes from different atomic actions
    :param df_sla_fail_dict: dict, dict of dataframes from different atomic actions that fails sla
    :param sla_duration: int, max duration allowed as per sla
    :param sla_enabled: bool, variable that determines whether sla criteria should be considered
    """
    for json_file_path in json_file_paths:
        json_file = open(json_file_path)
        json_data = json.load(json_file)

        df = pd.DataFrame({"Resource Number": [], "Duration(in seconds)": []})

        if sla_enabled:
            df_sla_fail = pd.DataFrame({"Resource Number": [], "Duration(in seconds)": []})

        resource_number = 1

        for iteration in json_data[0]["result"]:
            for atomic_action_json in iteration["atomic_actions"]:
                if atomic_action in atomic_action_json:
                    atomic_action_duration = iteration["atomic_actions"][atomic_action_json]
                    df = df.append({"Resource Number": resource_number,
                                    "Duration(in seconds)": atomic_action_duration},
                                   ignore_index=True)
                    if sla_enabled and atomic_action_duration > sla_duration:
                        df_sla_fail = df_sla_fail.append({"Resource Number": resource_number,
                                                          "Duration(in seconds)":
                                                          atomic_action_duration},
                                                         ignore_index=True)
                    resource_number += 1

        df_dict[(json_file_path, atomic_action)] = df

        if sla_enabled:
            df_sla_fail_dict[(json_file_path, atomic_action)] = df_sla_fail

        print("Pandas DF for json file {} and atomic action {} generated successfully.".format(
              json_file_path, atomic_action))


def generate_csv_from_df(csv_files_path, df_dict):
    """Generate csv files from pandas dataframe
    :param csv_files_path: str, path of directory to generate csv files
    :param df_dict: dict, dict of dataframes from different json files
    """
    for key in df_dict:
        json_file_name = key[0].split("/")[-1].split(".")[0]
        atomic_action = key[1]
        df_dict[key].to_csv("{}/{}_{}.csv".format(csv_files_path, json_file_name, atomic_action))
        print("{}/{}_{}.csv created successfully".format(csv_files_path,
                                                         json_file_name, atomic_action))

def push_to_gsheet(df_dict, df_sla_fail_dict, google_svc_acc_key, email_id, sheetname, sla_enabled):
    """Push csv file to Google Sheets
    :param df_dict: dict, dict of dataframes from different atomic actions
    :param df_sla_fail_dict: dict, dict of dataframes from different atomic actions that fails sla
    :param google_svc_acc_key: str, path to json credentials for google service account
    :param email_id: str, email id of user who will be given edit access to google sheet
    :param sheetname: str, used as the name of the sheet that's going to be generated
    :param sla_enabled: bool, variable that determines whether sla criteria should be considered
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

    sh = gc.create(sheetname)

    for key in df_dict:
        json_file_name = key[0].split("/")[-1].split(".")[0]
        atomic_action = key[1]
        ws_name = "{}_{}".format(json_file_name, atomic_action)
        ws = sh.add_worksheet(ws_name, rows=len(df_dict[key]), cols=2)
        set_with_dataframe(ws, df_dict[key])
        format_cell_range(ws, "1:1000", fmt)
        set_column_width(ws, "A", 290)
        set_column_width(ws, "B", 190)

        if sla_enabled:
            ws_name_sla = ws_name + "_sla_fail"
            ws = sh.add_worksheet(ws_name_sla,
                                  rows=len(df_sla_fail_dict[key]), cols=2)
            set_with_dataframe(ws, df_sla_fail_dict[key])
            format_cell_range(ws, "1:1000", fmt)
            set_column_width(ws, "A", 290)
            set_column_width(ws, "B", 190)

    sh.share(email_id, perm_type="user", role="writer")
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{sh.id}"
    print(f"Google Spreadsheet link -> {spreadsheet_url}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--generatecsvfiles', action='store_true', required=False,
        help='Flag to enable csv file generation', dest="generatecsvfiles"
    )
    parser.add_argument(
        "-f", "--csvfilespath", help="Path to directory to create CSV files",
        nargs='?', required=False, dest="csvfilespath"
    )
    parser.add_argument(
        "-j", "--jsonfilepaths", help="Rally JSON file paths to scrape output from",
        nargs='+', required=True, dest="jsonfilepaths",
    )
    parser.add_argument(
        "-a", "--atomicactions", help="Atomic actions to generate duration data",
        nargs='+', required=True, dest="atomicactions",
    )
    parser.add_argument(
        '-g', '--uploadtogooglesheets', action='store_true', required=False,
        help='Flag to enable upload to Google Sheets', dest="uploadtogooglesheets"
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
    parser.add_argument(
        "-v", "--sladuration", help="sla criteria for max duration",
        nargs='+', required=False, dest="sladuration",
    )
    params = parser.parse_args()

    if(params.generatecsvfiles and params.csvfilespath is None):
        parser.error("{} requires {}.".format("--generatecsvfiles",
                                              "--csvfilespath"))

    df_dict = {}
    sla_durations = []
    sla_enabled = True
    df_sla_fail_dict = {}

    if(params.uploadtogooglesheets and
       (params.sheetname is None or params.googlesvcacckey is None or params.emailid is None)):
        parser.error("{} requires {} and {} and {}.".format("--uploadtogooglesheets",
                                                            "--sheetname",
                                                            "--googlesvcacckey",
                                                            "--emailid"))

    if params.sladuration is None:
        sla_enabled = False

    if sla_enabled:
        if len(params.sladuration) != len(params.atomicactions):
            errmsg = ' '.join(("Invalid arguments passed.",
                               "The number of Atomic actions and SLA durations doesn't match."))
            raise Exception(errmsg)

        for sla_duration in params.sladuration:
            sla_durations.append(int(sla_duration))

    for i, atomic_action in enumerate(params.atomicactions):
        sla_duration = -1
        if sla_enabled:
            sla_duration = sla_durations[i]
        add_atomic_action_data_to_df(params.jsonfilepaths, atomic_action,
                                     df_dict, df_sla_fail_dict, sla_duration, sla_enabled)

    if params.generatecsvfiles:
        generate_csv_from_df(params.csvfilespath, df_dict)

    if params.uploadtogooglesheets:
        push_to_gsheet(df_dict, df_sla_fail_dict, params.googlesvcacckey, params.emailid,
                       params.sheetname, sla_enabled)
