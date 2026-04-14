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
import time


def _generate_name(prefix="wf_nova_"):
    """Generate a random name following Rally's naming convention."""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return "{}{}".format(prefix, suffix)


def _nova_client(wf):
    """Get the nova client from workflow's os_clients.

    This returns the same novaclient that Rally's NovaScenario uses
    internally via self.clients("nova").
    """
    return wf.os_clients.nova()


def _neutron_client(wf):
    """Get the neutron client for floating IP operations.

    Rally's VMScenario uses self.clients("neutron") for floating IP
    attach/detach operations.
    """
    return wf.os_clients.neutron()


def _server_to_dict(server):
    """Convert a nova Server object to a dict, matching Rally's return patterns."""
    return {
        'id': server.id,
        'name': server.name,
        'status': server.status,
        'addresses': server.addresses,
        'tenant_id': getattr(server, 'tenant_id', None),
        'metadata': getattr(server, 'metadata', {}),
    }


def _wait_for_server_status(wf, nova, server_id, status, timeout=300, poll_interval=5):
    """Wait for server to reach a given status.

    Rally ref: rally.common.utils.wait_for_status()
    Rally's _boot_server internally waits for ACTIVE status.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        server = nova.servers.get(server_id)
        if server.status == status:
            wf.logger.info("Server {} reached status {}".format(server_id, status))
            return server
        elif server.status == 'ERROR':
            fault = getattr(server, 'fault', {})
            raise Exception("Server {} entered ERROR state: {}".format(
                server_id, fault.get('message', 'unknown error')))
        time.sleep(poll_interval)

    raise Exception("Timeout waiting for server {} to reach status {} "
                    "(current: {})".format(server_id, status, server.status))


def get_handlers(workflow_instance):
    """Return nova operation handlers.

    All handlers use the same nova/neutron client and patterns as Rally's
    NovaScenario and VMScenario
    (rally_openstack.task.scenarios.nova.utils,
     rally_openstack.task.scenarios.vm.utils).

    Args:
        workflow_instance: Workflow instance providing os_clients and logger

    Returns:
        dict: Mapping of operation type strings to handler callables
    """
    return {
        'nova.boot_server': lambda args, step: boot_server(workflow_instance, args, step),
        'nova.boot_server_with_fip': lambda args, step: boot_server_with_fip(
            workflow_instance, args, step),
        'nova.delete_server': lambda args, step: delete_server(workflow_instance, args, step),
        'nova.show_server': lambda args, step: show_server(workflow_instance, args, step),
        'nova.list_servers': lambda args, step: list_servers(workflow_instance, args, step),
        'nova.stop_server': lambda args, step: stop_server(workflow_instance, args, step),
        'nova.start_server': lambda args, step: start_server(workflow_instance, args, step),
        'nova.attach_floating_ip': lambda args, step: attach_floating_ip(
            workflow_instance, args, step),
        'nova.attach_interface': lambda args, step: attach_interface(
            workflow_instance, args, step),
        'nova.attach_volume': lambda args, step: attach_volume(
            workflow_instance, args, step),
        'nova.detach_volume': lambda args, step: detach_volume(
            workflow_instance, args, step),
        'nova.list_hypervisors': lambda args, step: list_hypervisors(
            workflow_instance, args, step),
        'nova.list_flavors': lambda args, step: list_flavors(
            workflow_instance, args, step),
        # Keep legacy alias
        'nova.create_server': lambda args, step: boot_server(workflow_instance, args, step),
        'nova.get_server': lambda args, step: show_server(workflow_instance, args, step),
    }


# ---------------------------------------------------------------------------
# Server lifecycle operations
# Pattern: NovaScenario._boot_server / VMScenario._boot_server_with_fip
# ---------------------------------------------------------------------------

def boot_server(wf, args, step):
    """Boot a server following Rally NovaScenario._boot_server pattern.

    Rally ref: NovaScenario._boot_server(image, flavor, auto_assign_nic=False, **kwargs)
    Internally calls: clients("nova").servers.create(...)
    Rally waits for ACTIVE status by default.

    Required args: image, flavor
    Optional args: name, nics, security_groups, key_name, availability_zone,
                   userdata, and any other nova boot kwargs.
    Step-level options: wait_for_status (default "ACTIVE"), wait_timeout (default 300)
    """
    nova = _nova_client(wf)
    args.setdefault("name", _generate_name("wf_server_"))

    # Resolve image/flavor names to UUIDs (Rally does this via type converters)
    if 'image' in args:
        args['image'] = _resolve_image(wf, args['image'])
    if 'flavor' in args:
        args['flavor'] = _resolve_flavor(wf, args['flavor'])

    server = nova.servers.create(**args)
    wf.logger.info("Created server {} (ID: {})".format(server.name, server.id))

    # Rally's _boot_server always waits for ACTIVE
    wait_for_status = step.get('wait_for_status', 'ACTIVE')
    wait_timeout = step.get('wait_timeout', 300)

    if wait_for_status:
        server = _wait_for_server_status(
            wf, nova, server.id, wait_for_status, timeout=wait_timeout)

    return _server_to_dict(server)


def boot_server_with_fip(wf, args, step):
    """Boot a server and attach a floating IP following Rally VMScenario pattern.

    Rally ref: VMScenario._boot_server_with_fip(
        image, flavor, use_floating_ip=True, floating_network=None, **kwargs)
    Internally: boots server, then creates floating IP and associates it.
    Returns (server_dict, fip_dict).

    Required args: image, flavor, floating_network (external network name or ID)
    Optional args: same as boot_server
    """
    nova = _nova_client(wf)
    neutron = _neutron_client(wf)

    floating_network = args.pop('floating_network', None)
    if not floating_network:
        raise Exception("floating_network is required for nova.boot_server_with_fip")

    args.setdefault("name", _generate_name("wf_server_"))

    # Resolve image/flavor names to UUIDs (Rally does this via type converters)
    if 'image' in args:
        args['image'] = _resolve_image(wf, args['image'])
    if 'flavor' in args:
        args['flavor'] = _resolve_flavor(wf, args['flavor'])

    # Boot the server (Rally pattern)
    server = nova.servers.create(**args)
    wf.logger.info("Created server {} (ID: {})".format(server.name, server.id))

    wait_timeout = step.get('wait_timeout', 300)
    server = _wait_for_server_status(wf, nova, server.id, 'ACTIVE', timeout=wait_timeout)

    # Resolve floating network ID if name was given (Rally pattern)
    floating_network_id = floating_network
    try:
        neutron.show_network(floating_network)
    except Exception:
        networks = neutron.list_networks(name=floating_network)['networks']
        if not networks:
            raise Exception("External network '{}' not found".format(floating_network))
        floating_network_id = networks[0]['id']

    # Create and associate floating IP (Rally VMScenario pattern)
    fip = neutron.create_floatingip({"floatingip": {
        "floating_network_id": floating_network_id,
        "port_id": _get_server_port_id(neutron, server.id)
    }})['floatingip']

    wf.logger.info("Attached floating IP {} to server {}".format(
        fip['floating_ip_address'], server.id))

    server = nova.servers.get(server.id)

    return {
        'server': _server_to_dict(server),
        'fip': {
            'id': fip['id'],
            'ip': fip['floating_ip_address'],
        }
    }


def delete_server(wf, args, step):
    """Delete a server following Rally NovaScenario._delete_server pattern.

    Rally ref: NovaScenario._delete_server(server, force=False)
    Internally calls: clients("nova").servers.delete(server)
    Optionally force-deletes and waits for DELETED status.
    """
    nova = _nova_client(wf)
    server_id = args.get('server_id') or args.get('id')
    force = args.get('force', False)

    if not server_id:
        raise Exception("server_id is required for nova.delete_server")

    server = nova.servers.get(server_id)
    wf.logger.info("Deleting server {} (ID: {})".format(server.name, server.id))

    if force:
        server.force_delete()
    else:
        nova.servers.delete(server)

    # Optionally wait for deletion to complete
    wait_for_delete = step.get('wait_for_delete', False)
    wait_timeout = step.get('wait_timeout', 300)
    if wait_for_delete:
        start_time = time.time()
        while time.time() - start_time < wait_timeout:
            try:
                nova.servers.get(server_id)
                time.sleep(5)
            except Exception:
                wf.logger.info("Server {} deleted".format(server_id))
                break
        else:
            raise Exception("Timeout waiting for server {} to be deleted".format(server_id))

    return {'id': server_id, 'deleted': True}


# ---------------------------------------------------------------------------
# Server query operations
# Pattern: NovaScenario._show_server / _list_servers
# ---------------------------------------------------------------------------

def show_server(wf, args, step):
    """Get server details following Rally NovaScenario._show_server pattern.

    Rally ref: NovaScenario._show_server(server)
    Internally calls: clients("nova").servers.get(server_id)
    """
    nova = _nova_client(wf)
    server_id = args.get('server_id') or args.get('id')

    if not server_id:
        raise Exception("server_id is required for nova.show_server")

    server = nova.servers.get(server_id)

    return _server_to_dict(server)


def list_servers(wf, args, step):
    """List servers following Rally NovaScenario._list_servers pattern.

    Rally ref: NovaScenario._list_servers(detailed=True)
    Internally calls: clients("nova").servers.list(detailed=detailed)
    """
    nova = _nova_client(wf)
    detailed = args.get('detailed', True)

    servers = nova.servers.list(detailed=detailed)

    wf.logger.info("Listed {} servers".format(len(servers)))

    return [_server_to_dict(s) for s in servers]


# ---------------------------------------------------------------------------
# Server state operations
# Pattern: NovaScenario._stop_server / _start_server
# ---------------------------------------------------------------------------

def stop_server(wf, args, step):
    """Stop a server following Rally NovaScenario._stop_server pattern.

    Rally ref: NovaScenario._stop_server(server)
    Internally calls: server.stop() then waits for SHUTOFF status.
    """
    nova = _nova_client(wf)
    server_id = args.get('server_id') or args.get('id')

    if not server_id:
        raise Exception("server_id is required for nova.stop_server")

    server = nova.servers.get(server_id)
    wf.logger.info("Stopping server {} (ID: {})".format(server.name, server.id))
    server.stop()

    wait_timeout = step.get('wait_timeout', 300)
    server = _wait_for_server_status(wf, nova, server.id, 'SHUTOFF', timeout=wait_timeout)

    return _server_to_dict(server)


def start_server(wf, args, step):
    """Start a server following Rally NovaScenario._start_server pattern.

    Rally ref: NovaScenario._start_server(server)
    Internally calls: server.start() then waits for ACTIVE status.
    """
    nova = _nova_client(wf)
    server_id = args.get('server_id') or args.get('id')

    if not server_id:
        raise Exception("server_id is required for nova.start_server")

    server = nova.servers.get(server_id)
    wf.logger.info("Starting server {} (ID: {})".format(server.name, server.id))
    server.start()

    wait_timeout = step.get('wait_timeout', 300)
    server = _wait_for_server_status(wf, nova, server.id, 'ACTIVE', timeout=wait_timeout)

    return _server_to_dict(server)


# ---------------------------------------------------------------------------
# Network/interface operations
# Pattern: VMScenario._attach_floating_ip / NovaScenario._attach_interface
# ---------------------------------------------------------------------------

def attach_floating_ip(wf, args, step):
    """Attach a floating IP to a server following Rally VMScenario pattern.

    Rally ref: VMScenario._attach_floating_ip(server, floating_network)
    Internally: creates floating IP via neutron and associates to server port.
    """
    neutron = _neutron_client(wf)

    server_id = args.get('server_id') or args.get('id')
    floating_network = args.get('floating_network')

    if not server_id:
        raise Exception("server_id is required for nova.attach_floating_ip")
    if not floating_network:
        raise Exception("floating_network is required for nova.attach_floating_ip")

    # Resolve floating network name to ID if needed
    floating_network_id = floating_network
    try:
        neutron.show_network(floating_network)
    except Exception:
        networks = neutron.list_networks(name=floating_network)['networks']
        if not networks:
            raise Exception("External network '{}' not found".format(floating_network))
        floating_network_id = networks[0]['id']

    port_id = _get_server_port_id(neutron, server_id)

    fip = neutron.create_floatingip({"floatingip": {
        "floating_network_id": floating_network_id,
        "port_id": port_id
    }})['floatingip']

    wf.logger.info("Attached floating IP {} to server {}".format(
        fip['floating_ip_address'], server_id))

    return {
        'id': fip['id'],
        'ip': fip['floating_ip_address'],
        'server_id': server_id
    }


def attach_interface(wf, args, step):
    """Attach a network interface to a server following Rally pattern.

    Rally ref: NovaScenario._attach_interface(server, net_id)
    Internally calls: server.interface_attach(port_id, net_id, fixed_ip)
    """
    nova = _nova_client(wf)
    server_id = args.get('server_id') or args.get('id')
    net_id = args.get('net_id') or args.get('network_id')

    if not server_id:
        raise Exception("server_id is required for nova.attach_interface")

    server = nova.servers.get(server_id)

    port_id = args.get('port_id')
    fixed_ip = args.get('fixed_ip')

    interface = server.interface_attach(port_id, net_id, fixed_ip)

    wf.logger.info("Attached interface to server {} (port: {})".format(
        server_id, interface.port_id))

    return {
        'port_id': interface.port_id,
        'net_id': interface.net_id,
        'server_id': server_id
    }


# ---------------------------------------------------------------------------
# Volume operations
# Pattern: NovaScenario._attach_volume / _detach_volume
# ---------------------------------------------------------------------------

def attach_volume(wf, args, step):
    """Attach a volume to a server following Rally NovaScenario._attach_volume pattern.

    Rally ref: NovaScenario._attach_volume(server, volume)
    Internally calls: clients("nova").volumes.create_server_volume(server_id, volume_id)
    """
    nova = _nova_client(wf)
    server_id = args.get('server_id')
    volume_id = args.get('volume_id')

    if not server_id or not volume_id:
        raise Exception("server_id and volume_id are required for nova.attach_volume")

    wf.logger.info("Attaching volume {} to server {}".format(volume_id, server_id))
    nova.volumes.create_server_volume(server_id, volume_id)

    return {'server_id': server_id, 'volume_id': volume_id}


def detach_volume(wf, args, step):
    """Detach a volume from a server following Rally NovaScenario._detach_volume pattern.

    Rally ref: NovaScenario._detach_volume(server, volume)
    Internally calls: clients("nova").volumes.delete_server_volume(server_id, volume_id)
    """
    nova = _nova_client(wf)
    server_id = args.get('server_id')
    volume_id = args.get('volume_id')

    if not server_id or not volume_id:
        raise Exception("server_id and volume_id are required for nova.detach_volume")

    wf.logger.info("Detaching volume {} from server {}".format(volume_id, server_id))
    nova.volumes.delete_server_volume(server_id, volume_id)

    return {'server_id': server_id, 'volume_id': volume_id}


# ---------------------------------------------------------------------------
# Infrastructure query operations
# Pattern: NovaScenario._list_hypervisors / _list_flavors
# ---------------------------------------------------------------------------

def list_hypervisors(wf, args, step):
    """List hypervisors following Rally NovaScenario._list_hypervisors pattern.

    Rally ref: NovaScenario._list_hypervisors()
    Internally calls: clients("nova").hypervisors.list()
    """
    nova = _nova_client(wf)
    hypervisors = nova.hypervisors.list()

    wf.logger.info("Listed {} hypervisors".format(len(hypervisors)))

    return [{'id': h.id, 'hypervisor_hostname': h.hypervisor_hostname,
             'state': h.state, 'status': h.status} for h in hypervisors]


def list_flavors(wf, args, step):
    """List flavors following Rally NovaScenario._list_flavors pattern.

    Rally ref: NovaScenario._list_flavors()
    Internally calls: clients("nova").flavors.list()
    """
    nova = _nova_client(wf)
    flavors = nova.flavors.list()

    wf.logger.info("Listed {} flavors".format(len(flavors)))

    return [{'id': f.id, 'name': f.name, 'ram': f.ram,
             'vcpus': f.vcpus, 'disk': f.disk} for f in flavors]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_server_port_id(neutron, server_id):
    """Get the first port ID for a server (used for floating IP association).

    Rally's VMScenario uses this pattern internally when associating
    floating IPs to servers.
    """
    ports = neutron.list_ports(device_id=server_id)['ports']
    if not ports:
        raise Exception("No ports found for server {}".format(server_id))
    return ports[0]['id']


def _resolve_image(wf, image_ref):
    """Resolve image name to UUID if needed.

    Rally does this via the glance_image type converter. Nova API requires
    the image UUID, not the name.
    """
    # Already a UUID
    if _is_uuid(image_ref):
        return image_ref

    glance = wf.os_clients.glance()
    images = list(glance.images.list(filters={'name': image_ref}))
    if not images:
        raise Exception("Image '{}' not found".format(image_ref))
    return images[0]['id']


def _resolve_flavor(wf, flavor_ref):
    """Resolve flavor name to UUID if needed.

    Rally does this via the nova_flavor type converter. Nova API accepts
    both name and UUID for flavor, but UUID is more reliable.
    """
    if _is_uuid(flavor_ref):
        return flavor_ref

    nova = _nova_client(wf)
    for flavor in nova.flavors.list():
        if flavor.name == flavor_ref:
            return flavor.id
    raise Exception("Flavor '{}' not found".format(flavor_ref))


def _is_uuid(value):
    """Check if a string looks like a UUID."""
    import re
    return bool(re.match(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        str(value).lower()))
