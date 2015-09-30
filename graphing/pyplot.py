import csv
import sys
from datetime import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
from pylab import rcParams
rcParams['figure.figsize'] = 18, 10

services=['nova-scheduler','keystone-all','nova-api','nova-conductor']
color_wheel=['r','g','b']

data = {}
for service in services :
    data[service] = {}

reader = csv.DictReader(open(sys.argv[1]))
for row in reader:
    for service in services :
        if not row['host'] in data[service].keys() :
            data[service][row['host']] = {}
            data[service][row['host']]['datetime'] = []
            data[service][row['host']]['host'] = []
            data[service][row['host']]['maxconn'] = []
            data[service][row['host']]['conn'] = []
            data[service][row['host']]['ckout'] = []

        if row['progname'] == service :
            data[service][row['host']]['datetime'].append(datetime.strptime(row['datetime'],'%Y-%m-%d %H:%M:%S'))
            data[service][row['host']]['conn'].append(row['conn'])
            data[service][row['host']]['maxconn'].append(row['maxconn'])

for service in data :
    pos=0
    for host in data[service] :
        plt.title("Service : %s" % service)
        plt.xlabel("Time")
        plt.ylabel("Max Connections")
        controller,=plt.plot_date(data[service][host]['datetime'][1::30],data[service][host]['maxconn'][1::30],'c',linewidth=2,label="%s-controller0"%service)
        controller.set_color(color_wheel[pos])
        pos=pos+1

    plt.legend(["%s-controller0"%service,"%s-controller1"%service,"%s-controller2"%service])
    plt.savefig("%s_%s-maxconnctions.png"%(sys.argv[1],service), bbox_inches='tight')
    plt.close()
