#!/bin/bash

# Determine the configuration file based on the node name
CONFIG_FILE="/etc/config/${NODE_NAME}.conf"
# Start the main process with the selected configuration file
exec collectd -f -C $CONFIG_FILE
