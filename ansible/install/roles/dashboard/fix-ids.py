#!/usr/bin/env python
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
