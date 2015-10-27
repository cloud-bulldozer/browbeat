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
            data[service][row['hostname']]['max_checkedout'] = []
            data[service][row['hostname']]['checkouts_per_second'] = []

        if row['progname'] == service :
            data[service][row['hostname']]['timestamp'].append(datetime.strptime(row['timestamp'],
                                                                                '%Y-%m-%d %H:%M:%S'))
            data[service][row['hostname']]['connection_count'].append(row['connection_count'])
            data[service][row['hostname']]['max_connections'].append(row['max_connections'])
            data[service][row['hostname']]['checkout_count'].append(row['checkout_count'])
            data[service][row['hostname']]['max_checkedout'].append(row['max_checkedout'])
            data[service][row['hostname']]['checkouts_per_second'].append(row['checkouts_per_second'])

#
# Graph connections across each controller.
#
for service in data :
    pos=0
    for host in data[service] :
        plt.title("Service : %s" % service)
        plt.xlabel("Time")
        plt.ylabel("Connections")
        controller,=plt.plot_date(data[service][host]['timestamp'],
                                    data[service][host]['connection_count'],
                                    'c',
                                    linewidth=4,label="%s-controller0-conn"%service)

        controller1,=plt.plot_date(data[service][host]['timestamp'],
                                    data[service][host]['connection_count'],
                                    'c',
                                    linewidth=4,
                                    label="%s-controller0-conn"%service)

        controller2,=plt.plot_date(data[service][host]['timestamp'],
                                    data[service][host]['checkout_count'],
                                    'c',
                                    linewidth=2,
                                    label="%s-controller0-ckout"%service)

        controller.set_color(color_wheel[pos])
        controller1.set_color(color_wheel[pos])
        controller2.set_color(color_wheel[pos])
        pos=pos+1

    plt.legend(["%s-controller0-conn"%service,
                "%s-controller0-ckout"%service,
                "%s-controller0-max-ckout"%service,
                "%s-controller1-conn"%service,
                "%s-controller1-ckout"%service,
                "%s-controller1-max-ckout"%service,
                "%s-controller2-conn"%service,
                "%s-controller2-ckout"%service,
                "%s-controller2-max-ckout"%service])

    plt.savefig("%s_%s-connctions.png"%(sys.argv[1],ntpath.basename(service)), bbox_inches='tight')
    plt.close()

#
# Graph checkouts per second across each controller.
#
    pos=0
    for host in data[service] :
        plt.title("Checkouts Per-Second : Service : %s" % service)
        plt.xlabel("Time")
        plt.ylabel("Connections")

        controller,=plt.plot_date(data[service][host]['timestamp'],
                                    data[service][host]['checkouts_per_second'],
                                    'c',
                                    linewidth=1,
                                    label="%s-controller0-ckout"%service)

        controller.set_color(color_wheel[pos])
        pos=pos+1

    plt.legend(["%s-controller0-ckout-persec"%service,
                "%s-controller1-ckout-persec"%service,
                "%s-controller2-ckout-persec"%service])
    plt.savefig("%s_%s-connctions-checkout-persec.png"%
                (sys.argv[1],
                ntpath.basename(service)),
                bbox_inches='tight')
    plt.close()
