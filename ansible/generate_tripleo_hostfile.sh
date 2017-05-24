#!/bin/bash
function usage
{
    echo "Usage: generate_tripleo_hostfile.sh [-t <tripleo_ip_address> [-l | --localhost]] | [-h | --help]"
    echo "Generates ssh config file to use with an TripleO undercloud host as a jumpbox and creates ansible inventory file."
}

uncomment_localhost=false
tripleo_ip_address=
while [ "$1" != "" ]; do
  case $1 in
    -l | --localhost )      uncomment_localhost=true
                            ;;
    -t | --tripleo_ip_address )
                            shift
                            tripleo_ip_address=$1
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

ansible_inventory_file='hosts'
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ssh_config_file=${DIR}'/ssh-config'

# "Hackish" copy ssh key to self if we are on directly on the undercloud machine:
if [[ "${tripleo_ip_address}" == "localhost" ]]; then
 cat ~stack/.ssh/id_rsa.pub >> ~stack/.ssh/authorized_keys
 chmod 0600 ~stack/.ssh/authorized_keys
 sudo bash -c "cat ~stack/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys"
 sudo bash -c "chmod 0600 /root/.ssh/authorized_keys"
fi

# Check if there are any clouds built.
clouds=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack list | grep -i -E 'overcloud'")
if [ ${#clouds} -gt 0 ]; then
  nodes=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack server list | grep -i -E 'active|running'")
  if [ ${#nodes} -lt 1 ]; then
    echo "ERROR: nova list failed to execute properly, please check the openstack-nova-api on the undercloud."
    exit 1
  fi
  controller_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show overcloud Controller > >(grep physical_resource_id) 2>/dev/null" | awk '{print $4}')
  if [ ${#controller_id} -lt 1 ]; then
     echo "Error: Controller ID is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi
  blockstorage_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show overcloud BlockStorage > >(grep physical_resource_id) 2>/dev/null" | awk '{print $4}')
  if [ ${#blockstorage_id} -lt 1 ]; then
     echo "Error: BlockStorage ID is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi
  objectstorage_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show overcloud ObjectStorage > >(grep physical_resource_id) 2>/dev/null" | awk '{print $4}')
  if [ ${#objectstorage_id} -lt 1 ]; then
     echo "Error: ObjectStorage ID is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi
  cephstorage_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show overcloud CephStorage > >(grep physical_resource_id) 2>/dev/null" | awk '{print $4}')
  if [ ${#cephstorage_id} -lt 1 ]; then
     echo "Error: CephStorage ID is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi
  compute_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show overcloud Compute > >(grep physical_resource_id) 2>/dev/null" | awk '{print $4}')
  if [ ${#compute_id} -lt 1 ]; then
     echo "Error: Compute ID is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi

  controller_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${controller_id} > >(grep -i controller) 2>/dev/null" | awk '{print $2}')
  if [ ${#controller_ids} -lt 1 ]; then
     echo "Error: Controller IDs is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi
  blockstorage_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${blockstorage_id} > >(grep -i blockstorage) 2>/dev/null" | awk '{print $2}')
  if [ ${#blockstorage_ids} -lt 1 ]; then
     echo "Info: No BlockStorage resources."
  fi
  objectstorage_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${objectstorage_id} > >(grep -i objectstorage) 2>/dev/null" | awk '{print $2}')
  if [ ${#objectstorage_ids} -lt 1 ]; then
     echo "Info: No ObjectStorage resources."
  fi
  cephstorage_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${cephstorage_id} > >(grep -i cephstorage) 2>/dev/null" | awk '{print $2}')
  if [ ${#cephstorage_ids} -lt 1 ]; then
     echo "Info: No CephStorage resources."
  fi
  compute_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${compute_id} > >(grep -i compute) 2>/dev/null" | awk '{print $2}')
  if [ ${#compute_ids} -lt 1 ]; then
     echo "Error: Compute IDs is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi

  version_tripleo=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} "rpm -qa | egrep 'openstack-tripleo-heat-templates-[[:digit:]]'" | awk -F- '{print $5}' | awk -F. '{print $1}')
  controller_uuids=()
  for controller in ${controller_ids}
  do
   if [[ ${version_tripleo} -lt 2 ]] ; then
     controller_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; heat resource-show ${controller_id} ${controller} | grep -i nova_server_resource" | awk '{print $4}')
   else
     controller_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show ${controller_id} ${controller} > >(grep -oP \"'nova_server_resource': u'([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)'\") 2>/dev/null" | awk '{print $2}' | grep -oP [a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)
   fi
  done
  blockstorage_uuids=()
  for blockstorage in ${blockstorage_ids}
  do
   if [[ ${version_tripleo} -lt 2 ]] ; then
     blockstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; heat resource-show ${blockstorage_id} ${blockstorage} | grep -i nova_server_resource" | awk '{print $4}')
   else
     blockstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show ${blockstorage_id} ${blockstorage} > >(grep -oP \"'nova_server_resource': u'([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)'\") 2>/dev/null" | awk '{print $2}' | grep -oP [a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)
   fi
  done
  objectstorage_uuids=()
  for objectstorage in ${objectstorage_ids}
  do
   if [[ ${version_tripleo} -lt 2 ]] ; then
     objectstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; heat resource-show ${objectstorage_id} ${objectstorage} | grep -i nova_server_resource" | awk '{print $4}')
   else
     objectstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show ${objectstorage_id} ${objectstorage} > >(grep -oP \"'nova_server_resource': u'([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)'\") 2>/dev/null" | awk '{print $2}' | grep -oP [a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)
   fi
  done
  cephstorage_uuids=()
  for cephstorage in ${cephstorage_ids}
  do
   if [[ ${version_tripleo} -lt 2 ]] ; then
     cephstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; heat resource-show ${cephstorage_id} ${cephstorage} | grep -i nova_server_resource" | awk '{print $4}')
   else
     cephstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show ${cephstorage_id} ${cephstorage} > >(grep -oP \"'nova_server_resource': u'([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)'\") 2>/dev/null" | awk '{print $2}' | grep -oP [a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)
   fi
  done
  compute_uuids=()
  for compute in ${compute_ids}
  do
   if [[ ${version_tripleo} -lt 2 ]] ; then
     compute_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; heat resource-show ${compute_id} ${compute} | grep -i nova_server_resource" | awk '{print $4}')
 else
     compute_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" stack@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show ${compute_id} ${compute} > >(grep -oP \"'nova_server_resource': u'([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)'\") 2>/dev/null" | awk '{print $2}' | grep -oP [a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)
   fi
  done
fi

echo ""
echo "---------------------------"
echo "Creating ssh config file:"
echo "---------------------------"
echo ""

echo "# Generated by generate_tripleo_hostfile.sh from browbeat" | tee ${ssh_config_file}
echo "" | tee -a ${ssh_config_file}
echo "Host undercloud" | tee -a ${ssh_config_file}
echo "    Hostname ${tripleo_ip_address}" | tee -a ${ssh_config_file}
echo "    IdentityFile ~/.ssh/id_rsa" | tee -a ${ssh_config_file}
echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}
echo "" | tee -a ${ssh_config_file}
echo "Host undercloud-root" | tee -a ${ssh_config_file}
echo "    Hostname ${tripleo_ip_address}" | tee -a ${ssh_config_file}
echo "    User root" | tee -a ${ssh_config_file}
echo "    IdentityFile ~/.ssh/id_rsa" | tee -a ${ssh_config_file}
echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}
echo "" | tee -a ${ssh_config_file}
echo "Host undercloud-stack" | tee -a ${ssh_config_file}
echo "    Hostname ${tripleo_ip_address}" | tee -a ${ssh_config_file}
echo "    User stack" | tee -a ${ssh_config_file}
echo "    IdentityFile ~/.ssh/id_rsa" | tee -a ${ssh_config_file}
echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}

compute_hn=()
controller_hn=()
blockstorage_hn=()
objectstorage_hn=()
cephstorage_hn=()
IFS=$'\n'
for line in $nodes; do
 uuid=$(echo $line | awk '{print $2}')
 host=$(echo $line | awk '{print $4}')
 IP=$(echo $line | awk '{print $8}' | cut -d "=" -f2)
 if grep -q $uuid <<< {$controller_uuids}; then
  controller_hn+=("$host")
elif grep -q $uuid <<< {$blockstorage_uuids}; then
  blockstorage_hn+=("$host")
 elif grep -q $uuid <<< {$objectstorage_uuids}; then
  objectstorage_hn+=("$host")
 elif grep -q $uuid <<< {$cephstorage_uuids}; then
  cephstorage_hn+=("$host")
 elif grep -q $uuid <<< {$compute_uuids}; then
  compute_hn+=("$host")
 else
  other_hn+=("$host")
 fi
 echo "" | tee -a ${ssh_config_file}
 echo "Host ${host}" | tee -a ${ssh_config_file}
 echo "    ProxyCommand ssh -F ${ssh_config_file} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=60 -i ~/.ssh/id_rsa stack@${tripleo_ip_address} -W ${IP}:22" | tee -a ${ssh_config_file}
 echo "    User heat-admin" | tee -a ${ssh_config_file}
 echo "    IdentityFile ${DIR}/heat-admin-id_rsa" | tee -a ${ssh_config_file}
 echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
 echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}
done

echo ""
echo "---------------------------"
echo "Creating ansible inventory file:"
echo "---------------------------"
echo ""
echo "[browbeat]" | tee ${ansible_inventory_file}
echo "# Pick host depending on desired install" | tee -a ${ansible_inventory_file}
if [ "${uncomment_localhost}" = true ]; then
  echo "localhost" | tee -a ${ansible_inventory_file}
  echo "#undercloud" | tee -a ${ansible_inventory_file}
else
  echo "#localhost" | tee -a ${ansible_inventory_file}
  echo "undercloud" | tee -a ${ansible_inventory_file}
fi
echo ""  | tee -a ${ansible_inventory_file}
echo "[undercloud]" | tee -a ${ansible_inventory_file}
echo "undercloud" | tee -a ${ansible_inventory_file}
if [[ ${#controller_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[controller]" | tee -a ${ansible_inventory_file}
 for ct in ${controller_hn[@]}; do
  echo "${ct}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#blockstorage_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[blockstorage]" | tee -a ${ansible_inventory_file}
 for blockstorage in ${blockstorage_hn[@]}; do
  echo "${blockstorage}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#objectstorage_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[objectstorage]" | tee -a ${ansible_inventory_file}
 for objectstorage in ${objectstorage_hn[@]}; do
  echo "${objectstorage}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#cephstorage_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[cephstorage]" | tee -a ${ansible_inventory_file}
 for cephstorage in ${cephstorage_hn[@]}; do
  echo "${cephstorage}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#compute_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[compute]" | tee -a ${ansible_inventory_file}
 for c in ${compute_hn[@]}; do
  echo "${c}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#controller_hn} -gt 0 ]] || [[ ${#blockstorage_hn} -gt 0 ]] || [[ ${#objectstorage_hn} -gt 0 ]] || [[ ${#cephstorage_hn} -gt 0 ]] || [[ ${#compute_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[overcloud:children]" | tee -a ${ansible_inventory_file}
 if [[ ${#controller_hn} -gt 0 ]]; then
  echo "controller" | tee -a ${ansible_inventory_file}
 fi
 if [[ ${#blockstorage_hn} -gt 0 ]]; then
  echo "blockstorage" | tee -a ${ansible_inventory_file}
 fi
 if [[ ${#objectstorage_hn} -gt 0 ]]; then
  echo "objectstorage" | tee -a ${ansible_inventory_file}
 fi
 if [[ ${#cephstorage_hn} -gt 0 ]]; then
  echo "cephstorage" | tee -a ${ansible_inventory_file}
 fi
 if [[ ${#compute_hn} -gt 0 ]]; then
  echo "compute" | tee -a ${ansible_inventory_file}
 fi
fi
if [[ ${#other_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[other]" | tee -a ${ansible_inventory_file}
 for other in ${other_hn[@]}; do
  echo "${other}" | tee -a ${ansible_inventory_file}
 done
fi
echo "" | tee -a ${ansible_inventory_file}
echo "[graphite]" | tee -a ${ansible_inventory_file}
echo "## example host entry." | tee -a ${ansible_inventory_file}
echo "#host-01" | tee -a ${ansible_inventory_file}
echo "" | tee -a ${ansible_inventory_file}
echo "[grafana]" | tee -a ${ansible_inventory_file}
echo "## example host entry." | tee -a ${ansible_inventory_file}
echo "#host-02" | tee -a ${ansible_inventory_file}

echo "---------------------------"
echo "IMPORTANT: If you plan on deploying graphite and grafana, update hosts and make sure"
echo "           the [graphite] and [grafana] hosts entries are updated with valid hosts."
echo "           You will need to have passwordless access to root on these hosts."
echo "---------------------------"
echo "" | tee -a ${ansible_inventory_file}
echo "[elk]" | tee -a ${ansible_inventory_file}
echo "## example host entry." | tee -a ${ansible_inventory_file}
echo "#host-01" | tee -a ${ansible_inventory_file}
echo "" | tee -a ${ansible_inventory_file}
echo "[elk-client]" | tee -a ${ansible_inventory_file}
echo "## example host entry." | tee -a ${ansible_inventory_file}
echo "#host-02" | tee -a ${ansible_inventory_file}

echo "---------------------------"
echo "IMPORTANT: If you plan on deploying ELK and ELK clients, update hosts and make sure"
echo "           the [elk] and [elk-client] hosts entries are updated with valid hosts."
echo "           You will need to have passwordless access to root on these hosts."
echo "---------------------------"

# Before referencing a host in ~/.ssh/config, ensure correct permissions on ssh config file
chmod 0600 ${ssh_config_file}

# Copy heat-admin key so we can use jumpbox
echo ""
echo "---------------------------"
echo "Copying heat-admin key to local machine(~/.ssh/heat-admin-id_rsa) to for use with ssh config file"
echo "---------------------------"
echo ""
scp -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" "stack@${tripleo_ip_address}":/home/stack/.ssh/id_rsa heat-admin-id_rsa
