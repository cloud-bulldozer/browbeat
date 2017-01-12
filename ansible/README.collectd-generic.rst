Installing and configuring collectd agent on other machines
===========================================================

Collectd configurations are built for these types of machines:
  * baremetal
  * guest
  * graphite/grafana

To install collectd agent and configure collectd to send metrics to your
Graphite server, simply add the host to your ansible inventory file
under the correct group.

Complete Example Inventory file:

::

    [undercloud]
    undercloud

    [controller]
    overcloud-controller-0
    overcloud-controller-1
    overcloud-controller-2

    [compute]
    overcloud-compute-0
    overcloud-compute-1

    [cephstorage]
    overcloud-cephstorage-0

    [objectstorage]
    overcloud-objectstorage-0

    [baremetal]
    x.x.x.x # An ip adddress or fqdn or specificed host in ~/.ssh/config

    [guest]
    x.x.x.x # An ip adddress or fqdn or specificed vm in ~/.ssh/config

    [graphite]
    x.x.x.x # An ip address of a Graphite/Grafana Server


Example running the collectd-generic playbook on the above specified
baremetal machine:

::

    # ansible-playbook -i hosts install/collectd-generic.yml --tags "baremetal"

Replace "baremetal" with whatever machines you intend to install collectd on.

Note: Openstack host groups (undercloud, controller, compute, cephstorage,
objectstorage) are ignored with the collectd-generic.yml playbook.
