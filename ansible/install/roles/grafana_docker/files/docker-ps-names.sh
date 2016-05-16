#!/bin/sh

/usr/bin/docker ps -a  --format '{{ .Names }}'
