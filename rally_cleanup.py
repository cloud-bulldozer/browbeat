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

import os
import time
from multiprocessing import Pool
from rally.common import cfg
from rally.common import logging

from rally_openstack import osclients

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
# Define http timeout to avoid traceback
CONF.openstack_client_http_timeout = 180.0

# Get Openstack clients
osclient = osclients.Clients.create_from_env()
nova_client = osclient.nova(version="2.73")
neutron_client = osclient.neutron()
keystone_client = osclient.keystone()

# Currently we only check and delete router_interface
# and not DVR or HA interface
ROUTER_INTERFACE_OWNERS = ("network:router_interface",
                           "network:router_interface_distributed",
                           "network:ha_router_replicated_interface")
# Exclude deleting these networks
NETWORK_EXCLUDE = ["public", "lb-mgmt-net"]

# number of processes swapned to delete resources concurrently
CONCURRENCY = 16

# Cleanup of a resource is retried by these many times
MAX_ATTEMPTS = 7

# number of times we check if the resource still exist after giving a delete request
MAX_CHECK = 6


def delete_server(resource):
    server = nova_client.servers.get(resource.id)
    print("pid {} deleting server id {} name {}".format(
        os.getpid(), resource.id, server.name))
    nova_client.servers.delete(server)
    for i in range(0, MAX_CHECK):
        try:
            nova_client.servers.get(resource.id)
            print("pid {} server {} still exists".format(os.getpid(), resource.id))
        except Exception:
            print("pid {} server {} succesfully deleted".format(os.getpid(), resource.id))
            break
        time.sleep(5)
    return resource


def delete_network(resource):
    network = neutron_client.show_network(resource.id)["network"]
    print("pid {} deleting network id {} name {}".format(
        os.getpid(), resource.id, network["name"]))
    # delete network
    neutron_client.delete_network(network["id"])
    # check if network got deleted or not
    for i in range(0, MAX_CHECK):
        try:
            neutron_client.show_network(resource.id)["network"]
            print("pid {} network {} still exists".format(os.getpid(), resource.id))
        except Exception:
            print("pid {} network {} succesfully deleted".format(os.getpid(), resource.id))
            break
        time.sleep(5)
    return resource

def delete_security_group(resource):
    sg = neutron_client.show_security_group(resource.id)["security_group"]
    print("pid {} deleting security_group id {} name {}".format(
        os.getpid(), resource.id, sg["name"]))
    # delete security_group
    neutron_client.delete_security_group(sg["id"])
    # check if security_group got deleted or not
    for i in range(0, MAX_CHECK):
        try:
            neutron_client.show_security_group(resource.id)["security_group"]
            print("pid {} security_group {} still exists".format(os.getpid(), resource.id))
        except Exception:
            print("pid {} security_group {} succesfully deleted".format(os.getpid(), resource.id))
            break
        time.sleep(5)
    return resource

def delete_floatingip(resource):
    floatingip = neutron_client.show_floatingip(resource.id)["floatingip"]
    print("pid {} deleting floatingip id {} address {}".format(
        os.getpid(), resource.id, floatingip["floating_ip_address"]))
    neutron_client.delete_floatingip(resource.id)
    # check if floatingip got deleted or not
    for i in range(0, MAX_CHECK):
        try:
            neutron_client.show_floatingip(resource.id)["floatingip"]
            print("pid {} floatingip {} still exists".format(os.getpid(), resource.id))
        except Exception:
            print("pid {} floatingip {} succesfully deleted".format(os.getpid(), resource.id))
            break
        time.sleep(5)
    return resource


def delete_router(resource):
    router = neutron_client.show_router(resource.id)["router"]
    print(router)
    print("pid {} deleting router id {} name {}".format(
        os.getpid(), resource.id, router["name"]))
    try:
        neutron_client.remove_gateway_router(resource.id)
    except Exception:
        print("pid {} router id {} gateway doesn't exist".format(os.getpid(), resource.id))
    time.sleep(5)
    neutron_client.delete_router(router["id"])
    # check if router got deleted or not
    for i in range(0, MAX_CHECK):
        try:
            neutron_client.show_router(resource.id)["router"]
            print("pid {} router {} still exists".format(os.getpid(), resource.id))
        except Exception:
            print("pid {} router {} succesfully deleted".format(os.getpid(), resource.id))
            break
        time.sleep(5)
    return resource


