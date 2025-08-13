#!/bin/bash

# OpenWRT Reporter Update Script
# Run this script as root on your OpenWRT router

set -e

echo "=== OpenWRT MQTT Reporter Update ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# Check if service is installed
if [ ! -f "/etc/init.d/openwrt-reporter" ]; then
    echo "Error: OpenWRT Reporter is not installed. Run install.sh first."
    exit 1
fi

# Backup current configuration
echo "Backing up current configuration..."
if [ -f "/etc/config/openwrt-reporter" ]; then
    cp /etc/config/openwrt-reporter /tmp/openwrt-reporter.config.backup
    echo "Configuration backed up to /tmp/openwrt-reporter.config.backup"
fi

# Stop the service
echo "Stopping service..."
/etc/init.d/openwrt-reporter stop 2>/dev/null || true

# Update the main script
echo "Updating reporter script..."
if [ -f "openwrt-reporter.py" ]; then
    cp openwrt-reporter.py /usr/bin/
    chmod +x /usr/bin/openwrt-reporter.py
    echo "Reporter script updated"
else
    echo "Warning: openwrt-reporter.py not found in current directory"
fi

# Update init script
echo "Updating init script..."
if [ -f "openwrt-reporter.init" ]; then
    cp openwrt-reporter.init /etc/init.d/openwrt-reporter
    chmod +x /etc/init.d/openwrt-reporter
    echo "Init script updated"
else
    echo "Warning: openwrt-reporter.init not found in current directory"
fi

# Update UCI configuration (only if new template exists and backup was created)
if [ -f "openwrt-reporter.uci" ] && [ -f "/tmp/openwrt-reporter.config.backup" ]; then
    echo "Checking for configuration updates..."
    
    # Check if there are new configuration options
    if ! diff -q openwrt-reporter.uci /etc/config/openwrt-reporter >/dev/null 2>&1; then
        echo "New configuration options detected."
        echo "Current config backed up. You may need to manually merge new options."
        echo "New template: openwrt-reporter.uci"
        echo "Your config: /tmp/openwrt-reporter.config.backup"
        echo ""
        echo "To see differences:"
        echo "  diff /tmp/openwrt-reporter.config.backup openwrt-reporter.uci"
        echo ""
        echo "To reset to new template (will lose current settings):"
        echo "  cp openwrt-reporter.uci /etc/config/openwrt-reporter"
    else
        echo "No configuration changes needed"
    fi
fi

# Test configuration
echo "Testing configuration..."
if python3 /usr/bin/openwrt-reporter.py --config >/dev/null 2>&1; then
    echo "Configuration test passed"
else
    echo "Warning: Configuration test failed. Check with:"
    echo "  python3 /usr/bin/openwrt-reporter.py --config --verbose"
fi

# Start the service
echo "Starting service..."
/etc/init.d/openwrt-reporter start

# Check service status
sleep 2
if /etc/init.d/openwrt-reporter status >/dev/null 2>&1; then
    echo "Service started successfully"
else
    echo "Warning: Service may not have started properly"
    echo "Check logs with: logread | grep openwrt-reporter"
fi

echo ""
echo "=== Update Complete ==="
echo ""
echo "Service commands:"
echo "  Status:  /etc/init.d/openwrt-reporter status"
echo "  Logs:    logread | grep openwrt-reporter"
echo "  Config:  python3 /usr/bin/openwrt-reporter.py --config"
echo ""
echo "Configuration backup: /tmp/openwrt-reporter.config.backup"
echo ""
