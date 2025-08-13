#!/usr/bin/env python3

import time
import json
import re
import subprocess
import threading
import atexit
import sys
from paho.mqtt import client as mqtt

# --- Configuration ---
VERBOSE = "--verbose" in sys.argv

# Load UCI configuration
def load_uci_config():
    """Load configuration from UCI"""
    config = {
        'enabled': True,
        'verbose': VERBOSE,  # Command line overrides UCI
        'mqtt': {
            'host': 'mqtt.lan',
            'port': 1883,
            'username': '',
            'password': '',
            'base_topic': 'openwrt',
            'discovery_prefix': 'homeassistant'
        },
        'interfaces': {
            'base': [],
            'virtual': []
        }
    }
    
    try:
        # Read UCI config
        import subprocess
        result = subprocess.run(['uci', 'show', 'openwrt-reporter'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            if VERBOSE: print("[WARN] UCI config not found, using defaults")
            return get_default_config()
            
        for line in result.stdout.strip().split('\n'):
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            value = value.strip("'\"")
            
            # Parse configuration
            if 'global.enabled' in key:
                config['enabled'] = value == '1'
            elif 'global.verbose' in key and not VERBOSE:  # CLI overrides
                config['verbose'] = value == '1'
            elif 'mqtt.' in key:
                mqtt_key = key.split('.')[-1]
                if mqtt_key == 'port':
                    config['mqtt']['port'] = int(value)
                else:
                    config['mqtt'][mqtt_key] = value
            elif '.interface.' in key and '=interface' not in key:
                # Parse interface config
                parts = key.split('.')
                if len(parts) >= 4:
                    iface_name = parts[1].replace('openwrt-reporter', '').strip('@[]')
                    if iface_name.isdigit():
                        continue  # Skip numeric indices
                    attr = parts[-1]
                    
                    # Find or create interface config
                    iface_config = None
                    for iface in config['interfaces']['base'] + config['interfaces']['virtual']:
                        if iface.get('name') == iface_name:
                            iface_config = iface
                            break
                    
                    if not iface_config:
                        iface_config = {'name': iface_name, 'enabled': True, 'type': 'base'}
                        config['interfaces']['base'].append(iface_config)
                    
                    if attr == 'enabled':
                        iface_config['enabled'] = value == '1'
                    elif attr == 'type':
                        # Move to correct list if type changed
                        if iface_config in config['interfaces']['base'] and value == 'virtual':
                            config['interfaces']['base'].remove(iface_config)
                            config['interfaces']['virtual'].append(iface_config)
                        elif iface_config in config['interfaces']['virtual'] and value == 'base':
                            config['interfaces']['virtual'].remove(iface_config)
                            config['interfaces']['base'].append(iface_config)
                        iface_config['type'] = value
                    else:
                        iface_config[attr] = value
                        
    except Exception as e:
        if VERBOSE: print(f"[WARN] Failed to load UCI config: {e}")
        return get_default_config()
    
    # Filter enabled interfaces
    config['interfaces']['base'] = [i for i in config['interfaces']['base'] if i.get('enabled', True)]
    config['interfaces']['virtual'] = [i for i in config['interfaces']['virtual'] if i.get('enabled', True)]
    
    # If no interfaces configured, use defaults
    if not config['interfaces']['base'] and not config['interfaces']['virtual']:
        return get_default_config()
        
    return config

def get_default_config():
    """Default configuration fallback"""
    return {
        'enabled': True,
        'verbose': VERBOSE,
        'mqtt': {
            'host': 'mqtt.lan',
            'port': 1883,
            'username': '',
            'password': '',
            'base_topic': 'openwrt',
            'discovery_prefix': 'homeassistant'
        },
        'interfaces': {
            'base': [
                {'name': 'wan', 'label': 'StarNet', 'enabled': True, 'monitor_ipv4': True, 'monitor_ipv6': False},
                {'name': 'wanb', 'label': 'Vodafone LTE', 'enabled': True, 'monitor_ipv4': True, 'monitor_ipv6': False}
            ],
            'virtual': [
                {'name': 'wan6', 'label': 'StarNet', 'enabled': True, 'monitor_ipv4': False, 'monitor_ipv6': True}
            ]
        }
    }

# Load configuration
CONFIG = load_uci_config()
if not CONFIG['enabled']:
    print("[INFO] OpenWRT Reporter is disabled in configuration")
    sys.exit(0)

VERBOSE = CONFIG['verbose']  # Update VERBOSE from config

# Thread safety
mqtt_lock = threading.Lock()
stats_lock = threading.Lock()

# Apply configuration
MQTT_HOST = CONFIG['mqtt']['host']
MQTT_PORT = CONFIG['mqtt']['port'] 
MQTT_USERNAME = CONFIG['mqtt']['username']
MQTT_PASSWORD = CONFIG['mqtt']['password']
BASE_TOPIC = CONFIG['mqtt']['base_topic']
DISCOVERY_PREFIX = CONFIG['mqtt']['discovery_prefix']

# Build interface lists from config
BASE_INTERFACES = [i['name'] for i in CONFIG['interfaces']['base']]
VIRTUAL_INTERFACES = [i['name'] for i in CONFIG['interfaces']['virtual']]
ALL_INTERFACES = BASE_INTERFACES + VIRTUAL_INTERFACES

# Build interface labels
INTERFACE_LABELS = {}
for iface in CONFIG['interfaces']['base'] + CONFIG['interfaces']['virtual']:
    INTERFACE_LABELS[iface['name']] = iface.get('label', iface['name'].upper())

client = mqtt.Client()

# Set authentication if provided
if MQTT_USERNAME:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

try:
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    if VERBOSE: print(f"[INFO] Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
except Exception as e:
    print(f"[ERROR] Failed to connect to MQTT broker: {e}")
    sys.exit(1)

# --- Utilities ---
def safe_publish(topic, payload, retain=False):
    """Thread-safe MQTT publish"""
    with mqtt_lock:
        try:
            client.publish(topic, payload, retain=retain)
        except Exception as e:
            if VERBOSE: print(f"[ERROR] Failed to publish to {topic}: {e}")

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
    except subprocess.CalledProcessError as e:
        if VERBOSE: print(f"[ERROR] {cmd} → {e.output.decode().strip()}")
        return "unavailable"

def ubus_status(interface):
    raw = run_cmd(f"ubus call network.interface.{interface} status '{{}}'")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        if VERBOSE: print(f"[ERROR] JSON parse {interface}: {raw}")
        return {}

def get_interface_device(interface):
    return ubus_status(interface).get("l3_device", "")

def get_ip(interface, version="ipv4"):
    key = "ipv4-address" if version == "ipv4" else "ipv6-address"
    status = ubus_status(interface)
    addrs = status.get(key, [])
    if not isinstance(addrs, list):
        if VERBOSE: print(f"[WARN] {interface} {version} address list is not a list: {addrs}")
        return "unavailable"
    for item in addrs:
        if isinstance(item, dict) and "address" in item:
            return item["address"]
    if VERBOSE: print(f"[WARN] {interface} {version} address not found in: {addrs}")
    return "unavailable"

def get_operstate(dev):
    result = run_cmd(f"cat /sys/class/net/{dev}/operstate").lower()
    return result if result else "unavailable"

def get_bytes(dev, direction):
    try:
        with open(f"/sys/class/net/{dev}/statistics/{direction}_bytes") as f:
            return int(f.read().strip())
    except Exception as e:
        if VERBOSE: print(f"[WARN] Failed to read {direction}_bytes for {dev}: {e}")
        return "unavailable"

def get_active_mwan():
    raw = run_cmd("mwan3 status")
    for line in raw.splitlines():
        m = re.search(r'interface\s+([^\s]+)\s+is online', line, re.IGNORECASE)
        if m:
            return m.group(1)
    return "unknown"

def get_mwan_status():
    raw = run_cmd("mwan3 status")
    result = {}
    for line in raw.splitlines():
        m = re.search(r'interface\s+([^\s]+)\s+is\s+(\w+)', line, re.IGNORECASE)
        if m:
            result[m.group(1)] = m.group(2).lower()
    return result

# --- Discovery ---
def publish_binary_sensor(iface, key, name, payload_on, payload_off, icon):
    label = INTERFACE_LABELS.get(iface, iface.upper())
    device_info = {
        "identifiers": [f"{BASE_TOPIC}_{iface}"],
        "name": f"{label} Interface",
        "manufacturer": "OpenWRT",
        "model": "MWAN3 Reporter"
    }
    payload = {
        "availability_topic": f"{BASE_TOPIC}/{iface}/availability",
        "payload_available": "online",
        "payload_not_available": "offline",
        "name": f"{label} {name}",
        "state_topic": f"{BASE_TOPIC}/{iface}/{key}",
        "payload_on": payload_on,
        "payload_off": payload_off,
        "device_class": "connectivity",
        "icon": icon,
        "unique_id": f"{BASE_TOPIC}_{iface}_{key}",
        "device": device_info
    }
    safe_publish(
        f"{DISCOVERY_PREFIX}/binary_sensor/{BASE_TOPIC}_{iface}_{key}/config",
        json.dumps(payload), retain=True
    )

def publish_sensor(iface, key, name, unit, device_class, icon):
    label = INTERFACE_LABELS.get(iface, iface.upper())
    device_info = {
        "identifiers": [f"{BASE_TOPIC}_{iface}"],
        "name": f"{label} Interface",
        "manufacturer": "OpenWRT",
        "model": "MWAN3 Reporter"
    }
    payload = {
        "availability_topic": f"{BASE_TOPIC}/{iface}/availability",
        "payload_available": "online",
        "payload_not_available": "offline",
        "name": f"{label} {name}",
        "state_topic": f"{BASE_TOPIC}/{iface}/{key}",
        "icon": icon,
        "unique_id": f"{BASE_TOPIC}_{iface}_{key}",
        "device": device_info
    }
    if unit:
        payload["unit_of_measurement"] = unit
    if device_class:
        payload["device_class"] = device_class
    safe_publish(
        f"{DISCOVERY_PREFIX}/sensor/{BASE_TOPIC}_{iface}_{key}/config",
        json.dumps(payload), retain=True
    )

def publish_discovery():
    for iface in BASE_INTERFACES:
        publish_binary_sensor(iface, "status", "MWAN Stav", "online", "offline", "mdi:wan")
        publish_binary_sensor(iface, "link_status", "Link Stav", "up", "down", "mdi:lan-connect")
        for dir in ["rx", "tx"]:
            publish_sensor(iface, f"{dir}_bytes", f"{dir.upper()} Bytes", "B", "data_size", "mdi:counter")
            publish_sensor(iface, f"{dir}_rate", f"{dir.upper()} Rate", "B/s", "data_rate", "mdi:speedometer")
        publish_sensor(iface, "ipv4", "IPv4", None, None, "mdi:ip")
    for iface in VIRTUAL_INTERFACES:
        label = INTERFACE_LABELS.get(iface, iface.upper())
        publish_binary_sensor(iface, "status", f"{label} Stav", "online", "offline", "mdi:wan")
        publish_sensor(iface, "ipv6", "IPv6", None, None, "mdi:ip")
    
    # MWAN3 sensors s vlastním device
    mwan_device_info = {
        "identifiers": [f"{BASE_TOPIC}_mwan3"],
        "name": "MWAN3 Load Balancer",
        "manufacturer": "OpenWRT",
        "model": "MWAN3 Reporter"
    }
    
    safe_publish(
        f"{DISCOVERY_PREFIX}/sensor/{BASE_TOPIC}_mwan3_active/config",
        json.dumps({
            "name": "Aktivní WAN",
            "state_topic": f"{BASE_TOPIC}/mwan3/active",
            "icon": "mdi:network",
            "unique_id": f"{BASE_TOPIC}_mwan3_active",
            "availability_topic": f"{BASE_TOPIC}/mwan3/availability",
            "payload_available": "online",
            "payload_not_available": "offline",
            "options": ["wan", "wanb", "unknown"],
            "device": mwan_device_info
        }), retain=True
    )
    
    safe_publish(
        f"{DISCOVERY_PREFIX}/sensor/{BASE_TOPIC}_mwan3_active_name/config",
        json.dumps({
            "name": "Aktivní WAN Název",
            "state_topic": f"{BASE_TOPIC}/mwan3/active_name",
            "icon": "mdi:wan",
            "unique_id": f"{BASE_TOPIC}_mwan3_active_name",
            "availability_topic": f"{BASE_TOPIC}/mwan3/availability",
            "payload_available": "online",
            "payload_not_available": "offline",
            "options": ["StarNet", "Vodafone LTE", "unknown"],
            "device": mwan_device_info
        }), retain=True
    )

# --- Main Loops ---
last_stats = {}

def fast_loop():
    for iface in ALL_INTERFACES:
        safe_publish(f"{BASE_TOPIC}/{iface}/availability", "online", retain=True)
    safe_publish(f"{BASE_TOPIC}/mwan3/availability", "online", retain=True)
    while True:
        now = time.time()
        mwan_status = get_mwan_status()
        for iface in BASE_INTERFACES:
            dev = get_interface_device(iface)
            if not dev:
                if VERBOSE: print(f"[WARN] Skipping {iface}, no l3_device found (interface is likely down)")
                safe_publish(f"{BASE_TOPIC}/{iface}/link_status", "down")
                safe_publish(f"{BASE_TOPIC}/{iface}/status", mwan_status.get(iface, "offline"))
                continue
            link = get_operstate(dev)
            safe_publish(f"{BASE_TOPIC}/{iface}/link_status", link)
            state = mwan_status.get(iface, "unknown")
            safe_publish(f"{BASE_TOPIC}/{iface}/status", state)
            rx, tx = get_bytes(dev, "rx"), get_bytes(dev, "tx")
            if isinstance(rx, int): safe_publish(f"{BASE_TOPIC}/{iface}/rx_bytes", rx)
            if isinstance(tx, int): safe_publish(f"{BASE_TOPIC}/{iface}/tx_bytes", tx)
            
            # Thread-safe stats handling
            with stats_lock:
                if iface in last_stats:
                    elapsed = now - last_stats[iface]["time"]
                    if elapsed > 0 and isinstance(rx, int) and isinstance(tx, int):
                        rx_rate = (rx - last_stats[iface]["rx"]) / elapsed
                        tx_rate = (tx - last_stats[iface]["tx"]) / elapsed
                        # Ignore negative rates (counter reset)
                        if rx_rate >= 0:
                            safe_publish(f"{BASE_TOPIC}/{iface}/rx_rate", round(rx_rate))
                        if tx_rate >= 0:
                            safe_publish(f"{BASE_TOPIC}/{iface}/tx_rate", round(tx_rate))
                if isinstance(rx, int) and isinstance(tx, int):
                    last_stats[iface] = {"rx": rx, "tx": tx, "time": now}
        for iface in VIRTUAL_INTERFACES:
            dev = get_interface_device(iface)
            if not dev:
                if VERBOSE: print(f"[WARN] Skipping {iface}, no l3_device found (interface is likely down)")
                safe_publish(f"{BASE_TOPIC}/{iface}/status", "offline")
                continue
            state = get_operstate(dev)
            safe_publish(f"{BASE_TOPIC}/{iface}/status", "online" if state == "up" else "offline")
        active = get_active_mwan()
        label = INTERFACE_LABELS.get(active, active)
        safe_publish(f"{BASE_TOPIC}/mwan3/active", active)
        safe_publish(f"{BASE_TOPIC}/mwan3/active_name", label)
        time.sleep(5)

def slow_loop():
    while True:
        # Monitor IPv4 for base interfaces
        for iface_config in CONFIG['interfaces']['base']:
            if iface_config.get('monitor_ipv4', True):
                iface = iface_config['name']
                ip = get_ip(iface, "ipv4") or "unavailable"
                safe_publish(f"{BASE_TOPIC}/{iface}/ipv4", ip)
        
        # Monitor IPv6 for virtual interfaces  
        for iface_config in CONFIG['interfaces']['virtual']:
            if iface_config.get('monitor_ipv6', True):
                iface = iface_config['name']
                ip6 = get_ip(iface, "ipv6") or "unavailable"
                safe_publish(f"{BASE_TOPIC}/{iface}/ipv6", ip6)
        
        # Also monitor IPv6 for base interfaces if configured
        for iface_config in CONFIG['interfaces']['base']:
            if iface_config.get('monitor_ipv6', False):
                iface = iface_config['name']
                ip6 = get_ip(iface, "ipv6") or "unavailable"
                safe_publish(f"{BASE_TOPIC}/{iface}/ipv6", ip6)
                
        time.sleep(60)

# --- Start ---
def publish_offline():
    if VERBOSE: print("[INFO] Publishing offline status...")
    for iface in ALL_INTERFACES:
        safe_publish(f"{BASE_TOPIC}/{iface}/availability", "offline", retain=True)
    safe_publish(f"{BASE_TOPIC}/mwan3/availability", "offline", retain=True)
    time.sleep(1)  # Give time for messages to be sent

atexit.register(publish_offline)

if __name__ == "__main__":
    if VERBOSE: print("[INFO] Starting OpenWRT MQTT Reporter...")
    publish_discovery()
    client.loop_start()
    threading.Thread(target=fast_loop, daemon=True).start()
    threading.Thread(target=slow_loop, daemon=True).start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        if VERBOSE: print("[INFO] Shutting down...")
        publish_offline()
        client.loop_stop()
        client.disconnect()
