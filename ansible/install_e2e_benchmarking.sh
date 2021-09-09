#!/usr/bin/env bash

ansible_dir=`pwd`
cd gather/e2e-benchmarking/workloads/kube-burner

create_operator_deploy_script() {
    cat > deploy_operator.sh <<- EOM
#!/usr/bin/bash -e

set -e

. common.sh

deploy_operator
exit 0
EOM
}

remove_unnecessary_calls_from_scripts() {
    find . -type f -name '*fromgit.sh' | xargs sed -i -e 's/deploy_operator//g'
    find . -type f -name '*fromgit.sh' | xargs sed -i -e 's/check_running_benchmarks//g'
    find . -type f -name '*fromgit.sh' | xargs sed -i -e 's/rm -rf benchmark-operator//g'
}

create_operator_deploy_script
sudo chmod 775 deploy_operator.sh
./deploy_operator.sh
remove_unnecessary_calls_from_scripts
cd $ansible_dir
