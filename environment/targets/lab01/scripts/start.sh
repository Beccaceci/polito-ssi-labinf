#!/bin/sh
set -eu

ethtool -K eth0 gro off 2>/dev/null || true
ethtool -K eth0 gso off tso off 2>/dev/null || true
ssh-keygen -A
mkdir -p /run/sshd
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf -n
