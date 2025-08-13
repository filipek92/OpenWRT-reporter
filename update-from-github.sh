#!/bin/bash

# OpenWRT Reporter Advanced Update Script
# Downloads latest version from GitHub and updates

set -e

REPO_URL="https://github.com/filipek92/OpenWRT-reporter"
BRANCH="main"
TEMP_DIR="/tmp/openwrt-reporter-update"

echo "=== OpenWRT MQTT Reporter Advanced Update ==="

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

# Check for required tools
if ! command -v wget >/dev/null 2>&1 && ! command -v curl >/dev/null 2>&1; then
    echo "Error: Either wget or curl is required for download"
    echo "Install with: opkg install wget"
    exit 1
fi

# Create temp directory
echo "Creating temporary directory..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Download files
echo "Downloading latest version from GitHub..."
BASE_URL="https://raw.githubusercontent.com/filipek92/OpenWRT-reporter/$BRANCH"

download_file() {
    local file="$1"
    echo "  Downloading $file..."
    
    if command -v wget >/dev/null 2>&1; then
        wget -q "$BASE_URL/$file" -O "$file" || {
            echo "Warning: Failed to download $file"
            return 1
        }
    elif command -v curl >/dev/null 2>&1; then
        curl -s "$BASE_URL/$file" -o "$file" || {
            echo "Warning: Failed to download $file"
            return 1
        }
    fi
    return 0
}

# Download core files
download_file "openwrt-reporter.py"
download_file "openwrt-reporter.init"
download_file "openwrt-reporter.uci"
download_file "install.sh"
download_file "uninstall.sh"
download_file "update.sh"
download_file "README.md"

# Check if main script was downloaded
if [ ! -f "openwrt-reporter.py" ]; then
    echo "Error: Failed to download main script"
    exit 1
fi

# Make scripts executable
chmod +x *.sh 2>/dev/null || true
chmod +x openwrt-reporter.py 2>/dev/null || true
chmod +x openwrt-reporter.init 2>/dev/null || true

echo "Download complete. Running update..."

# Run the standard update script
if [ -f "update.sh" ]; then
    ./update.sh
else
    echo "Warning: update.sh not found, running manual update..."
    
    # Backup current configuration (preserve it)
    echo "Creating configuration backup..."
    if [ -f "/etc/config/openwrt-reporter" ]; then
        cp /etc/config/openwrt-reporter /tmp/openwrt-reporter.config.backup
        echo "Configuration preserved (backup created for safety)"
    fi
    
    # Stop service
    /etc/init.d/openwrt-reporter stop 2>/dev/null || true
    
    # Update files
    cp openwrt-reporter.py /usr/bin/
    chmod +x /usr/bin/openwrt-reporter.py
    
    cp openwrt-reporter.init /etc/init.d/openwrt-reporter
    chmod +x /etc/init.d/openwrt-reporter
    
    # Start service
    /etc/init.d/openwrt-reporter start
    
    echo "Manual update complete"
fi

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "=== Advanced Update Complete ==="
echo ""
echo "Latest version downloaded and installed from GitHub"
echo ""
