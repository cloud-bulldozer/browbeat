#!/bin/bash

CONNECTIONS=$(mysql -u root -e "select count(*), db from information_schema.processlist group by db")
DATA_FILE=./pbench-maraidb-connections.csv
INTERVAL=10
while true; do
  TIME=$(date "+%y-%m-%d %H:%M:%S")
  echo "${CONNECTIONS}" | while IFS= read -r line ; do
   if [[ "$line" =~ .*count.* ]] ; then continue ; fi
   if [[ "$line" =~ .*NULL.* ]] ; then continue ; fi
   count=$(echo $line | awk '{print $1}')
   service=$(echo $line | awk '{print $2}')
   echo "$TIME,$service,$count"
   echo "$TIME,$service,$count" >> ${DATA_FILE}
  done
  sleep $INTERVAL
done 
