# OpenWRT MQTT Reporter

MQTT reporter pro OpenWRT routery s MWAN3 podporou. Odesílá telemetrii do Home Assistant přes MQTT.

## Funkce

- 📊 **Dual-WAN monitoring** (WAN + Backup WAN)
- 🌐 **IPv4/IPv6 adresy** pro všechna rozhraní
- 📈 **Rychlosti přenosu** (RX/TX rate)
- 🔗 **Link status** (up/down)
- ⚖️ **MWAN3 status** (aktivní WAN interface)
- 🏠 **Home Assistant Discovery** (automatická konfigurace)
- 🔒 **Thread-safe** architektura
- ⚙️ **UCI konfigurace** (OpenWRT native config)
- 🔐 **MQTT autentifikace** podpora

## Instalace

### 1. Příprava souborů
```bash
# Zkopírujte všechny soubory na OpenWRT router
scp *.py *.init *.sh *.uci root@192.168.1.1:/tmp/
```

### 2. Spuštění instalace
```bash
# Připojte se na router
ssh root@192.168.1.1

# Spusťte instalaci
cd /tmp
chmod +x install.sh
./install.sh
```

### 3. Konfigurace

Veškerá konfigurace se provádí přes UCI systém:

```bash
# Zobrazení současné konfigurace
uci show openwrt-reporter

# MQTT nastavení
uci set openwrt-reporter.mqtt.host='192.168.1.100'
uci set openwrt-reporter.mqtt.username='homeassistant'
uci set openwrt-reporter.mqtt.password='secret123'

# Povolení verbose loggingu
uci set openwrt-reporter.global.verbose=1

# Úprava rozhraní
uci set openwrt-reporter.wan.label='Hlavní ISP'
uci set openwrt-reporter.wanb.label='Záložní LTE'

# Uložení a restart
uci commit openwrt-reporter
/etc/init.d/openwrt-reporter restart
```

## Správa služby

```bash
# Spuštění
/etc/init.d/openwrt-reporter start

# Zastavení
/etc/init.d/openwrt-reporter stop

# Restart
/etc/init.d/openwrt-reporter restart

# Status
/etc/init.d/openwrt-reporter status

# Logy
logread | grep openwrt-reporter

# Povolení autostartu
/etc/init.d/openwrt-reporter enable

# Zákaz autostartu
/etc/init.d/openwrt-reporter disable
```

## Verbose mód

```bash
# Povolení verbose módu přes UCI
uci set openwrt-reporter.global.verbose=1
uci commit openwrt-reporter
/etc/init.d/openwrt-reporter restart

# Nebo dočasně při spuštění
python3 /usr/bin/openwrt-reporter.py --verbose
```

## Testování konfigurace

```bash
# Zobrazení aplikované konfigurace bez spuštění služby
python3 /usr/bin/openwrt-reporter.py --config

# Kombinace s verbose pro detailní výstup
python3 /usr/bin/openwrt-reporter.py --config --verbose
```

## MQTT Topiky

### Dostupnost
- `openwrt/{interface}/availability` - online/offline

### Binary senzory
- `openwrt/{interface}/status` - MWAN stav (online/offline)
- `openwrt/{interface}/link_status` - Link stav (up/down)

### Senzory
- `openwrt/{interface}/ipv4` - IPv4 adresa
- `openwrt/{interface}/ipv6` - IPv6 adresa
- `openwrt/{interface}/rx_bytes` - Přijaté byty
- `openwrt/{interface}/tx_bytes` - Odeslané byty
- `openwrt/{interface}/rx_rate` - Rychlost příjmu (B/s)
- `openwrt/{interface}/tx_rate` - Rychlost odesílání (B/s)

### MWAN3
- `openwrt/mwan3/active` - Aktivní WAN interface
- `openwrt/mwan3/active_name` - Název aktivního WAN

## Home Assistant

Entity se automaticky objeví v Home Assistant díky MQTT Discovery. Najdete je pod:
- **StarNet Interface** (wan)
- **Vodafone LTE Interface** (wanb) 
- **MWAN3 Load Balancer**

## Požadavky

- OpenWRT router s Python3
- MWAN3 balíček
- MQTT broker
- Home Assistant (volitelné)

## Troubleshooting

### Script se nespustí
```bash
# Zkontrolujte konfiguraci
python3 /usr/bin/openwrt-reporter.py --config

# Zkontrolujte Python3
python3 --version

# Zkontrolujte paho-mqtt
python3 -c "import paho.mqtt"

# Ruční spuštění pro debug
python3 /usr/bin/openwrt-reporter.py --verbose
```

### MQTT problémy
```bash
# Test MQTT připojení
opkg install mosquitto-client
mosquitto_pub -h mqtt.lan -t test -m "hello"

# Test s autentifikací
mosquitto_pub -h mqtt.lan -u username -P password -t test -m "hello"
```

