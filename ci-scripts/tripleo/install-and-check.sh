#!/bin/bash
# CI test based on Triple O's full deploy CI test, will deploy
# a Triple O instance, install Browbeat and then perform various checks
# Usage:
#  export VIRTHOST=<virthost>
#  export WORKSPACE=<workspace>
#  install-and-test.sh <release> <build_system> <config> <job_type>
#
# The workspace should be a blank folder with the browbeat and TripleO-Quickstart
# repositories cloned into that folder with their default folder names. The env vars
# must be exported outside of install-and-test.sh not inside, otherwise they don't get
# passed to some components of TripleO. You also must have your ssh key copied to root
# on virthost for ansible to work.
#
set -eux

RELEASE=$1
BUILD_SYS=$2
CONFIG=$3
JOB_TYPE=$4
SSH_CMD="ssh -tt -F $WORKSPACE/ssh.config.ansible undercloud"
SCP_CMD="scp -F $WORKSPACE/ssh.config.ansible"
DIFF_CMD="git diff origin/master --name-only"


if [ "$JOB_TYPE" = "gate" ] || [ "$JOB_TYPE" = "periodic" ]; then
    LOCATION='stable'
elif [ "$JOB_TYPE" = "promote" ]; then
    LOCATION='testing'
else
    echo "Job type must be one of gate, periodic, or promote"
    exit 1
fi

# (trown) This is so that we ensure separate ssh sockets for
# concurrent jobs. Without this, two jobs running in parallel
# would try to use the same undercloud-stack socket.
socketdir=$(mktemp -d /tmp/sockXXXXXX)
export ANSIBLE_SSH_CONTROL_PATH=$socketdir/%%h-%%r


deployCloud()
{
  pushd $WORKSPACE/tripleo-quickstart
  bash quickstart.sh \
  --tags all \
  --playbook quickstart-extras.yml \
  --requirements quickstart-extras-requirements.txt \
  -R mitaka \
  --bootstrap \
  --working-dir $WORKSPACE \
  $VIRTHOST $RELEASE
  popd
}


deployBrowbeat()
{
  #The vitrualenv script is delicate to environmental changes
  #this restores the default terminal mode temporarily (jkilpatr)
  set +eux
  . $WORKSPACE/bin/activate
  set -eux

  pip install ansible

  pushd $WORKSPACE/browbeat/ansible

  cp $WORKSPACE/browbeat/ci-scripts/config/tripleo/install-and-check/all.yml $WORKSPACE/browbeat/ansible/install/group_vars/all.yml

  #Clone repo from ci (with current changes) to $VIRTHOST so that we test the current commit
  $SCP_CMD -r $WORKSPACE/browbeat undercloud:

  ansible-playbook --ssh-common-args="-F $WORKSPACE/ssh.config.ansible" -i $WORKSPACE/hosts install/browbeat.yml


  ansible-playbook --ssh-common-args="-F $WORKSPACE/ssh.config.ansible" -i $WORKSPACE/hosts install/browbeat_network.yml

  #Non functional until upstream fix released (jkipatr)
  #ansible-playbook --ssh-common-args="-F $WORKSPACE/ssh.config.ansible" -i $WORKSPACE/hosts install/shaker_build.yml

  #Required to change the configs on the Undercloud since we must run from there
  $SCP_CMD $WORKSPACE/browbeat/ci-scripts/config/browbeat-ci.yaml undercloud:/home/stack/browbeat/browbeat-config.yaml

  popd
}

runGather()
{
 pushd $WORKSPACE/browbeat/ansible

 ansible-playbook --ssh-common-args="-F $WORKSPACE/ssh.config.ansible" -i $WORKSPACE/hosts gather/site.yml

 popd
}

runCheck()
{
 pushd $WORKSPACE/browbeat/ansible

 ansible-playbook --ssh-common-args="-F $WORKSPACE/ssh.config.ansible" -i $WORKSPACE/hosts check/site.yml

 pushd $WORKSPACE/browbeat/results
 if [[ $(cat bug_report.log) == "" ]]
 then
   #checks failed to create the bug_report.log
   exit 1
 fi
 popd
 popd
}

runBrowbeat()
{
  $SSH_CMD ". /home/stack/browbeat-venv/bin/activate; cd /home/stack/browbeat; python browbeat.py $1"
}

#minimum check
time deployCloud
time deployBrowbeat

pushd $WORKSPACE/browbeat
if [[ $($DIFF_CMD | grep -i metadata) != "" ]]
then
  time runGather
fi
popd

pushd $WORKSPACE/browbeat

if [[ $($DIFF_CMD | grep -i check) != "" ]]
then
  time runCheck
fi
popd

#variable to determine if an execution test has already happened
HASRUN=false

pushd $WORKSPACE/browbeat
#re-add shaker to tools list when fixed upstream
#re-add perfkit to this list after investigation
for tool in rally; do

  if [[ $($DIFF_CMD | grep -i $tool) != "" ]]
  then
    time runBrowbeat $tool
    HASRUN=true
  fi

done

#Tests files in lib/
if [[ $($DIFF_CMD | grep -i lib\/) != "" ]] && [ $HASRUN == false ]
then
  time runBrowbeat rally
  HASRUN=true
fi

#Test Browbeat.py
if [[ $($DIFF_CMD | grep -i browbeat.py) != "" ]] && [ $HASRUN == false ]
then
  time runBrowbeat rally
  HASRUN=true
fi
popd

exit 0
