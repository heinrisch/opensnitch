.DEFAULT_GOAL := all
PYTHON ?= python3
BUILD_DIR := $(CURDIR)/.build
BUILD_PYTHON := $(BUILD_DIR)/venv/bin/python
SUDO ?= sudo

.PHONY: all build update install-local restart-local build-tools protocol opensnitch_daemon gui clean

all: build

# Build unprivileged; only installation needs sudo. No system Python changes.
build: opensnitch_daemon gui

build-tools:
	$(PYTHON) -m venv $(BUILD_DIR)/venv
	$(BUILD_PYTHON) -m pip install --upgrade pip wheel
	$(BUILD_PYTHON) -m pip install -r ui/requirements.txt
	GOBIN=$(BUILD_DIR)/bin go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.26.0
	GOBIN=$(BUILD_DIR)/bin go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.1.0

# Run as your desktop user: make update builds, replaces, and switches versions.
update: build
	bash utils/restart-local-ui.sh --check
	$(SUDO) bash utils/install-local.sh "$(BUILD_DIR)"
	bash utils/restart-local-ui.sh

install-local: build
	$(SUDO) bash utils/install-local.sh "$(BUILD_DIR)"

restart-local:
	bash utils/restart-local-ui.sh --check
	$(SUDO) systemctl restart opensnitchd.service
	bash utils/restart-local-ui.sh

install:
	@cd daemon && make install
	@cd ui && make install

protocol: build-tools
	PATH="$(BUILD_DIR)/bin:$$PATH" $(MAKE) -C proto PYTHON="$(BUILD_PYTHON)"

opensnitch_daemon: protocol
	cd daemon && go build -o opensnitchd .

gui: protocol
	$(BUILD_PYTHON) -m pip wheel --wheel-dir $(BUILD_DIR)/wheels -r ui/requirements.txt ./ui

clean:
	@cd daemon && make clean
	@cd proto && make clean
	@cd ui && make clean

run:
	cd ui && pip3 install --upgrade . && cd ..
	opensnitch-ui --socket unix:///tmp/osui.sock &
	./daemon/opensnitchd -rules-path /etc/opensnitchd/rules -ui-socket unix:///tmp/osui.sock -cpu-profile cpu.profile -mem-profile mem.profile

test:
	clear
	make clean
	clear
	mkdir -p rules
	make
	clear
	make run

adblocker:
	clear
	make clean
	clear
	make
	clear
	python make_ads_rules.py
	clear
	cd ui && pip3 install --upgrade . && cd ..
	opensnitch-ui --socket unix:///tmp/osui.sock &
	./daemon/opensnitchd -rules-path /etc/opensnitchd/rules -ui-socket unix:///tmp/osui.sock


