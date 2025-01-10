#!/bin/bash

parallel-ssh -i -h localhosts "systemctl daemon-reload"
parallel-ssh -i -h remotehosts "systemctl daemon-reload"
parallel-ssh -i -h localhosts "systemctl start watchdog-client-local.service"
parallel-ssh -i -h remotehosts "systemctl start watchdog-client-remote.service"