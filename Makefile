# OpenWRT Reporter Makefile
# Simple commands for development and deployment

ROUTER_IP ?= 192.168.1.1
ROUTER_USER ?= root

# Default target
.PHONY: help
help:
	@echo "OpenWRT Reporter Management"
	@echo ""
	@echo "Available targets:"
	@echo "  deploy       - Deploy files to router (set ROUTER_IP=x.x.x.x)"
	@echo "  install      - Deploy and install on router"
	@echo "  update       - Deploy and update on router"
	@echo "  status       - Check status on router"
	@echo "  logs         - Show logs from router"
	@echo "  config       - Show configuration from router"
	@echo "  start        - Start service on router"
	@echo "  stop         - Stop service on router"
	@echo "  restart      - Restart service on router"
	@echo "  uninstall    - Uninstall from router"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy ROUTER_IP=192.168.1.1"
	@echo "  make install ROUTER_IP=10.0.0.1"

.PHONY: deploy
deploy:
	@echo "Deploying files to $(ROUTER_USER)@$(ROUTER_IP):/tmp/"
	scp *.py *.init *.sh *.uci *.md $(ROUTER_USER)@$(ROUTER_IP):/tmp/

.PHONY: install
install: deploy
	@echo "Installing on router..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "cd /tmp && chmod +x install.sh && ./install.sh"

.PHONY: update
update: deploy
	@echo "Updating on router..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "cd /tmp && chmod +x update.sh && ./update.sh"

.PHONY: status
status:
	@echo "Checking status on router..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "/etc/init.d/openwrt-reporter status && echo '' && python3 /usr/bin/openwrt-reporter.py --config"

.PHONY: logs
logs:
	@echo "Showing logs from router..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "logread | grep openwrt-reporter | tail -20"

.PHONY: config
config:
	@echo "Showing configuration..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "python3 /usr/bin/openwrt-reporter.py --config"

.PHONY: start
start:
	@echo "Starting service..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "/etc/init.d/openwrt-reporter start"

.PHONY: stop
stop:
	@echo "Stopping service..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "/etc/init.d/openwrt-reporter stop"

.PHONY: restart
restart:
	@echo "Restarting service..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "/etc/init.d/openwrt-reporter restart"

.PHONY: uninstall
uninstall: deploy
	@echo "Uninstalling from router..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "cd /tmp && chmod +x uninstall.sh && ./uninstall.sh"

.PHONY: check-version
check-version: deploy
	@echo "Checking version..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "cd /tmp && chmod +x check-version.sh && ./check-version.sh"

.PHONY: clean
clean:
	@echo "Cleaning temporary files..."
	ssh $(ROUTER_USER)@$(ROUTER_IP) "rm -f /tmp/openwrt-reporter* /tmp/install.sh /tmp/uninstall.sh /tmp/update*.sh /tmp/check-version.sh"
