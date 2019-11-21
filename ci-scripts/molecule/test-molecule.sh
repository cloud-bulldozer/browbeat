#!/bin/bash


# Run molecule tests. Any arguments passed to this script will be passed onto
# molecule.

set -e

molecules="$(find ansible/install/roles/ -name molecule -type d)"

failed=0
ran=0
for molecule in $molecules; do
    pushd $(dirname $molecule)
    if ! molecule test --all $*; then
        failed=$((failed + 1))
    fi
    ran=$((ran + 1))
    popd
done

if [[ $failed -ne 0 ]]; then
    echo "Failed $failed / $ran molecule tests"
    exit 1
fi

echo "Ran $ran molecule tests successfully"
