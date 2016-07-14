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
"""Gets a token using rc file credentials."""
from keystoneclient.v2_0 import client
import os
import sys

os_auth_url = os.environ.get('OS_AUTH_URL')
os_username = os.environ.get('OS_USERNAME')
os_password = os.environ.get('OS_PASSWORD')

if os_auth_url is None or os_username is None or os_password is None:
    print "source rc file(stackrc/overcloudrc etc) before running."
    sys.exit(1)

project_scoped = client.Client(
    username=os_username,
    password=os_password,
    project_name='admin',
    auth_url=os_auth_url)

print('%s' % project_scoped.auth_token)
