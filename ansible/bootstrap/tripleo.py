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

from collections import defaultdict
import logging
import os
import re
import shutil
import time

LOG = logging.getLogger("browbeat.tripleo")


def register(installer_types, subparser):
    installer_types["tripleo"] = tripleo
    tripleo_parser = subparser.add_parser("tripleo",
                                          description="Bootstrap implementation for tripleo clouds")
    help_text = ("IP address of tripleo undercloud.  Defaults to 'localhost'. Currently only "
                 "localhost is supported.")
    tripleo_parser.add_argument("-i", "--tripleo-ip", default="localhost", type=str, help=help_text)
    help_text = "User used for tripleo install.  Defaults to 'stack'."
    tripleo_parser.add_argument("-u", "--user", default="stack", type=str, help=help_text)


class tripleo(object):

    def bootstrap(self, working_dir, cliargs):
        """Generates three files in order to install and operate tripleo cloud for Browbeat."""
        start_time = time.time()
        LOG.info("Bootstrap via tripleo installer")

        stack_id_rsa = "/home/stack/.ssh/id_rsa"
        ha_id_rsa = os.path.join(working_dir, "heat-admin-id_rsa")
        ssh_config = os.path.join(working_dir, "ssh-config")
        ansible_inventory_file = os.path.join(working_dir, "hosts")
        LOG.debug("working directory: {}".format(working_dir))
        LOG.debug("ssh-config file: {}".format(ssh_config))
        LOG.debug("Ansible inventory file: {}".format(ansible_inventory_file))

        if cliargs.tripleo_ip == "localhost" or cliargs.tripleo_ip == "127.0.0.1":
            if os.path.isfile(stack_id_rsa):
                shutil.copy2(stack_id_rsa, ha_id_rsa)
            else:
                LOG.error("Tripleo ip is localhost but unable to find {}".format(stack_id_rsa))
                exit(1)
        else:
            LOG.error("Currently only localhost is supported for tripleo.bootstrap")
            exit(1)

        if "OS_USERNAME" not in os.environ:
            LOG.error("OS_USERNAME not found in environment variables: source stackrc")
            exit(1)

        os_username = os.environ["OS_USERNAME"]
        os_password = os.environ["OS_PASSWORD"]
        os_auth_url = os.environ["OS_AUTH_URL"]
        os_user_domain_name = None
        os_project_domain_name = None
        if "OS_USER_DOMAIN_NAME" in os.environ:
            os_user_domain_name = os.environ["OS_USER_DOMAIN_NAME"]
        if "OS_PROJECT_DOMAIN_NAME" in os.environ:
            os_project_domain_name = os.environ["OS_PROJECT_DOMAIN_NAME"]

        if "OS_PROJECT_NAME" in os.environ:
            project_name = os.environ["OS_PROJECT_NAME"]
        elif "OS_TENANT_NAME" in os.environ:
            project_name = os.environ["OS_TENANT_NAME"]
        else:
            LOG.error("Missing OS_PROJECT_NAME or OS_TENANT_NAME in rc file")
            exit(1)

        LOG.debug("os_username: {}".format(os_username))
        LOG.debug("os_password: {}".format(os_password))
        LOG.debug("os_auth_url: {}".format(os_auth_url))
        LOG.debug("project_name: {}".format(project_name))
        LOG.debug("os_user_domain_name: {}".format(os_user_domain_name))
        LOG.debug("os_project_domain_name: {}".format(os_project_domain_name))

        # Lazy import due to pluggable bootstrapping
        from openstack import connection

        conn = connection.Connection(
            auth_url=os_auth_url,
            username=os_username,
            password=os_password,
            project_name=project_name,
            os_user_domain_name=os_user_domain_name,
            os_project_domain_name=os_project_domain_name,
            compute_api_version="2",
            identity_interface="internal")

        # Get the data needed
        servers = [server for server in conn.compute.servers()]
        baremetal_nodes = [node for node in conn.bare_metal.nodes()]

        inventory = defaultdict(dict)

        for server in conn.compute.servers():
            for baremetal_node in baremetal_nodes:
                if server.id == baremetal_node.instance_id:
                    group = re.search(r"overcloud-([a-zA-Z0-9_]+)-[0-9]+$", server.name).group(1)
                    LOG.debug("Matched: {} : ironic_uuid={}".format(server.name, baremetal_node.id))
                    if group:
                        # Unfortunately the easiest way to work with this data is to examine the
                        # server's name and see if it contains the "group" we most likely associate
                        # with the server's role.
                        if "compute" in group:
                            group = "compute"
                        inventory[group][server.name] = "{} ironic_uuid={}".format(
                            server.name, baremetal_node.id)
                    else:
                        LOG.warn("Unidentified group for server: {}".format(server.name))
                        inventory["other"][server.name] = "{} ironic_uuid={}".format(
                            server.name, baremetal_node.id)
                    break

        self._generate_ssh_config(ssh_config, ha_id_rsa, cliargs.tripleo_ip, cliargs.user, servers)
        self._generate_inventory(ansible_inventory_file, inventory)

        LOG.info("Completed bootstrap in {}".format(round(time.time() - start_time, 2)))

    def _generate_inventory(self, inventoryfile, inventory):
        with open(inventoryfile, "w") as f:
            f.write("# Generated by bootstrap.py (tripleo) from Browbeat\n")
            f.write("[browbeat]\n")
            f.write("# Pick host depending on desired install\n")
            f.write("localhost\n")
            f.write("#undercloud\n")
            f.write("\n")
            f.write("[undercloud]\n")
            f.write("undercloud\n")
            f.write("\n")
            for group in inventory.keys():
                f.write("[{}]\n".format(group))
                for node in sorted(inventory[group].keys()):
                    f.write("{}\n".format(inventory[group][node]))
                f.write("\n")
            f.write("[overcloud:children]\n")
            for group in inventory.keys():
                f.write("{}\n".format(group))
            f.write("\n")

    def _generate_ssh_config(self, sshfile, ha_id_rsa, tripleo_ip, tripleo_user, servers):
        with open(sshfile, "w") as f:
            f.write("# Generated by bootstrap.py (tripleo) from Browbeat\n")
            f.write("\n")
            f.write("Host undercloud\n")
            f.write("    Hostname {}\n".format(tripleo_ip))
            f.write("    IdentityFile ~/.ssh/id_rsa\n")
            f.write("    StrictHostKeyChecking no\n")
            f.write("    UserKnownHostsFile=/dev/null\n")
            f.write("\n")
            f.write("Host undercloud-root\n")
            f.write("    Hostname {}\n".format(tripleo_ip))
            f.write("    User root\n")
            f.write("    IdentityFile ~/.ssh/id_rsa\n")
            f.write("    StrictHostKeyChecking no\n")
            f.write("    UserKnownHostsFile=/dev/null\n")
            f.write("\n")
            f.write("Host undercloud-{}\n".format(tripleo_user))
            f.write("    Hostname {}\n".format(tripleo_ip))
            f.write("    User {}\n".format(tripleo_user))
            f.write("    IdentityFile ~/.ssh/id_rsa\n")
            f.write("    StrictHostKeyChecking no\n")
            f.write("    UserKnownHostsFile=/dev/null\n")
            pcmd = ("    ProxyCommand ssh -F {} -o UserKnownHostsFile=/dev/null"
                    " -o StrictHostKeyChecking=no -o ConnectTimeout=60 -i ~/.ssh/id_rsa"
                    " {}@{} -W {}:22\n")
            for server in servers:
                LOG.debug("{} - {}".format(server.name, server.addresses["ctlplane"][0]["addr"]))
                f.write("\n")
                f.write("Host {}\n".format(server.name))
                f.write(pcmd.format(sshfile, tripleo_user, tripleo_ip,
                                    server.addresses["ctlplane"][0]["addr"]))
                f.write("    User heat-admin\n")
                f.write("    IdentityFile {}\n".format(ha_id_rsa))
                f.write("    StrictHostKeyChecking no\n")
                f.write("    UserKnownHostsFile=/dev/null\n")
