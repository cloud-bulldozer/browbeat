#!/bin/bash

grep -o 'UUID: [^,]*' $1 | tail -1 | grep -o ' [^,]*' | tr -d ' ' | sed 's/\x27/ /g'


