#!/bin/bash
set -eu

pushd $WORKSPACE
 git clone https://github.com/openstack/tripleo-quickstart-extras
 pushd $WORKSPACE/tripleo-quickstart-extras
  git fetch git://git.openstack.org/openstack/tripleo-quickstart-extras refs/changes/77/403677/9 && git checkout FETCH_HEAD
 popd
popd

pushd $WORKSPACE/tripleo-quickstart
 sed -i.bak '/extras/d' $WORKSPACE/tripleo-quickstart/quickstart-extras-requirements.txt
 echo "file://$WORKSPACE/tripleo-quickstart-extras/#egg=tripleo-quickstart-extras" >> $WORKSPACE/tripleo-quickstart/quickstart-extras-requirements.txt
popd

export OPT_DEBUG_ANSIBLE=0
export HW_ENV_DIR=$WORKSPACE/tripleo-environments/hardware_environments/$HW_ENV
export NETWORK_ISOLATION=no_vlan
export REQS=quickstart-extras-requirements.txt
export PLAYBOOK=baremetal-virt-undercloud-tripleo-browbeat.yml
export VARS="elastic_enabled_template=true \
--extra-vars grafana_enabled_template=true \
--extra-vars elastic_host_template=$ELASTIC_HOST \
--extra-vars graphite_host_template=$GRAPH_HOST \
--extra-vars grafana_host_template=$GRAPH_HOST \
--extra-vars grafana_username_template=$GRAFANA_USER \
--extra-vars grafana_password_template=$GRAFANA_PASS \
--extra-vars browbeat_cloud_name=$CLOUD_NAME \
--extra-vars browbeat_config_file=$BENCHMARK \
--extra-vars graphite_prefix_template=$CLOUD_NAME"

#For Pipeline builds we need to get the pipeline image
#we check that the pipeline image var is set and then
#configure it to be used.
if [ ! -z ${current_build+x} ]
 then
  source $WORKSPACE/tripleo-environments/ci-scripts/internal-functions.sh
  hash=$(get_delorean_hash_from_url $current_build)
  cached_image="$INTERNAL_IMAGE_SERVER/$RELEASE/delorean/$hash/undercloud.qcow2"
  export VARS="$VARS --extra-vars undercloud_image_url=$cached_image --extra-vars dlrn_hash=$hash"

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
--config $HW_ENV_DIR/network_configs/no_vlan/config_files/config.yml \
--extra-vars @$HW_ENV_DIR/network_configs/$NETWORK_ISOLATION/env_settings.yml \
--extra-vars $VARS \
$VIRTHOST
