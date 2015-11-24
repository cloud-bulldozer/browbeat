#!/bin/bash
if [ ! $# == 2 ]; then
  echo "Usage: ./gen_hostfiles.sh <ospd_ip_address> <ssh_config_file>"
  echo "Generates ssh config file to use OSP director host as a jumpbox and creates ansible inventory file."
  exit
fi
ospd_ip_address=$1
ansible_inventory_file='hosts'
ssh_config_file=$2

nodes=$(ssh -t -o "StrictHostKeyChecking no" stack@${ospd_ip_address} ". ~/stackrc; nova list | grep overcloud")

echo ""
echo "---------------------------"
echo "Creating ssh config file:"
echo "---------------------------"
echo ""

echo "# Generate by gen_hostfile.sh from browbeat" | tee ${ssh_config_file}
echo "" | tee -a ${ssh_config_file}
echo "Host undercloud-stack" | tee -a ${ssh_config_file}
echo "    Hostname ${ospd_ip_address}" | tee -a ${ssh_config_file}
echo "    User stack" | tee -a ${ssh_config_file}
echo "    IdentityFile ~/.ssh/id_rsa" | tee -a ${ssh_config_file}
echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}
echo "" | tee -a ${ssh_config_file}
echo "Host undercloud-root" | tee -a ${ssh_config_file}
echo "    Hostname ${ospd_ip_address}" | tee -a ${ssh_config_file}
echo "    User root" | tee -a ${ssh_config_file}
echo "    IdentityFile ~/.ssh/id_rsa" | tee -a ${ssh_config_file}
echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}

compute=()
controllers=()
ceph=()
IFS=$'\n'
for line in $nodes; do
 host=$(echo $line| awk '{print $4}')
 IP=$(echo $line | awk '{print $12}' | cut -d "=" -f2)
 if [[ ${host} =~ compute ]]; then
  compute+="$IP "
 fi
 if [[ ${host} =~ ceph ]] ; then
  ceph+="$IP "
 fi
 if [[ ${host} =~ control ]]; then
  controllers+="$IP "
 fi
 echo "" | tee -a ${ssh_config_file}
 echo "Host ${host}" | tee -a ${ssh_config_file}
 echo "    ProxyCommand ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=60 -i ~/.ssh/id_rsa stack@${ospd_ip_address} -W ${IP}:22" | tee -a ${ssh_config_file}
 echo "    User heat-admin" | tee -a ${ssh_config_file}
 echo "    IdentityFile ~/.ssh/heat-admin-id_rsa" | tee -a ${ssh_config_file}
 echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
 echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}
done


echo ""
echo "---------------------------"
echo "Creating ansible inventory file:"
echo "---------------------------"
echo ""
echo "[director]" | tee ${ansible_inventory_file}
echo "${ospd_ip_address}" | tee -a ${ansible_inventory_file}
if [[ ${#controllers} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[controllers]" | tee -a ${ansible_inventory_file}
 for ct in ${controllers[@]}; do
  echo "${ct}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#compute} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[computes]" | tee -a ${ansible_inventory_file}
 for c in ${compute[@]}; do
  echo "${c}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#ceph} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[ceph]" | tee -a ${ansible_inventory_file}
 for ceph in ${ceph[@]}; do
  echo "${ceph}" | tee -a ${ansible_inventory_file}
 done
fi
echo "---------------------------"

# Copy heat-admin key so we can use jumpbox
echo ""
echo "---------------------------"
echo "Copying heat-admin key to local machine(~/.ssh/heat-admin-id_rsa) to for use with ssh config file"
echo "---------------------------"
echo ""
scp undercloud-root:/home/stack/.ssh/id_rsa ~/.ssh/heat-admin-id_rsa
