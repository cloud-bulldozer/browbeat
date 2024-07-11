#!/bin/bash

# Get the last segment of the pod name (assuming the pod name is stored in POD_NAME environment variable)
POD_NAME_SUFFIX=$(echo $POD_NAME | awk -F '-' '{print $NF}')

# Determine the configuration file based on the pod name suffix
if [ "$POD_NAME_SUFFIX" = "0" ]; then
  CONFIG_FILE="/etc/config/collectd-db.conf"
else
  CONFIG_FILE="/etc/config/collectd.conf"
fi

# Start the main process with the selected configuration file
exec collectd -f -C $CONFIG_FILE
