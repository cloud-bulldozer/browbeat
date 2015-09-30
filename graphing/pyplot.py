import csv
from datetime import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook

services=['nova-scheduler','keystone-all','nova-api','nova-conductor']

# Build Struct.
data = {}
for service in services :
    data[service] = {}
    data[service]['datetime'] = []
    data[service]['host'] = []
    data[service]['maxconn'] = []
    data[service]['conn'] = []
    data[service]['ckout'] = []

reader = csv.DictReader(open('test001-nova-24-nova-boot-list-cc-0128-connmon_2015-09-29_192137.csv'))
for row in reader:
    for service in services :
        if row['progname'] == service :
            data[service]['datetime'].append(datetime.strptime(row['datetime'],'%Y-%m-%d %H:%M:%S'))
            data[service]['conn'].append(row['conn'])
            data[service]['maxconn'].append(row['maxconn'])

plt.title("Service : %s" % service)
plt.xlabel("Date Time")
plt.ylabel("Max Connections")
keystone,=plt.plot_date(data['keystone-all']['datetime'][1::30],data['keystone-all']['maxconn'][1::30],'c',linewidth=2,label="keystone")
conductor,=plt.plot_date(data['nova-conductor']['datetime'][1::30],data['nova-conductor']['maxconn'][1::30],'g',linewidth=2, label="nova-condcutor")
api,=plt.plot_date(data['nova-api']['datetime'][1::30],data['nova-api']['maxconn'][1::30],'r',linewidth=2,label="nova-api")
scheduler,=plt.plot_date(data['nova-scheduler']['datetime'][1::30],data['nova-scheduler']['maxconn'][1::30],'b',linewidth=2, label="nova-scheduler")
plt.legend([keystone,conductor,api,scheduler],['keystone','nova-conductor','nova-api','nova-scheduler'])
plt.show()
