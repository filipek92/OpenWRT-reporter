#!/bin/bash

# OpenWRT Reporter Version Check Script

echo "=== OpenWRT MQTT Reporter Version Info ==="
echo ""

# Check if installed
if [ ! -f "/usr/bin/openwrt-reporter.py" ]; then
    echo "Status: NOT INSTALLED"
    exit 1
fi

echo "Status: INSTALLED"
echo ""

# Get version from script (if available)
if grep -q "# Version:" /usr/bin/openwrt-reporter.py 2>/dev/null; then
    VERSION=$(grep "# Version:" /usr/bin/openwrt-reporter.py | cut -d' ' -f3)
    echo "Version: $VERSION"
else
    echo "Version: Unknown (no version info in script)"
fi

# Check installation date
if [ -f "/usr/bin/openwrt-reporter.py" ]; then
    INSTALL_DATE=$(stat -c %y /usr/bin/openwrt-reporter.py | cut -d' ' -f1)
    echo "Last updated: $INSTALL_DATE"
fi

echo ""

# Service status
echo "Service Status:"
if /etc/init.d/openwrt-reporter status >/dev/null 2>&1; then
    echo "  Running: YES"
else
    echo "  Running: NO"
fi

if /etc/init.d/openwrt-reporter enabled >/dev/null 2>&1; then
    echo "  Autostart: ENABLED"
else
    echo "  Autostart: DISABLED"
fi

echo ""

# Configuration check
echo "Configuration:"
if [ -f "/etc/config/openwrt-reporter" ]; then
    echo "  UCI config: PRESENT"
    
    # Count interfaces
    BASE_COUNT=$(uci show openwrt-reporter 2>/dev/null | grep "\.type='base'" | wc -l)
    VIRTUAL_COUNT=$(uci show openwrt-reporter 2>/dev/null | grep "\.type='virtual'" | wc -l)
    echo "  Base interfaces: $BASE_COUNT"
    echo "  Virtual interfaces: $VIRTUAL_COUNT"
    
    # MQTT host
    MQTT_HOST=$(uci get openwrt-reporter.mqtt.host 2>/dev/null || echo "unknown")
    echo "  MQTT host: $MQTT_HOST"
else
    echo "  UCI config: MISSING"
fi

echo ""

# Recent logs
echo "Recent logs (last 10 lines):"
logread | grep openwrt-reporter | tail -10 | while read line; do
    echo "  $line"
done

echo ""

# Quick test
echo "Configuration test:"
if python3 /usr/bin/openwrt-reporter.py --config >/dev/null 2>&1; then
    echo "  Status: PASSED"
else
    echo "  Status: FAILED - run with --verbose for details"
fi

echo ""
echo "For detailed configuration: python3 /usr/bin/openwrt-reporter.py --config"
echo "For verbose test: python3 /usr/bin/openwrt-reporter.py --config --verbose"
echo ""
