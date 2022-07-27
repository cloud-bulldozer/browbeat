#!/bin/bash

function usage
{
    echo "usage: generate_tripleo_hostfile.sh"
    echo "          [-t | --tripleo_ip_address <tripleo_ip_address> [-l | --localhost]]"
    echo "          [-o | --overcloud_stack_name <overcloud_stack_name>]"
    echo "          [-u | --user <user>]"
    echo "          [-c | --ceph_stack_name <ceph_stack_name>]"
    echo "          [-h | --help]"
    echo "Generates ssh config file to use with an TripleO undercloud host as a jumpbox and creates ansible inventory file."
}

user="stack"
overcloud_stack_name=overcloud
uncomment_localhost=false
tripleo_ip_address=

while [ "$1" != "" ]; do
  case $1 in
    -l | --localhost )      uncomment_localhost=true
                            tripleo_ip_address="localhost"
                            ;;
    -t | --tripleo_ip_address )
                            shift
                            tripleo_ip_address=$1
                            ;;
    -u | --user )
                            shift
                            user=$1
                            ;;
    -h | --help )           usage
                            exit
                            ;;
    * )                     usage
                            exit 1
  esac
  shift
done
if [ -z "$tripleo_ip_address" ]; then
  usage
  exit 1
fi

out_file="hosts.yml"
version=$(grep -o 17 /etc/rhosp-release)

if [ "$version" = "17" ]; then
  cp ~/overcloud-deploy/overcloud/tripleo-ansible-inventory.yaml ${out_file}
elif ([ $uncomment_localhost ] && [ "$version" != "17" ]); then
  source ~/stackrc
  tripleo-ansible-inventory --stack ${overcloud_stack_name} --static-yaml-inventory ${out_file}
else
  file_path=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; tripleo-ansible-inventory --stack ${overcloud_stack_name} --static-yaml-inventory ${out_file}; pwd ${out_file}")
  scp -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address}:${file_path}/${out_file} .
fi

sed -i '1iBrowbeat:\n  hosts:\n    undercloud: {}' ${out_file}
sed -i '$aStockpile:\n  hosts:\n    undercloud: {}' ${out_file}

# Copy heat-admin key so we can use jumpbox
echo ""
echo "---------------------------"
echo "Copying heat-admin key to local machine for use with ssh config file"
echo "---------------------------"
echo ""
scp -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" "${user}@${tripleo_ip_address}":/home/${user}/.ssh/id_rsa heat-admin-id_rsa
