#!/bin/bash

# OpenWRT Reporter Installation Script
# Run this script as root on your OpenWRT router

set -e

echo "=== OpenWRT MQTT Reporter Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
opkg update
opkg install python3 python3-pip python3-setuptools

# Install paho-mqtt
echo "Installing paho-mqtt..."
pip3 install paho-mqtt

# Copy the reporter script
echo "Installing reporter script..."
cp openwrt-reporter.py /usr/bin/
chmod +x /usr/bin/openwrt-reporter.py

# Copy and install the init script
echo "Installing init script..."
cp openwrt-reporter.init /etc/init.d/openwrt-reporter
chmod +x /etc/init.d/openwrt-reporter

# Install UCI configuration
echo "Installing UCI configuration..."
cp openwrt-reporter.uci /etc/config/openwrt-reporter

# Enable the service
echo "Enabling service..."
/etc/init.d/openwrt-reporter enable

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Configuration:"
echo "1. Edit UCI configuration: uci show openwrt-reporter"
echo "2. Set MQTT host: uci set openwrt-reporter.mqtt.host='your.mqtt.host'"
echo "3. Commit changes: uci commit openwrt-reporter"
echo ""
echo "Service commands:"
echo "  Start:   /etc/init.d/openwrt-reporter start"
echo "  Stop:    /etc/init.d/openwrt-reporter stop"
echo "  Restart: /etc/init.d/openwrt-reporter restart"
echo "  Status:  /etc/init.d/openwrt-reporter status"
echo "  Logs:    logread | grep openwrt-reporter"
echo ""
echo "Configuration commands:"
echo "  Show config:      uci show openwrt-reporter"
echo "  Enable verbose:   uci set openwrt-reporter.global.verbose=1"
echo "  Set MQTT host:    uci set openwrt-reporter.mqtt.host='192.168.1.100'"
echo "  Disable service:  uci set openwrt-reporter.global.enabled=0"
echo "  Add interface:    uci add openwrt-reporter interface"
echo "  Commit changes:   uci commit openwrt-reporter"
echo ""
