#!/bin/bash

scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.34:/usr/bin/
echo "192.168.1.34"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.35:/usr/bin/
echo "192.168.1.35"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.36:/usr/bin/
echo "192.168.1.36"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.37:/usr/bin/
echo "192.168.1.37"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.38:/usr/bin/
echo "192.168.1.38"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.39:/usr/bin/
echo "192.168.1.39"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.41:/usr/bin/
echo "192.168.1.41"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.42:/usr/bin/
echo "192.168.1.42"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.45:/usr/bin/
echo "192.168.1.45"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.46:/usr/bin/
echo "192.168.1.46"
scp ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@192.168.1.48:/usr/bin/
echo "192.168.1.48"
scp -P 8021 ./client/target/x86_64-unknown-linux-musl/release/watchdog-client root@113.55.126.9:/usr/bin/
echo "113.55.126.9:8021"

scp ./watchdog-client-local.service root@192.168.1.34:/etc/systemd/system/
echo "192.168.1.34"
scp ./watchdog-client-local.service root@192.168.1.35:/etc/systemd/system/
echo "192.168.1.35"
scp ./watchdog-client-local.service root@192.168.1.36:/etc/systemd/system/
echo "192.168.1.36"
scp ./watchdog-client-local.service root@192.168.1.37:/etc/systemd/system/
echo "192.168.1.37"
scp ./watchdog-client-local.service root@192.168.1.38:/etc/systemd/system/
echo "192.168.1.38"
scp ./watchdog-client-local.service root@192.168.1.39:/etc/systemd/system/
echo "192.168.1.39"
scp ./watchdog-client-local.service root@192.168.1.41:/etc/systemd/system/
echo "192.168.1.41"
scp ./watchdog-client-local.service root@192.168.1.42:/etc/systemd/system/
echo "192.168.1.42"
scp ./watchdog-client-local.service root@192.168.1.45:/etc/systemd/system/
echo "192.168.1.45"
scp ./watchdog-client-local.service root@192.168.1.46:/etc/systemd/system/
echo "192.168.1.46"
scp ./watchdog-client-local.service root@192.168.1.48:/etc/systemd/system/
echo "192.168.1.48"
scp -P 8021 ./watchdog-client-remote.service root@113.55.126.9:/etc/systemd/system/
echo "113.55.126.9:8021"
