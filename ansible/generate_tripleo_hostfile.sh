#!/bin/bash
# If things break, take out the hammer and remove the hash below:
#set -x

function usage
{
    echo "Usage: generate_tripleo_hostfile.sh"
    echo "          [-t | --tripleo_ip_address <tripleo_ip_address> [-l | --localhost]]"
    echo "          [-o | --overcloud_stack_name <overcloud_stack_name>]"
    echo "          [-u | --user <user>]"
    echo "          [-c | --ceph_stack_name <ceph_stack_name>]"
    echo "          [-h | --help]"
    echo "Generates ssh config file to use with an TripleO undercloud host as a jumpbox and creates ansible inventory file."
}

user="stack"
uncomment_localhost=false
tripleo_ip_address=
overcloud_name="overcloud"
ceph_stack_name=$overcloud_name
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
    -o | --overcloud_stack_name )
                            shift
                            overcloud_name=$1
                            ;;
    -c | --ceph_stack_name )
                            shift
                            ceph_stack_name=$1
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
 cat "${HOME}/.ssh/id_rsa.pub" >> "${HOME}/.ssh/authorized_keys"
 chmod 0600 "${HOME}/.ssh/authorized_keys"
 sudo bash -c "cat ${HOME}/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys"
 sudo bash -c "chmod 0600 /root/.ssh/authorized_keys"
fi

