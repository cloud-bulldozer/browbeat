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

import random
import string


def _generate_name(prefix="wf_neutron_"):
    """Generate a random name following Rally's naming convention."""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return "{}{}".format(prefix, suffix)


def _neutron_client(wf):
    """Get the neutron client from workflow's os_clients.

    This returns the same neutronclient that Rally's NeutronScenario uses
    internally via self.clients("neutron").
    """
    return wf.os_clients.neutron()


def get_handlers(workflow_instance):
    """Return neutron operation handlers.

    All handlers use the same neutron client and patterns as Rally's
    NeutronScenario (rally_openstack.task.scenarios.neutron.utils).

    Args:
        workflow_instance: Workflow instance providing os_clients and logger

    Returns:
        dict: Mapping of operation type strings to handler callables
    """
    return {
        'neutron.create_network': lambda args, step: create_network(workflow_instance, args, step),
        'neutron.delete_network': lambda args, step: delete_network(workflow_instance, args, step),
        'neutron.list_networks': lambda args, step: list_networks(workflow_instance, args, step),
        'neutron.create_subnet': lambda args, step: create_subnet(workflow_instance, args, step),
        'neutron.delete_subnet': lambda args, step: delete_subnet(workflow_instance, args, step),
        'neutron.create_router': lambda args, step: create_router(workflow_instance, args, step),
        'neutron.delete_router': lambda args, step: delete_router(workflow_instance, args, step),
        'neutron.add_interface_router': lambda args, step: add_interface_router(
            workflow_instance, args, step),
        'neutron.remove_interface_router': lambda args, step: remove_interface_router(
            workflow_instance, args, step),
        'neutron.create_port': lambda args, step: create_port(workflow_instance, args, step),
        'neutron.delete_port': lambda args, step: delete_port(workflow_instance, args, step),
        'neutron.create_security_group': lambda args, step: create_security_group(
            workflow_instance, args, step),
        'neutron.delete_security_group': lambda args, step: delete_security_group(
            workflow_instance, args, step),
        'neutron.create_security_group_rule': lambda args, step: create_security_group_rule(
            workflow_instance, args, step),
        'neutron.create_floatingip': lambda args, step: create_floatingip(
            workflow_instance, args, step),
        'neutron.delete_floatingip': lambda args, step: delete_floatingip(
            workflow_instance, args, step),
        'neutron.list_floating_ips': lambda args, step: list_floating_ips(
            workflow_instance, args, step),
    }


# ---------------------------------------------------------------------------
# Network operations
# Pattern: NeutronScenario._create_network / _list_networks
# ---------------------------------------------------------------------------

def create_network(wf, args, step):
    """Create a network following Rally NeutronScenario._create_network pattern.

    Rally ref: NeutronScenario._create_network(network_create_args)
    Internally calls: clients("neutron").create_network({"network": args})
    """
    client = _neutron_client(wf)
    args.setdefault("name", _generate_name("wf_net_"))
    network = client.create_network({"network": args})

    wf.logger.info("Created network {} (ID: {})".format(
        network['network']['name'], network['network']['id']))

    return network['network']


def delete_network(wf, args, step):
    """Delete a network following Rally NeutronScenario._delete_network pattern.

    Rally ref: NeutronScenario._delete_network(network)
    Internally calls: clients("neutron").delete_network(network_id)
    """
    client = _neutron_client(wf)
    network_id = args.get('network_id') or args.get('id')

    if not network_id:
        raise Exception("network_id is required for neutron.delete_network")

    wf.logger.info("Deleting network (ID: {})".format(network_id))
    client.delete_network(network_id)

    return {'id': network_id, 'deleted': True}


def list_networks(wf, args, step):
    """List networks following Rally NeutronScenario._list_networks pattern.

    Rally ref: NeutronScenario._list_networks(**kwargs)
    Internally calls: clients("neutron").list_networks(**kwargs)
    """
    client = _neutron_client(wf)
    networks = client.list_networks(**args)

    wf.logger.info("Listed {} networks".format(len(networks.get('networks', []))))

    return networks['networks']


# ---------------------------------------------------------------------------
# Subnet operations
# Pattern: NeutronScenario._create_subnet
# ---------------------------------------------------------------------------

def create_subnet(wf, args, step):
    """Create a subnet following Rally NeutronScenario._create_subnet pattern.

    Rally ref: NeutronScenario._create_subnet(network, subnet_create_args)
    Internally calls: clients("neutron").create_subnet({"subnet": args})

    Args.network_id is required. Rally gets this from the network dict returned
    by _create_network: network["network"]["id"].
    """
    client = _neutron_client(wf)

    if not args.get('network_id'):
        raise Exception("network_id is required for neutron.create_subnet")

    args.setdefault("name", _generate_name("wf_subnet_"))
    args.setdefault("ip_version", 4)

    subnet = client.create_subnet({"subnet": args})

    wf.logger.info("Created subnet {} (ID: {})".format(
        subnet['subnet'].get('name', ''), subnet['subnet']['id']))

    return subnet['subnet']


