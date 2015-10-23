#!/bin/bash
source ~/stackrc
CONTROLLERS=$(nova list | grep control)
# Fill in with pbench repo url:
PBENCH_REPO=''
LOGIN_USER="heat-admin"

# Install pbench repo
sudo wget -O /etc/yum.repos.d/pbench.repo ${PBENCH_REPO}
# Install pbench-agent
sudo yum install -y pbench-agent
# Source pbench-agent
source /opt/pbench-agent/base

# Since user stack, create directories for pbench-agent and own them for stack
sudo mkdir -p /var/lib/pbench-agent
sudo chown stack:stack /var/lib/pbench-agent/

echo_cmd="echo \"`cat /home/stack/.ssh/id_rsa.pub`\""
for IP in $(echo "$CONTROLLERS" | awk '{print $12}' | cut -d "=" -f 2); do
  echo "Installing pbench on Controller: ${IP}"
  scp /etc/yum.repos.d/rhos-release-rhel-7.1.repo ${LOGIN_USER}@${IP}:
  ssh ${LOGIN_USER}@${IP} sudo mv /home/heat-admin/rhos-release-rhel-7.1.repo /etc/yum.repos.d/rhos-release-rhel-7.1.repo
  ssh ${LOGIN_USER}@${IP} sudo yum install -y wget
  ssh ${LOGIN_USER}@${IP} sudo wget -O /etc/yum.repos.d/pbench.repo ${PBENCH_REPO}
  ssh ${LOGIN_USER}@${IP} sudo yum install -y pbench-agent

  # Setup stack to root ssh:
  ssh ${LOGIN_USER}@${IP} 'sudo sed -i "/Please login as the user/d" /root/.ssh/authorized_keys'
  ssh ${LOGIN_USER}@${IP} "sudo ${echo_cmd} | sudo tee -a /root/.ssh/authorized_keys"
  echo "host ${IP}" | tee -a /home/stack/.ssh/config
done
echo "user root" | tee -a /home/stack/.ssh/config
chmod 0644 /home/stack/.ssh/config
