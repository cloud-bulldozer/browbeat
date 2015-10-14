import csv
import sys
from datetime import datetime
import matplotlib
import ntpath
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
from pylab import rcParams
rcParams['figure.figsize'] = 18, 10

services=['/usr/bin/nova-scheduler','/usr/bin/keystone-all','/usr/bin/nova-api','/usr/bin/nova-conductor']
color_wheel=['r','g','b','y']

data = {}
for service in services :
    data[service] = {}

reader = csv.DictReader(open(sys.argv[1]))
for row in reader:
    for service in services :
        if not row['hostname'] in data[service].keys() :
            data[service][row['hostname']] = {}
            data[service][row['hostname']]['timestamp'] = []
            data[service][row['hostname']]['hostname'] = []
            data[service][row['hostname']]['max_connections'] = []
            data[service][row['hostname']]['connection_count'] = []
            data[service][row['hostname']]['checkout_count'] = []

        if row['progname'] == service :
            data[service][row['hostname']]['timestamp'].append(datetime.strptime(row['timestamp'],'%Y-%m-%d %H:%M:%S'))
            data[service][row['hostname']]['connection_count'].append(row['connection_count'])
            data[service][row['hostname']]['max_connections'].append(row['max_connections'])
            data[service][row['hostname']]['checkout_count'].append(row['checkout_count'])

for service in data :
    pos=0
    for host in data[service] :
        plt.title("Service : %s" % service)
        plt.xlabel("Time")
        plt.ylabel("Max Connections")
        controller,=plt.plot_date(data[service][host]['timestamp'][1::30],data[service][host]['connection_count'][1::30],'c',linewidth=2,label="%s-controller0"%service)
        controller.set_color(color_wheel[pos])
        pos=pos+1

    plt.legend(["%s-controller0"%service,"%s-controller1"%service,"%s-controller2"%service])
    plt.savefig("%s_%s-connction_count.png"%(sys.argv[1],ntpath.basename(service)), bbox_inches='tight')
    plt.close()

    pos=0
    for host in data[service] :
        plt.title("Service : %s" % service)
        plt.xlabel("Time")
        plt.ylabel("Connections")
        controller,=plt.plot_date(data[service][host]['timestamp'][1::30],data[service][host]['connection_count'][1::30],'c',linewidth=4,label="%s-controller0-conn"%service)
        controller1,=plt.plot_date(data[service][host]['timestamp'][1::30],data[service][host]['checkout_count'][1::30],'c',linewidth=1,label="%s-controller0-ckout"%service)
        controller.set_color(color_wheel[pos])
        controller1.set_color(color_wheel[pos])
        pos=pos+1

    plt.legend(["%s-controller0-conn"%service,"%s-controller0-ckout"%service,"%s-controller1-conn"%service,"%s-controller1-ckout"%service,"%s-controller2-conn"%service,"%s-controller2-ckout"%service])
    plt.savefig("%s_%s-connctions.png"%(sys.argv[1],ntpath.basename(service)), bbox_inches='tight')
    plt.close()