def delete_subnet(wf, args, step):
    """Delete a subnet.

    Rally ref: NeutronScenario._delete_subnet(subnet)
    Internally calls: clients("neutron").delete_subnet(subnet_id)
    """
    client = _neutron_client(wf)
    subnet_id = args.get('subnet_id') or args.get('id')

    if not subnet_id:
        raise Exception("subnet_id is required for neutron.delete_subnet")

    wf.logger.info("Deleting subnet (ID: {})".format(subnet_id))
    client.delete_subnet(subnet_id)

    return {'id': subnet_id, 'deleted': True}


# ---------------------------------------------------------------------------
# Router operations
# Pattern: NeutronScenario._create_router / _add_interface_router
# ---------------------------------------------------------------------------

def create_router(wf, args, step):
    """Create a router following Rally NeutronScenario._create_router pattern.

    Rally ref: NeutronScenario._create_router(router_create_args)
    Internally calls: clients("neutron").create_router({"router": args})

    Note: Rally plugins often set external_gateway_info for SNAT:
        args["external_gateway_info"] = {"network_id": ext_net_id, "enable_snat": True}
    """
    client = _neutron_client(wf)
    args.setdefault("name", _generate_name("wf_router_"))

    router = client.create_router({"router": args})

    wf.logger.info("Created router {} (ID: {})".format(
        router['router']['name'], router['router']['id']))

    return router['router']


def delete_router(wf, args, step):
    """Delete a router.

    Rally ref: NeutronScenario._delete_router(router)
    Internally calls: clients("neutron").delete_router(router_id)
    """
    client = _neutron_client(wf)
    router_id = args.get('router_id') or args.get('id')

    if not router_id:
        raise Exception("router_id is required for neutron.delete_router")

    wf.logger.info("Deleting router (ID: {})".format(router_id))
    client.delete_router(router_id)

    return {'id': router_id, 'deleted': True}


def add_interface_router(wf, args, step):
    """Add subnet interface to router following Rally pattern.

    Rally ref: NeutronScenario._add_interface_router(subnet, router)
    Internally calls: clients("neutron").add_interface_router(
        router_id, {"subnet_id": subnet_id})
    """
    client = _neutron_client(wf)
    router_id = args.get('router_id')
    subnet_id = args.get('subnet_id')

    if not router_id or not subnet_id:
        raise Exception("router_id and subnet_id are required for neutron.add_interface_router")

    wf.logger.info("Adding subnet {} to router {}".format(subnet_id, router_id))
    client.add_interface_router(router_id, {"subnet_id": subnet_id})

    return {'router_id': router_id, 'subnet_id': subnet_id}


def remove_interface_router(wf, args, step):
    """Remove subnet interface from router following Rally pattern.

    Rally ref: NeutronScenario._remove_interface_router(subnet, router)
    Internally calls: clients("neutron").remove_interface_router(
        router_id, {"subnet_id": subnet_id})
    """
    client = _neutron_client(wf)
    router_id = args.get('router_id')
    subnet_id = args.get('subnet_id')

    if not router_id or not subnet_id:
        raise Exception(
            "router_id and subnet_id are required for neutron.remove_interface_router")

    wf.logger.info("Removing subnet {} from router {}".format(subnet_id, router_id))
    client.remove_interface_router(router_id, {"subnet_id": subnet_id})

    return {'router_id': router_id, 'subnet_id': subnet_id}


# ---------------------------------------------------------------------------
# Port operations
# Pattern: NeutronScenario._create_port
# ---------------------------------------------------------------------------

def create_port(wf, args, step):
    """Create a port following Rally NeutronScenario._create_port pattern.

    Rally ref: NeutronScenario._create_port(network, port_create_args)
    Internally calls: clients("neutron").create_port({"port": args})
    """
    client = _neutron_client(wf)

    if not args.get('network_id'):
        raise Exception("network_id is required for neutron.create_port")

    args.setdefault("name", _generate_name("wf_port_"))

    port = client.create_port({"port": args})

    wf.logger.info("Created port {} (ID: {})".format(
        port['port'].get('name', ''), port['port']['id']))

    return port['port']


def delete_port(wf, args, step):
    """Delete a port.

    Rally ref: NeutronScenario._delete_port(port)
    Internally calls: clients("neutron").delete_port(port_id)
    """
    client = _neutron_client(wf)
    port_id = args.get('port_id') or args.get('id')

    if not port_id:
        raise Exception("port_id is required for neutron.delete_port")

    wf.logger.info("Deleting port (ID: {})".format(port_id))
    client.delete_port(port_id)

    return {'id': port_id, 'deleted': True}