def delete_router_ports(resource):
    port = neutron_client.show_port(resource.id)["port"]
    print(port)
    if (port["device_owner"] not in ROUTER_INTERFACE_OWNERS):
        return resource
    print("pid {} deleting router {} port id {}".format(
        os.getpid(), port["device_id"], resource.id))
    neutron_client.remove_interface_router(port["device_id"], {"port_id": port["id"]})
    time.sleep(5)
    neutron_client.delete_port(port["id"])
    # check if port got deleted or not
    for i in range(0, MAX_CHECK):
        try:
            neutron_client.show_port(resource.id)["port"]
            print("pid {} router port {} still exists".format(os.getpid(), resource.id))
        except Exception:
            print("pid {} router port {} succesfully deleted".format(os.getpid(), resource.id))
            break
        time.sleep(5)
    return resource


class Resource:
    def __init__(self, id):
        self.id = id

    def __getnewargs__(self):
            return self.id,


# Ir creates CONCURRENCY pool of processes. Each process runs the provided function.
# "map_async" will spwan the process with the function to run and with only one "unique"
# resource from the list of resources. None of the processes work on the same resource.
# For example, to delete networks, each process deletes a unique network.
def cleanup_with_concurrency(cleanup_fun, resources):
    ret = True
    with Pool(CONCURRENCY) as p:
        result = p.map_async(cleanup_fun, resources)
        # https://stackoverflow.com/questions/26063877/python-multiprocessing-module-join-processes-with-timeout
        # wait 50 seconds for every worker to finish
        # it is a cumulative timeout
        result.wait(timeout=60)
        try:
            # check if workers succesfully executed
            result.get(timeout=60)
        except Exception:
            ret = False
        try:
            # This will close succesfully exited processes and forcefully failed processes.
            p.terminate()
        except Exception:
            # close any leftover child processes
            p.close()
        p.join()
    return ret


def cleanup_nova_vms():
    while True:
        servers = nova_client.servers.list(detailed=True, search_opts={"all_tenants": 1}, limit=100)
        if (len(servers) == 0):
            break
        print("Deleting {} servers".format(len(servers)))
        ids = [Resource(server.id) for server in servers]
        cleanup_with_concurrency(delete_server, ids)
        time.sleep(5)


def cleanup_neutron_networks():
    for i in range(0, MAX_ATTEMPTS):
        networks = neutron_client.list_networks()["networks"]
        if (len(networks) == 0):
            break
        ids = [Resource(network["id"]) for network in networks
               if network["name"] not in NETWORK_EXCLUDE]
        if (len(ids) == 0):
            break
        print("Deleting {} networks".format(len(ids)))
        if cleanup_with_concurrency(delete_network, ids):
            break
        time.sleep(5)


def get_admin_security_group():
    projects = keystone_client.projects.list()
    admin_project = [project.id for project in projects if project.name == "admin"][0]
    sgs = neutron_client.list_security_groups(project=admin_project)["security_groups"]
    return [sg["id"] for sg in sgs if sg["name"] == "default"][0]


def cleanup_neutron_security_groups():
    # we shouldn't cleanup default security group created by admin
    default_sg = get_admin_security_group()
    while True:
        sgs = neutron_client.list_security_groups()["security_groups"]
        if (len(sgs) == 0):
            break
        ids = [Resource(sg["id"]) for sg in sgs
               if sg["id"] != default_sg]
        if (len(ids) == 0):
            break
        print("Deleting {} security_groups".format(len(ids)))
        if cleanup_with_concurrency(delete_security_group, ids):
            break
        time.sleep(5)


def cleanup_neutron_floatingips():
    while True:
        floatingips = neutron_client.list_floatingips()["floatingips"]
        if (len(floatingips) == 0):
            break
        print("Deleting {} floatingips".format(len(floatingips)))
        ids = [Resource(floatingip["id"]) for floatingip in floatingips]
        if cleanup_with_concurrency(delete_floatingip, ids):
            break
        time.sleep(5)


def _cleanup_neutron_router_ports():
    while True:
        ports = neutron_client.list_ports(device_owner='network:router_interface')["ports"]
        if (len(ports) == 0):
            break
        print("Deleting {} router ports".format(len(ports)))
        ids = [Resource(port["id"]) for port in ports]
        if cleanup_with_concurrency(delete_router_ports, ids):
            break
        time.sleep(5)


def cleanup_neutron_routers():
    _cleanup_neutron_router_ports()
    while True:
        routers = neutron_client.list_routers()["routers"]
        if (len(routers) == 0):
            break
        print("Deleting {} routers".format(len(routers)))
        ids = [Resource(router["id"]) for router in routers]
        if cleanup_with_concurrency(delete_router, ids):
            break
        time.sleep(5)


def cleanup_resources():
    cleanup_nova_vms()
    cleanup_neutron_floatingips()
    cleanup_neutron_routers()
    cleanup_neutron_security_groups()
    cleanup_neutron_networks()


cleanup_resources()
