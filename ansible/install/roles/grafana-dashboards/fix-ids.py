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
import argparse
import json


def main():
    """Script used to fix panel ids in static dashboards.  Typically adding a new panel or row into
    a static dashboard will involve re-ordering all subsequent panels.  This script automates that.
    """
    parser = argparse.ArgumentParser(description="Fix panel ids in grafana json dashboard.")
    parser.add_argument('inputfile', help='Input json file')
    parser.add_argument('outputfile', help='Output json file')
    args = parser.parse_args()

    with open(args.inputfile) as data_file:
        data = json.load(data_file)

    index = 0
    for row in data['dashboard']['rows']:
        for panel in row['panels']:
            index += 1
            if index != panel['id']:
                print "Found error in panel({}): {}".format(index, panel['title'])
                panel['id'] = index

    with open(args.outputfile, 'w') as outputfile:
        json.dump(data, outputfile, sort_keys=True, indent=2, separators=(',', ': '))

if __name__ == "__main__":
    main()
