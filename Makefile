# Makefile for gui-yt-dlp

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
APP_NAME = gui-yt-dlp
VERSION = 1.0.0

.PHONY: all venv run build deb install uninstall clean exe

all: run

# 1. Setup virtual environment and install requirements
venv: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV)
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate

# 2. Run the application
run: venv
	@echo "Launching $(APP_NAME)..."
	$(PYTHON) -m src.main

# 3. Build standalone single-file binary using PyInstaller
build: venv
	@echo "Installing PyInstaller..."
	$(PIP) install pyinstaller
	@echo "Compiling standalone binary..."
	$(VENV)/bin/pyinstaller --clean gui-yt-dlp.spec
	@echo "Compilation completed: dist/$(APP_NAME)"

# Target to compile standalone executable (alias for build)
exe: build

# 4. Package standalone binary into a Debian (.deb) package
deb: build
	@echo "Creating Debian package directories..."
	mkdir -p build/deb/DEBIAN
	mkdir -p build/deb/usr/bin
	mkdir -p build/deb/usr/share/applications
	mkdir -p build/deb/usr/share/pixmaps
	
	@echo "Copying binary and logo asset to Debian build root..."
	cp dist/$(APP_NAME) build/deb/usr/bin/$(APP_NAME)
	chmod +x build/deb/usr/bin/$(APP_NAME)
	cp src/gui/assets/logo.png build/deb/usr/share/pixmaps/$(APP_NAME).png
	
	@echo "Writing Debian control configuration..."
	@echo "Package: $(APP_NAME)" > build/deb/DEBIAN/control
	@echo "Version: $(VERSION)" >> build/deb/DEBIAN/control
	@echo "Section: utils" >> build/deb/DEBIAN/control
	@echo "Priority: optional" >> build/deb/DEBIAN/control
	@echo "Architecture: amd64" >> build/deb/DEBIAN/control
	@echo "Maintainer: Sudhanshu Singh" >> build/deb/DEBIAN/control
	@echo "Description: A modern PySide6 desktop GUI frontend for yt-dlp" >> build/deb/DEBIAN/control
	@echo " yt-dlp Flow provides a modern, fast, responsive dark-themed" >> build/deb/DEBIAN/control
	@echo " desktop interface for downloading videos, playlists, extracting" >> build/deb/DEBIAN/control
	@echo " audio as MP3, and embedding metadata and subtitles." >> build/deb/DEBIAN/control
	
	@echo "Writing desktop menu shortcut entry..."
	@echo "[Desktop Entry]" > build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Version=1.0" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Type=Application" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Name=yt-dlp Flow" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Comment=Modern PySide6 GUI frontend for yt-dlp" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Exec=$(APP_NAME)" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Icon=$(APP_NAME)" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Categories=Network;Video;AudioVideo;Player;FLOSS;" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "Terminal=false" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	@echo "StartupNotify=true" >> build/deb/usr/share/applications/$(APP_NAME).desktop
	
	@echo "Building Debian package..."
	dpkg-deb --build build/deb $(APP_NAME)_$(VERSION)_amd64.deb
	@echo "Debian package created: $(APP_NAME)_$(VERSION)_amd64.deb"

# 5. Direct installation of Debian package on host
install:
	@if [ -f $(APP_NAME)_$(VERSION)_amd64.deb ]; then \
		echo "Installing Debian package..."; \
		sudo dpkg -i $(APP_NAME)_$(VERSION)_amd64.deb || sudo apt-get install -f; \
	else \
		echo "Debian package not found! Please run 'make deb' first."; \
		exit 1; \
	fi

uninstall:
	@echo "Uninstalling $(APP_NAME)..."
	sudo dpkg -r $(APP_NAME) || sudo apt-get remove $(APP_NAME)

# 6. Clean build and cache files
clean:
	@echo "Cleaning up temporary files..."
	rm -rf build/ dist/ __pycache__/ src/__pycache__/ src/*/__pycache__/ *.spec.bak
	rm -rf *.deb
	@echo "Clean completed."
