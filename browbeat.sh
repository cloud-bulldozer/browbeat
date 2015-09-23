#!/bin/bash
source ~/stackrc
DEBUG=true
#WORKERS="metadata_workers|osapi_compute_workers|ec2_workers|public_workers|admin_workers|rpc_workers|api_workers"
CONTROLLERS=$(nova list | grep control)
SSH_OPTS="StrictHostKeyChecking no"
declare -A WORKERS
WORKERS["keystone"]="public_workers|admin_workers"
WORKERS["nova"]="metadata_workers|osapi_compute_workers|ec2_workers"
WORKERS["neutron"]="rpc_workers|api_workers"

#
# So this function pulls the current config from the hosts and just presents it -- doesn't store or use it... we could change this.
#

check_controllers()
{
 for IP in $(echo "$CONTROLLERS" | awk '{print $12}' | cut -d "=" -f 2); do
  # Number of cores?
  CORES=$(ssh -o "${SSH_OPTS}" heat-admin@$IP sudo cat /proc/cpuinfo | grep processor | wc -l)
  echo " ------------------- Controller : $IP -------------------"
  echo " -- Number of cores : $CORES --"
  echo " :::: Service : Keystone ::::"
  ssh -o "${SSH_OPTS}" heat-admin@$IP sudo cat /etc/keystone/keystone.conf | grep -vi "NONE" | grep -v "#" |grep -E ${WORKERS["keystone"]}
  echo " :::: Service : Nova ::::"
  ssh -o "${SSH_OPTS}" heat-admin@$IP sudo cat /etc/nova/nova.conf | grep -vi "NONE" | grep -v "#" |grep -E ${WORKERS["nova"]}
  echo " :::: Service : Neutron ::::"
  ssh -o "${SSH_OPTS}" heat-admin@$IP sudo cat /etc/neutron/neutron.conf | grep -vi "NONE" | grep -v "#" |grep -E ${WORKERS["neutron"]}
 done
}


#
#  This will update each of the functions - we pass which one to update.
#

update_workers()
{
 declare -A services
 services["keystone"]="/etc/keystone/keystone.conf"
 services["nova"]="/etc/nova/nova.conf"
 services["neutron"]="/etc/neutron/neutron.conf"

 if [ -z "$1" ] ; then
  echo "ERROR : Pass # of workers to use"
  exit 1
 else
  echo " Setting : $1 for number of workers"
  wkr_count=$1
 fi
 if [ -z "$2" ] ; then
  echo "ERROR : Pass which service to update"
  echo "Usage : update_workers COUNT SERVICE"
  echo "Valid services : keystone, nova, neutron"
  exit 1
 else
  echo "Updating : $2"
  osp_service=$2
 fi

 for IP in $(echo "$CONTROLLERS" | awk '{print $12}' | cut -d "=" -f 2); do
  #for i in $(echo $WORKERS | tr "|" "\n") ; do
  for i in $(echo ${WORKERS[$osp_service]} | tr "|" "\n") ; do
    echo "Copying Config files"
    ssh -o "${SSH_OPTS}" heat-admin@$IP sudo cp ${services[$osp_service]} ${services[$osp_service]}-copy
    #ssh -o "${SSH_OPTS}" heat-admin@$IP sudo sed -i -e 's/$i.*/${i}=${wkr_count}/g' ${services[$worker]}
    ssh -o "${SSH_OPTS}" heat-admin@$IP sudo "sed -i -e \"s/^\(${i}\)\( \)*=\( \)*\([0-9]\)*/${i}=${wkr_count}/g\" ${services[$osp_service]}"
  done
 done
 if [ "${osp_service}" == "keystone" ]; then
  IP=`echo "$CONTROLLERS" | head -n 1 | awk '{print $12}' | cut -d "=" -f 2`
  ssh -o "${SSH_OPTS}" heat-admin@$IP sudo "pcs resource restart openstack-keystone"
 fi

}


run_rally()
{
 if [ -z "$1" ] ; then
  echo "ERROR : Pass which service to run rally tests against"
  echo "Usage : run_rally SERVICE TEST_PREFIX"
  echo "Valid services : keystone, nova, neutron"
  exit 1
 else
  echo "Benchmarking : $1"
  osp_service=$1
 fi
 if [ -z "$2" ] ; then
  echo "ERROR : Pass test_prefix to run rally tests"
  echo "Usage : run_rally SERVICE TEST_PREFIX"
  echo "Valid services : keystone, nova, neutron"
  exit 1
 else
  test_prefix=$2
 fi

 for task_file in `ls ${osp_service}`
 do
  if [ ${task_file: -3} == "-cc" ]
  then
   #for concur in 32 64 128 256 384
   for concur in 128 256 384
   do
    times=5000
    task_dir=$osp_service
    test_name="${test_prefix}-${task_file}-${concur}"
    echo "${test_name}"
    sed -i "s/\"concurrency\": 1,/\"concurrency\": ${concur},/g" ${task_dir}/${task_file}
    sed -i "s/\"times\": 1,/\"times\": ${times},/g" ${task_dir}/${task_file}

    rally task start --task ${task_dir}/${task_file} 2>&1 | tee ${test_name}.log

    # grep the log file for the results to be run
    test_id=`grep "rally task results" ${test_name}.log | awk '{print $4}'`
    rally task report ${test_id} --out ${test_name}.html
    mv ${test_name}.log results/
    mv ${test_name}.html results/

    sed -i "s/\"concurrency\": ${concur},/\"concurrency\": 1,/g" ${task_dir}/${task_file}
    sed -i "s/\"times\": ${times},/\"times\": 1,/g" ${task_dir}/${task_file}
   done
  fi
 done
}

if $DEBUG ; then
  echo "$CONTROLLERS"
fi

#
# 1) Show the current # of workers
# 2) Run Tests (Keystone, Nova, Neutron)
# 3) Update # of workers per-service
# 4) Re-Run tests above
#

mkdir -p results
check_controllers
for num_wkrs in `seq 24 -2 2`; do
#for num_wkrs in 12; do
  num_wkr_padded="$(printf "%02d" ${num_wkrs})"
  # Update number of workers
  update_workers ${num_wkrs} keystone
  # Show number of workers
  check_controllers
  # Run Rally $SERVICE test
  run_rally keystone "test001-${num_wkr_padded}"
done
update_workers 24 keystone
check_controllers