### UCI konfigurace problémy
```bash
# Zobrazení konfigurace
uci show openwrt-reporter

# Reset na výchozí
rm /etc/config/openwrt-reporter
cp /tmp/openwrt-reporter.uci /etc/config/openwrt-reporter
/etc/init.d/openwrt-reporter restart

# Kontrola UCI syntaxe
uci export openwrt-reporter
```

### MWAN3 nedetekován
```bash
# Zkontrolujte MWAN3
mwan3 status

# Instalace MWAN3 (pokud chybí)
opkg install mwan3
```

## Konfigurace pro jiné routery

Vše se konfiguruje přes UCI - žádné úpravy kódu nejsou potřeba:

```bash
# Přidání vlastních rozhraní
uci add openwrt-reporter interface
uci set openwrt-reporter.@interface[-1].name='pppoe-wan'
uci set openwrt-reporter.@interface[-1].label='PPPoE Connection'

# Konfigurace vlastního MQTT brokeru
uci set openwrt-reporter.mqtt.host='192.168.100.50'
uci set openwrt-reporter.mqtt.port=1883

# Vlastní MQTT topiky
uci set openwrt-reporter.mqtt.base_topic='router1'

uci commit openwrt-reporter
```

## Soubory

- `openwrt-reporter.py` - Hlavní script
- `openwrt-reporter.init` - Init.d služba
- `openwrt-reporter.uci` - UCI konfigurace
- `install.sh` - Instalační script
- `uninstall.sh` - Odinstalační script
- `update.sh` - Update script (lokální soubory)
- `update-from-github.sh` - Update z GitHubu
- `check-version.sh` - Kontrola verze a stavu
- `README.md` - Dokumentace

## Aktualizace

### Lokální update (máte soubory)
```bash
# Zkopírujte nové soubory na router
scp *.py *.init *.sh *.uci root@192.168.1.1:/tmp/

# Spusťte update
ssh root@192.168.1.1
cd /tmp
chmod +x update.sh
./update.sh
```

### Automatický update z GitHubu
```bash
# Stáhne a nainstaluje nejnovější verzi
ssh root@192.168.1.1
wget -O /tmp/update-github.sh https://raw.githubusercontent.com/filipek92/OpenWRT-reporter/main/update-from-github.sh
chmod +x /tmp/update-github.sh
/tmp/update-github.sh
```

### Kontrola verze
```bash
# Zobrazí informace o nainstalované verzi
./check-version.sh
```

## Makefile (pro vývojáře)

Pro snadnou správu z vývojového prostředí:

```bash
# Zobrazí nápovědu
make help

# Nasazení a instalace
make install ROUTER_IP=192.168.1.1

# Update existující instalace
make update ROUTER_IP=192.168.1.1

# Kontrola stavu
make status ROUTER_IP=192.168.1.1

# Zobrazení logů
make logs ROUTER_IP=192.168.1.1

# Restart služby
make restart ROUTER_IP=192.168.1.1
```

## Odinstalace

```bash
# Spuštění odinstalace
cd /tmp
chmod +x uninstall.sh
./uninstall.sh

# Nebo manuálně
/etc/init.d/openwrt-reporter stop
/etc/init.d/openwrt-reporter disable
rm -f /etc/init.d/openwrt-reporter
rm -f /usr/bin/openwrt-reporter.py
rm -f /etc/config/openwrt-reporter
```

## UCI Konfigurace

### Globální nastavení
```bash
# Povolení/zakázání služby
uci set openwrt-reporter.global.enabled=1

# Verbose logging
uci set openwrt-reporter.global.verbose=1
```

### MQTT nastavení
```bash
# MQTT broker
uci set openwrt-reporter.mqtt.host='mqtt.lan'
uci set openwrt-reporter.mqtt.port=1883

# Autentifikace (volitelné)
uci set openwrt-reporter.mqtt.username='user'
uci set openwrt-reporter.mqtt.password='pass'

# MQTT topiky
uci set openwrt-reporter.mqtt.base_topic='openwrt'
uci set openwrt-reporter.mqtt.discovery_prefix='homeassistant'
```

### Správa rozhraní
```bash
# Přidání nového rozhraní
uci add openwrt-reporter interface
uci set openwrt-reporter.@interface[-1].name='wan3'
uci set openwrt-reporter.@interface[-1].type='base'
uci set openwrt-reporter.@interface[-1].label='Třetí WAN'
uci set openwrt-reporter.@interface[-1].monitor_ipv4=1
uci set openwrt-reporter.@interface[-1].monitor_ipv6=0

# Zakázání rozhraní
uci set openwrt-reporter.wan6.enabled=0

# Změna typu rozhraní
uci set openwrt-reporter.wan6.type='virtual'

# Uložení změn
uci commit openwrt-reporter
/etc/init.d/openwrt-reporter restart
```
