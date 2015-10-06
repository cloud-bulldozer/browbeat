#!/bin/bash
task_file=$1
test_name=$2

echo "task_file: ${task_file}"
echo "test_name: ${test_name}"
echo "Before Rally task start."
rally task start --task ${task_file} 2>&1 | tee ${test_name}.log
echo "After Rally task start."
