#!/bin/sh
HOSTNAME="${COLLECTD_HOSTNAME:-`hostname -f`}"
INTERVAL="${COLLECTD_INTERVAL:-15}"

if [ "$1" = "sb" ]; then
  IP=$OVN_SBDB_IP
  PORT=$OVN_SBDB_PORT
else
  IP=$OVN_NBDB_IP
  PORT=$OVN_NBDB_PORT
fi

while sleep "$INTERVAL"; do
  VALUE=$(sudo ovsdb-client dump --no-headings tcp:$IP:$PORT $2 | wc -l)
  VALUE=$[VALUE-1]
  echo "PUTVAL \"$HOSTNAME/ovn-$1db-$2/gauge-ovn_$1db_$2\" interval=$INTERVAL N:$VALUE"
done
