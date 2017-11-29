#!/bin/bash

if [[ $GERRIT_CHANGE_SUBJECT == "WIP "* ]] || [[ $GERRIT_CHANGE_SUBJECT == "wip "* ]]; then
  echo "Commit is a work in progress, short circuiting"
  exit 1
fi

if [[ $GERRIT_CHANGE_SUBJECT == "WIP: "* ]] || [[ $GERRIT_CHANGE_SUBJECT == "wip: "* ]]; then
  echo "Commit is a work in progress, short circuiting"
  exit 1
fi

set -eu
pushd $WORKSPACE/tripleo-quickstart
 sed -i.bak '/extras/d' $WORKSPACE/tripleo-quickstart/quickstart-extras-requirements.txt
 echo "file://$WORKSPACE/tripleo-quickstart-extras/#egg=tripleo-quickstart-extras" >> $WORKSPACE/tripleo-quickstart/quickstart-extras-requirements.txt
popd

export OPT_DEBUG_ANSIBLE=0
export HW_ENV_DIR=$WORKSPACE/tripleo-environments/hardware_environments/$HW_ENV
export NETWORK_ISOLATION=no_vlan
export REQS=quickstart-extras-requirements.txt
export VARS="elastic_enabled=true \
--extra-vars grafana_enabled=true \
--extra-vars elastic_host=$ELASTIC_HOST \
--extra-vars graphite_host=$GRAPH_HOST \
--extra-vars statsd_host=$GRAPH_HOST \
--extra-vars statsd_enabled=False \
--extra-vars grafana_host=$GRAPH_HOST \
--extra-vars grafana_username=$GRAFANA_USER \
--extra-vars grafana_password=$GRAFANA_PASS \
--extra-vars browbeat_cloud_name=$CLOUD_NAME \
--extra-vars browbeat_config_file=$BENCHMARK \
--extra-vars graphite_prefix=$CLOUD_NAME \
--extra-vars rsyslog_elasticsearch_server=$ELASTIC_HOST \
--extra-vars rsyslog_aggregator_server=$ELASTIC_HOST \
--extra-vars rsyslog_cloud_name=$CLOUD_NAME \
--extra-vars rsyslog_forwarding=true"

#For Pipeline builds we need to get the pipeline image
#we check that the pipeline image var is set and then
#configure it to be used.
if [ ! -z ${current_build+x} ]
 then
  source $WORKSPACE/tripleo-environments/ci-scripts/internal-functions.sh
  hash=$(get_delorean_hash_from_url $current_build)
  expanded_hash=$(get_expanded_delorean_hash_from_url $current_build)

  if [[ $RELEASE == *rhos-* ]]
   then
    export RELEASE="$RELEASE" #no mutations needed after latest changes
    export VARS="$VARS --extra-vars current_build=$current_build"
  else
    export RELEASE="$RELEASE-rhel"
    export VARS="$VARS --extra-vars current_build=$hash"
  fi

#If we are not in the pipeline downstream builds need to use current-passed-ci
elif [[ $RELEASE == *rhos-* ]]
 then
  export RELEASE="$RELEASE-current-passed-ci"
fi



#used to ensure concurrent jobs on the same executor work
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r


pushd $WORKSPACE/tripleo-quickstart

# Solves Ansible issue 13278
sed -i '/defaults/a timeout = 60' ansible.cfg


echo "file://$WORKSPACE/browbeat/#egg=browbeat" >> $REQS

./quickstart.sh \
--playbook $PLAYBOOK \
--working-dir $WORKSPACE \
--bootstrap \
--no-clone \
-t all \
-S overcloud-validate \
-R $RELEASE \
--config $HW_ENV_DIR/network_configs/$NETWORK_ISOLATION/config_files/config.yml \
--extra-vars @$HW_ENV_DIR/network_configs/$NETWORK_ISOLATION/env_settings.yml \
--extra-vars @$HW_ENV_DIR/all.yml \
--extra-vars $VARS \
$VIRTHOST
