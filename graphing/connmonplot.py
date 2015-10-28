import csv
from collections import Counter
import sys
from datetime import datetime
import matplotlib
import numpy as np
import ntpath
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
from pylab import rcParams
rcParams['figure.figsize'] = 18, 10

services=['/usr/bin/nova-scheduler','/usr/bin/keystone-all','/usr/bin/nova-api','/usr/bin/nova-conductor']
color_wheel=['r','g','b','y']

data = {}
average = {}
for service in services :
    data[service] = {}
    average[service] = {}
    average[service]['connection_count_avg'] = 0
    average[service]['max_checkedout_avg'] = 0
    average[service]['checkouts_per_second_avg'] = 0

reader = csv.DictReader(open(sys.argv[1]))
for row in reader:
    for service in services :
        if not row['hostname'] in data[service].keys() :
            data[service][row['hostname']] = {}
            data[service][row['hostname']]['timestamp'] = []
            data[service][row['hostname']]['hostname'] = []
            data[service][row['hostname']]['max_connections'] = []
            data[service][row['hostname']]['checkout_count'] = []
            data[service][row['hostname']]['connection_count'] = []
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

    print "Building Graph of connections per host second for : %s" % service
    plt.title("Database Connections : Service : %s" % service)
    plt.xlabel("Time")
    plt.ylabel("Connections")
    pos=0
    for host in data[service] :
        controller,=plt.plot_date(data[service][host]['timestamp'],
                                    data[service][host]['connection_count'],
                                    'c',
                                    linewidth=5,label="%s-controller0-conn"%service)

        controller2,=plt.plot_date(data[service][host]['timestamp'],
                                    data[service][host]['checkout_count'],
                                    'c',
                                    linewidth=3,
                                    label="%s-controller0-ckout"%service)

        controller1,=plt.plot_date(data[service][host]['timestamp'],
                                    data[service][host]['max_checkedout'],
                                    'c',
                                    linewidth=1,
                                    label="%s-controller0-max_checkedout"%service)

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
    print "Building Graph of checkouts per second for : %s" % service
    pos=0
    for host in data[service] :
        plt.title("Database Checkouts Per-Second : Service : %s" % service)
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

#
# Sum connections across controllers
#
#
    print "Building Graph of sum of connections for : %s" % service
    num_controllers=len(data[service].keys())
    pos=0
    total_connections = np.array([])
    total_checkouts = np.array([])
    total_maxcheckouts = np.array([])
    for host in data[service] :
        plt.title("Database Connections : Service : %s" % service)
        plt.xlabel("Time")
        plt.ylabel("Connections")
        if pos == 0 :
            total_connections = np.array(data[service][host]['connection_count']).astype(np.float)
            total_checkouts = np.array(data[service][host]['checkout_count']).astype(np.float)
            total_maxcheckouts = np.array(data[service][host]['max_checkedout']).astype(np.float)

        elif pos <= num_controllers :
            if total_connections.size < len(data[service][host]['connection_count']):
                 data[service][host]['connection_count'] = np.resize(data[service][host]['connection_count'],total_connections.size)
            else:
                 total_connections = np.resize(total_connections,len(data[service][host]['connection_count']))

            if total_checkouts.size < len(data[service][host]['checkout_count']):
                 data[service][host]['checkout_count'] = np.resize(data[service][host]['checkout_count'],total_checkouts.size)
            else:
                 total_checkouts = np.resize(total_checkouts,len(data[service][host]['checkout_count']))

            if total_maxcheckouts.size < len(data[service][host]['max_checkedout']):
                 data[service][host]['max_checkedout'] = np.resize(data[service][host]['max_checkedout'],total_maxcheckouts.size)
            else:
                 total_maxcheckouts = np.resize(total_maxcheckouts,len(data[service][host]['max_checkedout']))

            total_connections = np.add(total_connections, np.array(data[service][host]['connection_count']).astype(np.float))
            total_checkouts= np.add(total_checkouts, np.array(data[service][host]['checkout_count']).astype(np.float))
            total_maxcheckouts= np.add(total_maxcheckouts, np.array(data[service][host]['max_checkedout']).astype(np.float))

        pos=pos+1

    plt.title("Database Connections : Service : %s" % service)
    plt.xlabel("Time")
    plt.ylabel("Connections")
    pos=0
    controller,=plt.plot_date(data[service][host]['timestamp'],
                               total_connections,
                               'c',
                               linewidth=5,label="%s-controllers-conn"%service)

    controller2,=plt.plot_date(data[service][host]['timestamp'],
                               total_checkouts,
                               'c',
                               linewidth=3,
                               label="%s-controllers-ckout"%service)

    controller1,=plt.plot_date(data[service][host]['timestamp'],
                               total_maxcheckouts,
                               'c',
                               linewidth=1,
                               label="%s-controllers-max_checkedout"%service)

    controller.set_color(color_wheel[pos])
    controller1.set_color(color_wheel[pos+1])
    controller2.set_color(color_wheel[pos+2])

    plt.legend(["%s-controllers-sum-conn"%service,
        "%s-controllers-sum-ckout"%service,
        "%s-controllers-sum-maxckout"%service])

    plt.savefig("%s_%s-connctions-all.png"%(sys.argv[1],ntpath.basename(service)), bbox_inches='tight')
    plt.close()