# ---------------------------------------------------------------------------
# Security group operations
# Pattern: NeutronScenario._create_security_group / _create_security_group_rule
# ---------------------------------------------------------------------------

def create_security_group(wf, args, step):
    """Create a security group following Rally NeutronScenario._create_security_group pattern.

    Rally ref: NeutronScenario._create_security_group(**security_group_args)
    Internally calls: clients("neutron").create_security_group(
        {"security_group": args})
    """
    client = _neutron_client(wf)
    args.setdefault("name", _generate_name("wf_sg_"))

    security_group = client.create_security_group({"security_group": args})

    wf.logger.info("Created security group {} (ID: {})".format(
        security_group['security_group']['name'],
        security_group['security_group']['id']))

    return security_group['security_group']


def delete_security_group(wf, args, step):
    """Delete a security group following Rally NeutronScenario._delete_security_group pattern.

    Rally ref: NeutronScenario._delete_security_group(security_group)
    Internally calls: clients("neutron").delete_security_group(sg_id)
    """
    client = _neutron_client(wf)
    sg_id = args.get('security_group_id') or args.get('id')

    if not sg_id:
        raise Exception("security_group_id is required for neutron.delete_security_group")

    wf.logger.info("Deleting security group (ID: {})".format(sg_id))
    client.delete_security_group(sg_id)

    return {'id': sg_id, 'deleted': True}


def create_security_group_rule(wf, args, step):
    """Create a security group rule following Rally pattern.

    Rally ref: NeutronScenario._create_security_group_rule(
        security_group_id, **security_group_rule_args)
    Internally calls: clients("neutron").create_security_group_rule(
        {"security_group_rule": args})

    Rally defaults direction to "ingress" and protocol to "tcp" if not specified.
    """
    client = _neutron_client(wf)

    if not args.get('security_group_id'):
        raise Exception("security_group_id is required for neutron.create_security_group_rule")

    # Rally defaults (from netcreate_nova_boot_fip_ping_sec_groups.py)
    args.setdefault("direction", "ingress")
    args.setdefault("protocol", "tcp")

    rule = client.create_security_group_rule({"security_group_rule": args})

    wf.logger.info("Created security group rule (ID: {}) for SG {}".format(
        rule['security_group_rule']['id'], args['security_group_id']))

    return rule['security_group_rule']


# ---------------------------------------------------------------------------
# Floating IP operations
# Pattern: NeutronScenario._create_floatingip / _list_floating_ips
# ---------------------------------------------------------------------------

def create_floatingip(wf, args, step):
    """Create a floating IP following Rally NeutronScenario._create_floatingip pattern.

    Rally ref: NeutronScenario._create_floatingip(floating_network)
    Internally calls: clients("neutron").create_floatingip(
        {"floatingip": {"floating_network_id": ext_net_id}})

    Accepts either floating_network_id directly, or floating_network_name
    which will be resolved to an ID.
    """
    client = _neutron_client(wf)

    # Rally resolves the external network name to ID
    if not args.get('floating_network_id') and args.get('floating_network_name'):
        net_name = args.pop('floating_network_name')
        networks = client.list_networks(name=net_name)['networks']
        if not networks:
            raise Exception("External network '{}' not found".format(net_name))
        args['floating_network_id'] = networks[0]['id']

    if not args.get('floating_network_id'):
        raise Exception(
            "floating_network_id or floating_network_name is required "
            "for neutron.create_floatingip")

    fip = client.create_floatingip({"floatingip": args})

    wf.logger.info("Created floating IP {} (ID: {})".format(
        fip['floatingip']['floating_ip_address'],
        fip['floatingip']['id']))

    return fip['floatingip']


def delete_floatingip(wf, args, step):
    """Delete a floating IP.

    Rally ref: NeutronScenario._delete_floating_ip(floating_ip)
    Internally calls: clients("neutron").delete_floatingip(fip_id)
    """
    client = _neutron_client(wf)
    fip_id = args.get('floatingip_id') or args.get('id')

    if not fip_id:
        raise Exception("floatingip_id is required for neutron.delete_floatingip")

    wf.logger.info("Deleting floating IP (ID: {})".format(fip_id))
    client.delete_floatingip(fip_id)

    return {'id': fip_id, 'deleted': True}


def list_floating_ips(wf, args, step):
    """List floating IPs following Rally NeutronScenario._list_floating_ips pattern.

    Rally ref: NeutronScenario._list_floating_ips(**kwargs)
    Internally calls: clients("neutron").list_floatingips(**kwargs)
    """
    client = _neutron_client(wf)
    fips = client.list_floatingips(**args)

    wf.logger.info("Listed {} floating IPs".format(len(fips.get('floatingips', []))))

    return fips['floatingips']
