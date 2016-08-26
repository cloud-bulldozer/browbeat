#!/bin/bash

export OPT_DEBUG_ANSIBLE=1
export USER=root
export REQUIREMENTS=quickstart-extras-requirements.txt
export PLAYBOOK=browbeat-quickstart.yml
export RELEASE=$RELEASE
export VARS=""
#export VARS="elastic_enabled_template=true \
#--extra-vars graphite_enabled_template=true \
#--extra-vars elastic_host_template=$ELASTIC_HOST \
#--extra-vars graphite_host_template=$GRAPH_HOST \
#--extra-vars grafana_host_template=$GRAPH_HOST \
#--extra-vars grafana_username_template=$GRAFANA_USER \
#--extra-vars grafana_password_template=$GRAFANA_PASS \
#--extra-vars browbeat_cloud_name=$CLOUD_NAME \
#--extra-vars browbeat_config_file=$BENCHMARK \
#--extra-vars graphite_prefix_template=$CLOUD_NAME \
#--extra-vars dlrn_hash=$current_build"

socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r
export REQS=quickstart-extras-requirements.txt


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
--extra-vars $VARS \
$VIRTHOST
