#!/usr/bin/env bash
# Installs Browbeat against locally deployed tripleo quickstart cloud_name
# Follow guide on deploying tripleoo quickstart cloud before using this script

function usage
{
    echo "Usage: oooq-browbeat-install.sh [-h] [--undercloud]"
    echo "          -h, --help        show this help message"
    echo "          -u, --undercloud  install on oooq UC"
    echo "Installs Browbeat against tripleo quickstart cloud off local machine.  Browbeat is"
    echo "installed locally by default, but can be installed on the Undercloud."
}

install_host="localhost"
while [ "$1" != "" ]; do
  case $1 in
    -u | --undercloud )     install_host="undercloud"
                            shift
                            ;;
    -h | --help )           usage
                            exit
                            ;;
    * )                     usage
                            exit 1
  esac
  shift
done

echo "Installing Browbeat on ${install_host}"

# Clean ssh environment
rm -rf ansible/hosts ansible/ssh-config browbeat.pem

# Copy ssh-config and inventory hosts file
cp ~/.quickstart/ssh.config.ansible ansible/ssh-config
cp ~/.quickstart/hosts ansible/hosts

# Use localhost or undercloud for the Browbeat machine
echo "[browbeat]" >> ansible/hosts
echo "${install_host}" >> ansible/hosts

if [ "$install_host" == "localhost" ]; then
  # Clean local environment
  rm -rf .browbeat-venv/ .perfkit-venv/ .rally-venv/ .shaker-venv/
  rm -rf stackrc overcloudrc

  # Make sure brovc.10 is up
  sudo ifup brovc.10

  # Copy stackrc/overcloudrc
  scp -F ansible/ssh-config undercloud:stackrc .
  scp -F ansible/ssh-config undercloud:overcloudrc .

  # Local machine Install environment vars:
  browbeat_user=$(whoami)
  browbeat_path=$(pwd)
  overcloudrc=${browbeat_path}/overcloudrc

  # Install on local machine, browbeat_results_in_httpd=False because likely we don't want httpd
  # installed on the local host
  pushd ansible
  ansible-playbook -i hosts install/browbeat.yml -e "browbeat_user=${browbeat_user} browbeat_path=${browbeat_path} overcloudrc=${overcloudrc} browbeat_results_in_httpd=False"
  popd
else
  # Install on Undercloud machine
  pushd ansible
  ansible-playbook -i hosts install/browbeat.yml
  popd
fi
