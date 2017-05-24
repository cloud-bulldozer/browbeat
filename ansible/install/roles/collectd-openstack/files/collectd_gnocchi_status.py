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

    gnocchi = client.Client(session=keystone_session)
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

def create_keystone_session():
    auth = v2.Password(username=os_username,
        password=os_password,
        tenant_name=os_tenant,
        auth_url=os_auth_url)
    return session.Session(auth=auth)

os_username = os.environ.get('OS_USERNAME')
os_password = os.environ.get('OS_PASSWORD')
os_tenant = os.environ.get('OS_TENANT_NAME')
if os_tenant is None:
  os_tenant = os.environ.get('OS_PROJECT_NAME')
os_auth_url = os.environ.get('OS_AUTH_URL')

collectd.info('gnocchi_status: Connecting with user={}, password={}, tenant/project={}, '
    'auth_url={}'.format(os_username, os_password, os_tenant, os_auth_url))

keystone_session = create_keystone_session()
collectd.register_config(configure)
