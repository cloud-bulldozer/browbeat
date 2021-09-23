#!/bin/sh
HOSTNAME="${COLLECTD_HOSTNAME:-`hostname -f`}"
INTERVAL="${COLLECTD_INTERVAL:-15}"

while sleep "$INTERVAL"; do
  VALUE=$(sudo ovsdb-client dump unix:/var/lib/openvswitch/ovn/ovn$1_db.sock $2 | wc -l)
  echo "PUTVAL \"$HOSTNAME/ovn-$2/gauge-ovn_$2\" interval=$INTERVAL N:$VALUE"
done
