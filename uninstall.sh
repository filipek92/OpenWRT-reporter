#!/bin/bash

# OpenWRT Reporter Uninstall Script
# Run this script as root on your OpenWRT router

set -e

echo "=== OpenWRT MQTT Reporter Uninstall ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# Stop and disable service
echo "Stopping service..."
/etc/init.d/openwrt-reporter stop 2>/dev/null || true
/etc/init.d/openwrt-reporter disable 2>/dev/null || true

# Remove files
echo "Removing files..."
rm -f /etc/init.d/openwrt-reporter
rm -f /usr/bin/openwrt-reporter.py
rm -f /var/run/openwrt-reporter.pid

echo ""
echo "=== Uninstall Complete ==="
echo ""
echo "Note: Python3 and paho-mqtt were not removed."
echo "Remove them manually if not needed:"
echo "  opkg remove python3 python3-pip"
echo "  pip3 uninstall paho-mqtt"
echo ""
