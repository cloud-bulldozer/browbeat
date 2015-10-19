import csv
import json
import sys
import getopt
from collections import defaultdict

def main(argv):
    inputfile = None

    try:
        opts, args = getopt.getopt(argv,"c",["csv="])
    except :
        print "csv-to-json.py --csv=<inputfile>"
        sys.exit(2)

    for opt, arg in opts:
       if opt == '-h':
           print 'csv-to-json.py --csv=<inputfile>'
           sys.exit()
       elif opt in ("-c", "--csv"):
           inputfile = arg
    if inputfile == None :
        print "Error : No input file passed"
        print "Usage:"
        print "csv-to-json.py --csv=<inputfile>"
        sys.exit(2)

    print "Opening %s" % inputfile
    csvFile =  open(inputfile)
    data = list(csv.reader(csvFile))

if __name__ == "__main__":
    main(sys.argv[1:])
