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

import sys
import os
import subprocess
# usage: openstack-log-locator.py [service]-[component]
# returns the location of a given logfile depending on if the service
# is or is not containerized.


def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    output_dict = {}
    output_dict['stdout'] = stdout.strip()
    output_dict['stderr'] = stderr.strip()
    output_dict['rc'] = process.returncode
    return output_dict


def is_containerized(service_name):
    out = run_cmd("docker ps")
    return service_name in out['stdout']


def get_logfile_list(path, extension='.log'):
    configs = []
    for item in os.listdir(path):
        if item.endswith(extension):
            configs.extend([item])
    return configs


def print_config_entry(service_name, log_location):
    config_entry = "input(type=\"imfile\"\n \
                          File=\"{}\"\n \
                          Tag=\"{}\"\n \
                          Severity=\"info\"\n \
                          Facility=\"local7\") \n"
    print(config_entry.format(log_location, service_name, log_location))

# In an ideal world there wouldn't be logs changing all the time
# but we don't live in that world, this dynamically grabs the name
# of earch logfile and turns it into an appropriate tag.


def log_to_service(service_name, log_name):
    # strip extension
    title = log_name.split('.')[0]
    if service_name.lower() in log_name.lower():
        return title
    else:
        string = "{}-{}".format(service_name, title)
        return string


def main():
    if len(sys.argv) != 2:
        print("usage: openstack-config-parser.py [service]")
        exit(1)

    service_name = sys.argv[1]

    in_container = is_containerized(service_name)

    log_path_container = "/var/log/containers/{}".format(service_name)
    log_path_nocontainer = "/var/log/{}".format(service_name)
    if os.path.isdir(log_path_container) and len(
            get_logfile_list(log_path_container)) > 0 and in_container:
        log_path = "/var/log/containers/{}".format(service_name)
    elif os.path.isdir(log_path_nocontainer) \
            and len(get_logfile_list(log_path_nocontainer)):
        log_path = "/var/log/{}".format(service_name)
    else:
        print("# {} is not installed".format(service_name))
        exit(0)

    output = {}
    for item in get_logfile_list(log_path):
        full_path = "{}/{}".format(log_path,
                                   item)

        print_config_entry(log_to_service(service_name, item),
                           full_path)


if __name__ == '__main__':
    sys.exit(main())
