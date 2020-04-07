#!/bin/sh
HOSTNAME="${COLLECTD_HOSTNAME:-`hostname -f`}"
INTERVAL="${COLLECTD_INTERVAL:-15}"

while sleep "$INTERVAL"; do
  VALUE=$(sudo ovs-ofctl dump-flows br-int | wc -l)
  echo "PUTVAL \"$HOSTNAME/ovs-flows/gauge-ovs_flows\" interval=$INTERVAL N:$VALUE"
done
