#!/bin/bash

export OPT_DEBUG_ANSIBLE=1
export USER=root
export HW_ENV_DIR=$WORKSPACE/tripleo-environments/hardware_environments/$HW_ENV
export NETWORK_ISOLATION=no_vlan
export REQS=quickstart-extras-requirements.txt
export PLAYBOOK=baremetal-virt-undercloud-tripleo-browbeat.yml
export RELEASE=$RELEASE
export VARS="elastic_enabled_template=true \
--extra-vars graphite_enabled_template=true \
--extra-vars elastic_host_template=$ELASTIC_HOST \
--extra-vars graphite_host_template=$GRAPH_HOST \
--extra-vars grafana_host_template=$GRAPH_HOST \
--extra-vars grafana_username_template=$GRAFANA_USER \
--extra-vars grafana_password_template=$GRAFANA_PASS \
--extra-vars browbeat_cloud_name=$CLOUD_NAME \
--extra-vars browbeat_config_file=$BENCHMARK \
--extra-vars graphite_prefix_template=$CLOUD_NAME \
--extra-vars dlrn_hash=$current_build"

#For Pipeline builds we need to get the pipeline image
#we check that the pipeline image var is set and then
#configure it to be used.
if [ -z "$current_build" ]
 then
  export VARS='$VARS --extra-vars undercloud_image_url=$current_build'
fi


#used to ensure concurrent jobs on the same executor work
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r


pushd $WORKSPACE/tripleo-quickstart


echo "file://$WORKSPACE/browbeat/#egg=browbeat" >> $REQS

./quickstart.sh \
--requirements $REQS \
--playbook $PLAYBOOK \
--working-dir $WORKSPACE \
--bootstrap \
--no-clone \
-t all \
-S overcloud-validate \
-R $RELEASE \
--config $HW_ENV_DIR/network_configs/no_vlan/config_files/config.yml \
--extra-vars @$HW_ENV_DIR/network_configs/$NETWORK_ISOLATION/env_settings.yml \
--extra-vars $VARS \
$VIRTHOST