# Check if there are any clouds built.
clouds=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack list | grep -i -E '$overcloud_name'")
if [ ${#clouds} -gt 0 ]; then
	  nodes=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack server list 2>/dev/null | grep -i -E 'active|running'")
  if [ ${#nodes} -lt 1 ]; then
    echo "ERROR: nova list failed to execute properly, please check the openstack-nova-api on the undercloud."
    exit 1
  fi
  ironic_uuids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack baremetal node list > >(grep -i -E 'active|running') 2>/dev/null")
  controller_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show $overcloud_name Controller -c physical_resource_id -f value" | tr '\r' ' ')
  if [ ${#controller_id} -lt 3 ]; then
     echo "Error: Controller ID is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi
  controller_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${controller_id} -c resource_name -f value" | tr '\r' ' ')
  if [ ${#controller_ids} -lt 1 ]; then
     echo "Error: Controller IDs is not reporting correctly. Please see check the openstack-heat-api on the undercloud."
     exit 1
  fi

  networker_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show $overcloud_name Networker -c physical_resource_id -f value" | tr '\r' ' ')
  if [ ${#networker_id} -lt 3 ]; then
    echo "Info: No Networker resources."
  else
    networker_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${networker_id} -c resource_name -f value" | tr '\r' ' ')
    if [ ${#networker_ids} -lt 1 ]; then
      echo "Info: No Networker resources."
    fi
  fi

  blockstorage_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show $overcloud_name BlockStorage -c physical_resource_id -f value" | tr '\r' ' ')
  if [ ${#blockstorage_id} -lt 3 ]; then
    echo "Info: No BlockStorage resources."
  else
    #blockstorage_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${blockstorage_id} > >(grep -i blockstorage) 2>/dev/null" | awk '{print $2}')
    blockstorage_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${blockstorage_id} -c resource_name -f value" | tr '\r' ' ')
    if [ ${#blockstorage_ids} -lt 1 ]; then
       echo "Info: No BlockStorage resources."
     fi
  fi

  objectstorage_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show $overcloud_name ObjectStorage -c physical_resource_id -f value" | tr '\r' ' ')
  if [ ${#objectstorage_id} -lt 3 ]; then
    echo "Info: No ObjectStorage resources."
  else
     objectstorage_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${objectstorage_id} -c resource_name -f value" | tr '\r' ' ')
     if [ ${#objectstorage_ids} -lt 1 ]; then
       echo "Info: No ObjectStorage resources."
     fi
  fi

  cephstorage_id=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show $ceph_stack_name CephStorage -c physical_resource_id -f value" | tr '\r' ' ')
  if [ ${#cephstorage_id} -lt 3 ]; then
    echo "Info: No CephStorage resources."
  else
     cephstorage_ids=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${cephstorage_id} -c resource_name -f value" | tr '\r' ' ')
     if [ ${#cephstorage_ids} -lt 1 ]; then
       echo "Info: No CephStorage resources."
    fi
  fi

  compute_resources=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list $overcloud_name" | awk '{print $2}' | egrep -i 'Compute$|hci$')
  for resource in $compute_resources; do compute_resources_arr+=($(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show $overcloud_name $resource | grep physical_resource_id")); done
  compute_resource_ids=$(for id in ${compute_resources_arr[@]}; do echo $id | grep -v '|' | grep -v physical_resource_id; done)
  if [ ${#compute_resource_ids} -lt 3 ]; then
     echo "Info: No compute resources"
  else
     for compute_id in $compute_resource_ids; do
       compute_ids+=($(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource list ${compute_id} > >(grep -i compute) 2>/dev/null" | awk '{print $2}'))
     done
     compute_ids=$(for id in ${compute_ids[@]}; do echo $id; done)
     if [ ${#compute_ids} -lt 1 ]; then
       echo "Info: No compute resources"
    fi
  fi

  controller_uuids=()
  for controller in ${controller_ids}
  do
    controller_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show -c attributes -f json ${controller_id} ${controller} | jq .attributes.nova_server_resource")
  done

  networker_uuids=()
  for networker in ${networker_ids}
  do
    networker_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show -c attributes -f json ${networker_id} ${networker} | jq .attributes.nova_server_resource")
  done

  blockstorage_uuids=()
  for blockstorage in ${blockstorage_ids}
  do
    blockstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show -c attributes -f json ${blockstorage_id} ${blockstorage} | jq .attributes.nova_server_resource")
  done

  objectstorage_uuids=()
  for objectstorage in ${objectstorage_ids}
  do
    objectstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show -c attributes -f json ${objectstorage_id} ${objectstorage} | jq .attributes.nova_server_resource")
  done

  cephstorage_uuids=()
  for cephstorage in ${cephstorage_ids}
  do
    cephstorage_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show -c attributes -f json ${cephstorage_id} ${cephstorage} | jq .attributes.nova_server_resource")
  done

  compute_uuids=()
  for compute in ${compute_ids}
  do
     for compute_id in $compute_resource_ids; do
       compute_uuids+=$(ssh -tt -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" ${user}@${tripleo_ip_address} ". ~/stackrc; openstack stack resource show -c attributes -f json ${compute_id} ${compute} | jq .attributes.nova_server_resource")
     done
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

blockstorage_hn=()
cephstorage_hn=()
compute_hn=()
controller_hn=()
networker_hn=()
objectstorage_hn=()
IFS=$'\n'
for line in $nodes; do
 uuid=$(echo $line | awk '{print $2}')
 host=$(echo $line | awk '{print $4}')
 IP=$(echo $line | awk '{print $8}' | cut -d "=" -f2)
 if grep -q $uuid <<< {$controller_uuids}; then
  controller_hn+=("$host")
elif grep -q $uuid <<< {$networker_uuids}; then
  networker_hn+=("$host")
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
 echo "    ProxyCommand ssh -F ${ssh_config_file} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=60 -i ~/.ssh/id_rsa ${user}@${tripleo_ip_address} -W ${IP}:22" | tee -a ${ssh_config_file}
 echo "    User heat-admin" | tee -a ${ssh_config_file}
 echo "    IdentityFile ${DIR}/heat-admin-id_rsa" | tee -a ${ssh_config_file}
 echo "    StrictHostKeyChecking no" | tee -a ${ssh_config_file}
 echo "    UserKnownHostsFile=/dev/null" | tee -a ${ssh_config_file}
 # Substitute the nova instance id for the host name so we can attach the ironic uuid as a host var
 ironic_uuids=${ironic_uuids/$uuid/$host}
done

# Sort Host Types
controller_hn=( $(
    for item in "${controller_hn[@]}"
    do
        echo "$item"
    done | sort) )
networker_hn=( $(
    for item in "${networker_hn[@]}"
    do
        echo "$item"
    done | sort) )
blockstorage_hn=( $(
    for item in "${blockstorage_hn[@]}"
    do
        echo "$item"
    done | sort) )
objectstorage_hn=( $(
    for item in "${objectstorage_hn[@]}"
    do
        echo "$item"
    done | sort) )
cephstorage_hn=( $(
    for item in "${cephstorage_hn[@]}"
    do
        echo "$item"
    done | sort) )
compute_hn=( $(
    for item in "${compute_hn[@]}"
    do
        echo "$item"
    done | sort) )

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
  echo "undercloud ansible_user=${user}" | tee -a ${ansible_inventory_file}
fi
echo ""  | tee -a ${ansible_inventory_file}
echo "[undercloud]" | tee -a ${ansible_inventory_file}
echo "undercloud ansible_user=${user}" | tee -a ${ansible_inventory_file}
echo "" | tee -a ${ansible_inventory_file}
echo "[controller]" | tee -a ${ansible_inventory_file}
if [[ ${#controller_hn} -gt 0 ]]; then
 for ct in ${controller_hn[@]}; do
   ironic_uuid=''
   for line in ${ironic_uuids}; do
     uuid=$(echo $line | awk '{print $2}')
     host=$(echo $line | awk '{print $6}')
     if [ "$host" == "$ct" ]; then
       ironic_uuid=$uuid
       break
     fi
   done
  echo "${ct} ironic_uuid=${ironic_uuid}" | tee -a ${ansible_inventory_file}
 done
fi
echo "" | tee -a ${ansible_inventory_file}
echo "[networker]" | tee -a ${ansible_inventory_file}
if [[ ${#networker_hn} -gt 0 ]]; then
 for networker in ${networker_hn[@]}; do
  ironic_uuid=''
  for line in ${ironic_uuids}; do
   uuid=$(echo $line | awk '{print $2}')
   host=$(echo $line | awk '{print $6}')
   if [ "$host" == "$networker" ]; then
    ironic_uuid=$uuid
    break
   fi
  done
  echo "${networker} ironic_uuid=${ironic_uuid}" | tee -a ${ansible_inventory_file}
 done
fi
echo "" | tee -a ${ansible_inventory_file}
echo "[blockstorage]" | tee -a ${ansible_inventory_file}
if [[ ${#blockstorage_hn} -gt 0 ]]; then
 for blockstorage in ${blockstorage_hn[@]}; do
  ironic_uuid=''
  for line in ${ironic_uuids}; do
   uuid=$(echo $line | awk '{print $2}')
   host=$(echo $line | awk '{print $6}')
   if [ "$host" == "$blockstorage" ]; then
    ironic_uuid=$uuid
    break
   fi
  done
  echo "${blockstorage} ironic_uuid=${ironic_uuid}" | tee -a ${ansible_inventory_file}
 done
fi
echo "" | tee -a ${ansible_inventory_file}
echo "[objectstorage]" | tee -a ${ansible_inventory_file}
if [[ ${#objectstorage_hn} -gt 0 ]]; then
 for objectstorage in ${objectstorage_hn[@]}; do
  ironic_uuid=''
  for line in ${ironic_uuids}; do
   uuid=$(echo $line | awk '{print $2}')
   host=$(echo $line | awk '{print $6}')
   if [ "$host" == "$objectstorage" ]; then
    ironic_uuid=$uuid
    break
   fi
  done
  echo "${objectstorage} ironic_uuid=${ironic_uuid}" | tee -a ${ansible_inventory_file}
 done
fi
echo "" | tee -a ${ansible_inventory_file}
echo "[cephstorage]" | tee -a ${ansible_inventory_file}
if [[ ${#cephstorage_hn} -gt 0 ]]; then
 for cephstorage in ${cephstorage_hn[@]}; do
  ironic_uuid=''
  for line in ${ironic_uuids}; do
   uuid=$(echo $line | awk '{print $2}')
   host=$(echo $line | awk '{print $6}')
   if [ "$host" == "$cephstorage" ]; then
    ironic_uuid=$uuid
    break
   fi
  done
  echo "${cephstorage} ironic_uuid=${ironic_uuid}" | tee -a ${ansible_inventory_file}
 done
fi
echo "" | tee -a ${ansible_inventory_file}
echo "[compute]" | tee -a ${ansible_inventory_file}
if [[ ${#compute_hn} -gt 0 ]]; then
 for compute in ${compute_hn[@]}; do
   ironic_uuid=''
   for line in ${ironic_uuids}; do
     uuid=$(echo $line | awk '{print $2}')
     host=$(echo $line | awk '{print $6}')
     if [ "$host" == "$compute" ]; then
       ironic_uuid=$uuid
       break
     fi
   done
  echo "${compute} ironic_uuid=${ironic_uuid}" | tee -a ${ansible_inventory_file}
 done
fi
if [[ ${#controller_hn} -gt 0 ]] || [[ ${#blockstorage_hn} -gt 0 ]] || [[ ${#objectstorage_hn} -gt 0 ]] || [[ ${#cephstorage_hn} -gt 0 ]] || [[ ${#compute_hn} -gt 0 ]]; then
 echo "" | tee -a ${ansible_inventory_file}
 echo "[overcloud:children]" | tee -a ${ansible_inventory_file}
 if [[ ${#controller_hn} -gt 0 ]]; then
  echo "controller" | tee -a ${ansible_inventory_file}
 fi
 if [[ ${#networker_hn} -gt 0 ]]; then
  echo "networker" | tee -a ${ansible_inventory_file}
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
 echo "" | tee -a ${ansible_inventory_file}
 echo "[overcloud:vars]" | tee -a ${ansible_inventory_file}
 echo "ansible_user=heat-admin" | tee -a ${ansible_inventory_file}
fi
echo "" | tee -a ${ansible_inventory_file}
echo "[other]" | tee -a ${ansible_inventory_file}
if [[ ${#other_hn} -gt 0 ]]; then
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
echo "[elk-client]" | tee -a ${ansible_inventory_file}
echo "## example host entry." | tee -a ${ansible_inventory_file}
echo "#host-02" | tee -a ${ansible_inventory_file}
echo "" | tee -a ${ansible_inventory_file}
echo "[stockpile]" | tee -a ${ansible_inventory_file}
echo "undercloud ansible_user=${user}" | tee -a ${ansible_inventory_file}

echo "---------------------------"
echo "IMPORTANT: If you plan on deploying ELK clients, update hosts and make sure"
echo "           the [elk-client] hosts entries are updated with valid hosts."
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
scp -o "UserKnownHostsFile /dev/null" -o "StrictHostKeyChecking no" "${user}@${tripleo_ip_address}":/home/${user}/.ssh/id_rsa heat-admin-id_rsa
