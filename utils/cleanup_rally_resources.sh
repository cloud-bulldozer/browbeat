#!/bin/bash
set +e

source ~/overcloudrc
for i in `openstack server list --all -c ID -f value`; do openstack server delete $i; done
for i in `openstack floating ip list  -c ID -f value`; do openstack floating ip delete $i; done
for i in `openstack router list -c ID -f value`; do openstack router unset --external-gateway $i; done
for router in `openstack router list -c ID -f value`; do
 subnet=`openstack router show $router -c interfaces_info -f json | jq -r '.interfaces_info[0].subnet_id'`
 openstack router remove subnet $router $subnet
done
for i in `openstack router list  -c ID -f value`; do openstack router delete $i; done
for i in `openstack network list  -c ID -f value`; do openstack network delete $i; done
