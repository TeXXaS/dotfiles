#!/bin/bash

echo "
rename procmail.log $(date -u '+procmail.%Y_%m_%d.log') " | ftp <<ftp_host>>

