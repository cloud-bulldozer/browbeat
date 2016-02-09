#!/bin/bash

HOSTNAME="${COLLECTD_HOSTNAME:-`hostname -f`}"
INTERVAL="${COLLECTD_INTERVAL:-10}"
PORT=6379

while true
do

info=$((echo info ; sleep 2) |nc -w 1 $HOSTNAME $PORT 2>&1)
connected_clients=$(echo "$info" | egrep ^connected_clients| awk -F: '{ print $2 }' | sed 's///g')
connected_slaves=$(echo "$info" | egrep ^connected_slaves| awk -F: '{ print $2 }' | sed 's///g')
uptime=$(echo "$info" | egrep ^uptime_in_seconds| awk -F: '{ print $2 }' | sed 's///g')
used_memory=$(echo "$info" | egrep ^used_memory:| awk -F: '{ print $2 }' | sed 's///g')
changes_since_last_save=$(echo "$info" | egrep ^rdb_changes_since_last_save| awk -F: '{ print $2 }' | sed 's///g')
total_commands_processed=$(echo "$info" | egrep ^total_commands_processed| awk -F: '{ print $2 }' | sed 's///g')
keys=$(echo "$info" | egrep ^db0:keys| awk -F= '{ print $2 }' | awk -F, '{ print $1 }' | sed 's///g')

echo "PUTVAL $HOSTNAME/redis-$PORT/memcached_connections-clients interval=$INTERVAL N:$connected_clients"
echo "PUTVAL $HOSTNAME/redis-$PORT/memcached_connections-slaves interval=$INTERVAL N:$connected_slaves"
echo "PUTVAL $HOSTNAME/redis-$PORT/uptime interval=$INTERVAL N:$uptime"
echo "PUTVAL $HOSTNAME/redis-$PORT/df-memory interval=$INTERVAL N:$used_memory:U"
echo "PUTVAL $HOSTNAME/redis-$PORT/files-unsaved_changes interval=$INTERVAL N:$changes_since_last_save"
echo "PUTVAL $HOSTNAME/redis-$PORT/memcached_command-total interval=$INTERVAL N:$total_commands_processed"
echo "PUTVAL $HOSTNAME/redis-$PORT/memcached_items-db0 interval=$INTERVAL N:$keys"

sleep "$INTERVAL"
done

