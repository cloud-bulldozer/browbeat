#!/bin/bash

grep -o 'UUID: [^,]*' /tmp/browbeatrun_log.log| tail -1 | grep -o ' [^,]*' | tr -d ' ' | sed 's/\x27/ /g'


