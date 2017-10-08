#!/bin/bash

rm -rf <<base_dir>>/procmail*.log
echo '
lcd /home/mzaborow/logs/
prompt off
mget procmail*.log ' | ftp <<ftp_host>>
