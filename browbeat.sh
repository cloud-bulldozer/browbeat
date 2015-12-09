#!/bin/bash
source ~/stackrc
source browbeat-config

log()
{
    echo "[$(date)]: $*"
}

check_controllers()
{
 for IP in $(echo "$CONTROLLERS" | awk '{print $12}' | cut -d "=" -f 2); do
  # Number of cores?
  CORES=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo cat /proc/cpuinfo | grep processor | wc -l)
  log Controller : $IP
  log Number of cores : $CORES
  log Service : Keystone
  if [[ "${KEYSTONE_IN_APACHE}" == true ]]; then
   log "\_Admin:" $(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo cat /etc/httpd/conf.d/10-keystone_wsgi_admin.conf | grep -vi "NONE" | grep -v "#" | grep -E ${WORKERS["keystone"]})
   log "\_Main:" $(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo cat /etc/httpd/conf.d/10-keystone_wsgi_main.conf | grep -vi "NONE" | grep -v "#" | grep -E ${WORKERS["keystone"]})
  else
   log $(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo cat /etc/keystone/keystone.conf | grep -vi "NONE" | grep -v "#" |grep -E ${WORKERS["keystone"]})
  fi
  log Service : Nova
  log $(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo cat /etc/nova/nova.conf | grep -vi "NONE" | grep -v "#" |grep -E ${WORKERS["nova"]})
  log Service : Neutron
  log $(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo cat /etc/neutron/neutron.conf | grep -vi "NONE" | grep -v "#" |grep -E ${WORKERS["neutron"]})
 done
}

check_running_workers()
{
 for IP in $(echo "$CONTROLLERS" | awk '{print $12}' | cut -d "=" -f 2); do
  log Validate number of workers
  keystone_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Kk]eystone" | wc -l)
  keystone_admin_httpd_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Kk]eystone-admin" | wc -l)
  keystone_main_httpd_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Kk]eystone-main" | wc -l)
  nova_api_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Nn]ova-api" | wc -l)
  nova_conductor_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Nn]ova-conductor" | wc -l)
  nova_scheduler_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Nn]ova-scheduler" | wc -l)
  nova_consoleauth_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Nn]ova-consoleauth" | wc -l)
  nova_novncproxy_num=$(ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo ps afx | grep "[Nn]ova-novncproxy" | wc -l)
  log $IP : keystone : $keystone_num workers admin/main combined
  log $IP : "keystone(httpd)"  : $keystone_admin_httpd_num admin workers, $keystone_main_httpd_num main workers
  log $IP : nova-api : $nova_api_num workers
  log $IP : nova-conductor : $nova_conductor_num workers
  log $IP : nova-scheduler : $nova_scheduler_num workers
  log $IP : nova-consoleauth : $nova_consoleauth_num workers
  log $IP : nova-novncproxy : $nova_novncproxy_num workers

  # Keystone should be 2x for admin and main + 1 for main process
  # Nova should be 3x + 1 nova-api, core_count + 1 for conductor, and scheduler+consoleauth+novncproxy
  # Neutron ?
 done
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

 for task_file in `ls rally/${osp_service}`
 do
  task_dir=rally/$osp_service

  if [ ${task_file: -3} == "-cc" ]
  then

   for concur in ${CONCURRENCY[${osp_service}]}
   do

    for ((run_count=1; run_count<=${RERUN}; run_count++))
    do

     times=${TIMES[${osp_service}]}
     concur_padded="$(printf "%04d" ${concur})"
     test_name="${test_prefix}-iteration_$run_count-${task_file}-${concur_padded}"
     log Test-Name ${test_name}
     sed -i "s/\"concurrency\": 1,/\"concurrency\": ${concur},/g" ${task_dir}/${task_file}
     sed -i "s/\"times\": 1,/\"times\": ${times},/g" ${task_dir}/${task_file}
     truncate_token_bloat

     results_dir=results/${test_prefix}/$osp_service/${task_file}/run-$run_count
     mkdir -p $results_dir

     if $CONNMON ; then
         log Starting connmon
         sed -i "s/csv_dump:.*/csv_dump: results\/$test_prefix\/$osp_service\/$task_file\/run-$run_count\/current-run.csv/g" /etc/connmon.cfg
         connmond --config /etc/connmon.cfg > /tmp/connmond-${test_name} 2>&1 &
         CONNMON_PID=$!
     fi

     if $PBENCH ; then
      setup_pbench
      user-benchmark --config=${test_name} -- "./browbeat-run-rally.sh ${task_dir}/${task_file} ${test_name}"
     else
      # pbench is off, just run rally directly
      rally task start --task ${task_dir}/${task_file} 2>&1 | tee ${test_name}.log
     fi

     if $CONNMON ; then
      log Stopping connmon
      kill -9 $CONNMON_PID
      mv ${results_dir}/current-run.csv ${results_dir}/${test_name}.csv
     fi

     # grep the log file for the results to be run
     test_id=`grep "rally task results" ${test_name}.log | awk '{print $4}'`
     rally task report ${test_id} --out ${test_name}.html
     if $PBENCH ; then
      pbench_results_dir=`find /var/lib/pbench-agent/ -name "*${test_prefix}*" -print`
      log "Copying rally report and log into ${pbench_results_dir}"
      cp ${test_name}.log ${pbench_results_dir}
      cp ${test_name}.html ${pbench_results_dir}
      move-results --prefix=${test_prefix}/${task_file}-${concur}
      clear-tools
     fi
     mv ${test_name}.log $results_dir
     mv ${test_name}.html $results_dir

     post_process $results_dir

     sed -i "s/\"concurrency\": ${concur},/\"concurrency\": 1,/g" ${task_dir}/${task_file}
     sed -i "s/\"times\": ${times},/\"times\": 1,/g" ${task_dir}/${task_file}
    done  # RERUN
   done  # Concurrency
  fi
 done  # Task Files
}

