#!/usr/bin/env bash
set -euo pipefail

# Docker Desktop may expose TCP GSO super-packets to Ettercap as oversized
# Ethernet frames. Disable interface offloads so the MITM can relay them.
if command -v ethtool >/dev/null 2>&1; then
  sudo -n ethtool -K eth0 gro off 2>/dev/null || true
  sudo -n ethtool -K eth0 gso off tso off 2>/dev/null || true
fi

exec "$@"
