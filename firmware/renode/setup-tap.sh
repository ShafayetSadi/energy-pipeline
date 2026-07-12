#!/usr/bin/env bash
# One-time host setup: TAP interface bridging Renode's emulated Ethernet to
# the host network stack. Run with sudo. The firmware uses static IP
# 192.168.100.2 and talks to Mosquitto on 192.168.100.1:18831 (host port
# published by docker-compose).
set -euo pipefail

TAP=tap-stm32
HOST_IP=192.168.100.1/24

if ip link show "$TAP" &>/dev/null; then
    echo "$TAP already exists"
else
    ip tuntap add dev "$TAP" mode tap user "${SUDO_USER:-$USER}"
fi
# Keep NetworkManager from managing (and de-configuring) the TAP.
command -v nmcli &>/dev/null && nmcli device set "$TAP" managed no 2>/dev/null || true
ip addr replace "$HOST_IP" dev "$TAP"
ip link set "$TAP" up
echo "$TAP up at $HOST_IP — start Renode with renode/nucleo_f429zi.resc"
echo "Note: Mosquitto must listen on 0.0.0.0 (docker-compose port mapping does this)."