post_process()
{
 if [ -z "$1" ] ; then
  echo "Error result path not passed"
  exit 1
 else
  log Post-Processing : $1
  results=$1
 fi

 if $CONNMON ; then
  log Building Connmon Graphs
  for i in `ls -talrh $results | grep -E "*\.csv$" | awk '{print $9}'` ; do
    python graphing/connmonplot.py $results/$i;
  done
 fi
}

setup_pbench()
{
 log "Setting up pbench tools"
 clear-tools
 kill-tools
 sudo /opt/pbench-agent/util-scripts/register-tool --name=mpstat -- --interval=${PBENCH_INTERVAL}
 sudo /opt/pbench-agent/util-scripts/register-tool --name=iostat -- --interval=${PBENCH_INTERVAL}
 sudo /opt/pbench-agent/util-scripts/register-tool --name=sar -- --interval=${PBENCH_INTERVAL}
 sudo /opt/pbench-agent/util-scripts/register-tool --name=vmstat -- --interval=${PBENCH_INTERVAL}
 sudo /opt/pbench-agent/util-scripts/register-tool --name=pidstat -- --interval=${PBENCH_INTERVAL}
 for IP in $(echo "$CONTROLLERS" | awk '{print $12}' | cut -d "=" -f 2); do
  sudo /opt/pbench-agent/util-scripts/register-tool --name=mpstat --remote=${IP} -- --interval=${PBENCH_INTERVAL}
  sudo /opt/pbench-agent/util-scripts/register-tool --name=iostat --remote=${IP} -- --interval=${PBENCH_INTERVAL}
  sudo /opt/pbench-agent/util-scripts/register-tool --name=sar --remote=${IP} -- --interval=${PBENCH_INTERVAL}
  sudo /opt/pbench-agent/util-scripts/register-tool --name=vmstat --remote=${IP} -- --interval=${PBENCH_INTERVAL}
  sudo /opt/pbench-agent/util-scripts/register-tool --name=pidstat --remote=${IP} -- --interval=${PBENCH_INTERVAL}
  sudo /opt/pbench-agent/util-scripts/register-tool --name=user-tool --remote=${IP} -- --tool-name=mariadb-conntrack --start-script=/opt/usertool/mariadb-track.sh
 done
}

truncate_token_bloat()
{
 log "Truncating Token Bloat"
 IP=`echo "$CONTROLLERS" | head -n 1 | awk '{print $12}' | cut -d "=" -f 2`
 ssh -o "${SSH_OPTS}" ${LOGIN_USER}@$IP sudo "mysql keystone -e 'truncate token;'"
}


if [ ! $# == 1 ]; then
  log "Usage: ./browbeat.sh <test_prefix>"
  exit
fi

if [ ! -f ansible/hosts ]; then
  log "ERROR: Ansible inventory file does not exist."
  log "In ansible directory, run: ./gen_hosts.sh <ospd ip address> ~/.ssh/config"
  exit
fi

complete_test_prefix=$1

if $DEBUG ; then
  log $CONTROLLERS
fi

#
# 1) Show the current # of workers
# 2) Run Tests (Keystone, Nova, Neutron)
# 3) Update # of workers per-service
# 4) Re-Run tests above
#

mkdir -p results
check_controllers

# Clean logs before run
ansible-playbook -i ansible/hosts ansible/browbeat/cleanlogs.yml

for num_wkrs in ${NUM_WORKERS} ; do
  num_wkr_padded="$(printf "%02d" ${num_wkrs})"

  ansible-playbook -i ansible/hosts ansible/browbeat/adjustment.yml -e "workers=${num_wkrs}"
  check_running_workers

#  check_controllers
#  run_rally keystone "${complete_test_prefix}-keystone-${num_wkr_padded}" ${num_wkrs}

  check_controllers
  run_rally nova "${complete_test_prefix}-nova-${num_wkr_padded}" ${num_wkrs}

done
ansible-playbook -i ansible/hosts ansible/browbeat/adjustment.yml -e "workers=${RESET_WORKERS}"
check_running_workers
check_controllers
