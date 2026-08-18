# ============================================================
# Cross-platform Makefile for gui-yt-dlp
# Supports:
#   - Windows
#   - Linux
#   - macOS
#
# Usage:
#   make run
#   make test
#   make lint
#   make format
#   make check
#   make build
#   make clean
#
# Debian only:
#   make deb
#   make install
#   make uninstall
# ============================================================

VENV := .venv
APP_NAME := gui-yt-dlp


# ============================================================
# Platform detection
# ============================================================

ifeq ($(OS),Windows_NT)

PLATFORM := Windows

PYTHON_SYSTEM := python

PYTHON := $(VENV)\Scripts\python.exe
PIP := $(PYTHON) -m pip

PYTEST := $(PYTHON) -m pytest
RUFF := $(PYTHON) -m ruff
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort

PYINSTALLER := $(PYTHON) -m PyInstaller

VENV_MARKER := $(VENV)\Scripts\python.exe

else

UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
PLATFORM := macOS
else
PLATFORM := Linux
endif

PYTHON_SYSTEM := python3

PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip

PYTEST := $(PYTHON) -m pytest
RUFF := $(PYTHON) -m ruff
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort

PYINSTALLER := $(PYTHON) -m PyInstaller

VENV_MARKER := $(VENV)/bin/python

endif


# ============================================================
# Project version
# ============================================================

VERSION := $(shell $(PYTHON_SYSTEM) -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || echo 1.0.3)


# ============================================================
# Phony targets
# ============================================================

.PHONY: \
	all \
	info \
	venv \
	run \
	test \
	lint \
	format \
	check \
	build \
	exe \
	deb \
	install \
	uninstall \
	clean


# ============================================================
# Default
# ============================================================

all: run


# ============================================================
# Show environment information
# ============================================================

info:
	@echo Platform: $(PLATFORM)
	@echo System Python: $(PYTHON_SYSTEM)
	@echo Virtual Environment: $(VENV)
	@echo Python: $(PYTHON)
	@echo Version: $(VERSION)


# ============================================================
# Create virtual environment
# ============================================================

venv: $(VENV_MARKER)


$(VENV_MARKER): pyproject.toml

	@echo Creating virtual environment...
	$(PYTHON_SYSTEM) -m venv $(VENV)

	@echo Installing dependencies...
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

	@echo Virtual environment ready.


# ============================================================
# Run application
# ============================================================

run: venv

	@echo Launching $(APP_NAME)...
	$(PYTHON) -m src.main


# ============================================================
# Run tests
# ============================================================

test: venv

	@echo Running test suite...

ifeq ($(OS),Windows_NT)
	set QT_QPA_PLATFORM=offscreen && $(PYTEST) tests/
else
	QT_QPA_PLATFORM=offscreen $(PYTEST) tests/
endif


# ============================================================
# Lint
# ============================================================

lint: venv

	@echo Running linter...
	$(RUFF) check src tests


# ============================================================
# Format
# ============================================================

format: venv

	@echo Formatting code...

	$(BLACK) src tests
	$(ISORT) src tests


# ============================================================
# Run checks
# ============================================================

check: lint test


# ============================================================
# Build standalone application
# ============================================================

build: venv

	@echo Building $(APP_NAME) for $(PLATFORM)...

	$(PYINSTALLER) --clean --noconfirm gui-yt-dlp.spec

	@echo.
	@echo ========================================
	@echo Build completed successfully.
	@echo ========================================


exe: build


# ============================================================
# Create Debian package
# Linux only
# ============================================================

deb: build

ifeq ($(PLATFORM),Linux)

	@echo Creating Debian package directories...

	mkdir -p build/deb/DEBIAN
	mkdir -p build/deb/usr/bin
	mkdir -p build/deb/usr/share/applications
	mkdir -p build/deb/usr/share/pixmaps

	@echo Copying application...

	cp dist/$(APP_NAME) \
		build/deb/usr/bin/$(APP_NAME)

	chmod +x \
		build/deb/usr/bin/$(APP_NAME)

	cp src/gui/assets/logo.jpeg \
		build/deb/usr/share/pixmaps/$(APP_NAME).jpeg


	@echo Writing Debian control file...

	@echo Package: $(APP_NAME) \
		> build/deb/DEBIAN/control

	@echo Version: $(VERSION) \
		>> build/deb/DEBIAN/control

	@echo Section: utils \
		>> build/deb/DEBIAN/control

	@echo Priority: optional \
		>> build/deb/DEBIAN/control

	@echo Architecture: amd64 \
		>> build/deb/DEBIAN/control

	@echo Maintainer: Sudhanshu Singh \
		>> build/deb/DEBIAN/control

	@echo Description: A modern PySide6 desktop GUI frontend for yt-dlp \
		>> build/deb/DEBIAN/control


	@echo Writing desktop entry...

	@echo [Desktop Entry] \
		> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo Version=1.0 \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo Type=Application \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo Name=yt-dlp Flow \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo Comment=Modern PySide6 GUI frontend for yt-dlp \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo Exec=$(APP_NAME) \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo Icon=$(APP_NAME) \
		>> build/deb/usr/share/pixmaps/$(APP_NAME).jpeg

	@echo Categories=Network\;Video\;AudioVideo\;Player\; \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo Terminal=false \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop

	@echo StartupNotify=true \
		>> build/deb/usr/share/applications/$(APP_NAME).desktop


	@echo Building Debian package...

	dpkg-deb --build \
		build/deb \
		$(APP_NAME)_$(VERSION)_amd64.deb

	@echo Debian package created:
	@echo $(APP_NAME)_$(VERSION)_amd64.deb

else

	@echo Error: Debian packages can only be built on Linux.
	@exit 1

endif


# ============================================================
# Install Debian package
# ============================================================

install:

ifeq ($(PLATFORM),Linux)

	@if [ -f "$(APP_NAME)_$(VERSION)_amd64.deb" ]; then \
		echo Installing Debian package...; \
		sudo dpkg -i "$(APP_NAME)_$(VERSION)_amd64.deb" || \
		sudo apt-get install -f; \
	else \
		echo Debian package not found.; \
		echo Run 'make deb' first.; \
		exit 1; \
	fi

else

	@echo Install is only supported for Debian-based Linux.

endif


# ============================================================
# Uninstall Debian package
# ============================================================

uninstall:

ifeq ($(PLATFORM),Linux)

	@echo Uninstalling $(APP_NAME)...

	sudo dpkg -r $(APP_NAME) || \
	sudo apt-get remove $(APP_NAME)

else

	@echo Uninstall is only supported for Debian-based Linux.

endif


# ============================================================
# Clean generated files
# ============================================================

clean:

	@echo Cleaning generated files...

ifeq ($(OS),Windows_NT)

	@if exist "$(VENV)" rmdir /s /q "$(VENV)"
	@if exist "build" rmdir /s /q "build"
	@if exist "dist" rmdir /s /q "dist"

	@if exist "__pycache__" rmdir /s /q "__pycache__"
	@if exist ".pytest_cache" rmdir /s /q ".pytest_cache"
	@if exist ".mypy_cache" rmdir /s /q ".mypy_cache"

else

	rm -rf $(VENV)
	rm -rf build
	rm -rf dist

	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf src/*/__pycache__

	rm -rf .pytest_cache
	rm -rf .mypy_cache

	rm -f *.spec.bak
	rm -f *.deb

endif

	@echo Clean completed.