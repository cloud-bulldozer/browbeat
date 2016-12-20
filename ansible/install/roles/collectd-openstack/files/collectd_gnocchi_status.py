#!/usr/bin/env python
"""Collectd python plugin to read gnocchi status on an OpenStack Controller."""
from gnocchiclient.v1 import client
from keystoneauth1.identity import v2
from keystoneauth1 import session
import collectd
import os
import time


def configure(configobj):
    global INTERVAL

    config = {c.key: c.values for c in configobj.children}
    INTERVAL = 10
    if 'interval' in config:
        INTERVAL = config['interval'][0]
    collectd.info('gnocchi_status: Interval: {}'.format(INTERVAL))
    collectd.register_read(read, INTERVAL)

def read(data=None):
    starttime = time.time()

    auth = v2.Password(username=os_username,
        password=os_password,
        tenant_name=os_tenant,
        auth_url=os_auth_url)
    sess = session.Session(auth=auth)

    gnocchi = client.Client(session=sess)
    status = gnocchi.status.get()

    metric = collectd.Values()
    metric.plugin = 'gnocchi_status'
    metric.interval = INTERVAL
    metric.type = 'gauge'
    metric.type_instance = 'measures'
    metric.values = [status['storage']['summary']['measures']]
    metric.dispatch()

    metric = collectd.Values()
    metric.plugin = 'gnocchi_status'
    metric.interval = INTERVAL
    metric.type = 'gauge'
    metric.type_instance = 'metrics'
    metric.values = [status['storage']['summary']['metrics']]
    metric.dispatch()

    timediff = time.time() - starttime
    if timediff > INTERVAL:
        collectd.warning('gnocchi_status: Took: {} > {}'.format(round(timediff, 2),
            INTERVAL))

os_username = os.environ.get('OS_USERNAME')
os_password = os.environ.get('OS_PASSWORD')
os_tenant = os.environ.get('OS_TENANT_NAME')
os_auth_url = os.environ.get('OS_AUTH_URL')

collectd.info('gnocchi_status: Connecting with user={}, password={}, tenant={}, '
    'auth_url={}'.format(os_username, os_password, os_tenant, os_auth_url))
collectd.register_config(configure)
