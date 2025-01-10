#!/bin/bash

parallel-ssh -i -h localhosts "systemctl stop watchdog-client-local.service"
parallel-ssh -i -h remotehosts "systemctl stop watchdog-client-remote.service"