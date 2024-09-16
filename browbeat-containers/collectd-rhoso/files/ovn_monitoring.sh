#!/bin/sh
HOSTNAME="${COLLECTD_HOSTNAME:-`hostname -f`}"
INTERVAL="${COLLECTD_INTERVAL:-15}"

if [ "$1" = "sb" ]; then
  IP=$OVN_SBDB_IP
  PORT=$OVN_SBDB_PORT
  DB="ovnsb"
else
  IP=$OVN_NBDB_IP
  PORT=$OVN_NBDB_PORT
  DB="ovnnb"
fi

PRIVATE_KEY="/etc/pki/$DB/tls/private/ovndb.key"
CERTIFICATE="/etc/pki/$DB/tls/certs/ovndb.crt"
CA_CERT="/etc/pki/$DB/tls/certs/ovndbca.crt"

while sleep "$INTERVAL"; do
  VALUE=$(sudo ovsdb-client dump --no-headings ssl:$IP:$PORT \
    --private-key=$PRIVATE_KEY \
    --certificate=$CERTIFICATE \
    --ca-cert=$CA_CERT \
    $2 | wc -l)
  VALUE=$[VALUE-1]
  echo "PUTVAL \"$HOSTNAME/ovn-$1db-$2/gauge-ovn_$1db_$2\" interval=$INTERVAL N:$VALUE"
done
