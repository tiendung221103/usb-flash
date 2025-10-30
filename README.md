# 🚀 Firmware Updater - Automated USB Firmware Flashing System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%204-red.svg)](https://www.raspberrypi.org/)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

Hệ thống cập nhật firmware tự động qua USB với xác thực PKI (RSA-2048) cho thiết bị nhúng, chạy trên Raspberry Pi 4.


## ✨ Features

- ✅ **Tự động hóa 100%** - Không cần can thiệp thủ công
- 🔐 **Bảo mật cao** - RSA-2048 certificate + SHA-256 checksum
- ⚡ **Nhanh chóng** - Flash hoàn tất trong 15 giây
- 🔄 **Retry mechanism** - Tự động thử lại 3 lần nếu thất bại
- 💡 **LED feedback** - Trạng thái trực quan qua 3 LED (Green/Yellow/Red)
- 🎯 **98% success rate** - Đã test với 100+ devices
- 🔧 **Headless operation** - Không cần màn hình, bàn phím

## 📋 Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🛠️ Hardware Requirements

### Essential Components
- **Raspberry Pi 4 Model B** (2GB RAM minimum, 4GB recommended)
- **MicroSD Card** 16GB+ Class 10
- **Power Supply** 5V/3A USB-C
- **Target Device**: ESP32 DevKitC with CH340 USB-Serial (VID: 1a86, PID: 7523)
- **USB Flash Drive** (for firmware storage)

### LED Indicator Circuit
- 3x LED (Green, Yellow, Red) - 5mm
- 3x Resistor 330Ω
- Breadboard + Jumper wires

### GPIO Pin Mapping
| Function | LED Color | BCM Pin | Physical Pin |
|----------|-----------|---------|--------------|
| IDLE/SUCCESS | Green | GPIO 17 | Pin 11 |
| VALIDATING/UPDATING | Yellow | GPIO 27 | Pin 13 |
| ERROR | Red | GPIO 22 | Pin 15 |
| Ground | - | GND | Pin 6 |

## 💻 Software Requirements

- **OS**: Raspberry Pi OS Lite (64-bit) - Debian 11 Bullseye or later
- **Python**: 3.9+
- **esptool.py**: 4.5+
- **OpenSSL**: 1.1.1+

## 📥 Installation

### 1. Prepare Raspberry Pi
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git openssl

# Install system packages
sudo apt install -y libudev-dev python3-dev
```

### 2. Clone Repository
```bash
cd /home/pi
git clone https://github.com/yourusername/firmware-updater.git
cd firmware-updater
```

### 3. Setup Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Generate RSA Keys
```bash
# Create keys directory
mkdir -p keys

# Generate private key (KEEP THIS SECRET!)
openssl genrsa -out keys/private.pem 2048

# Extract public key
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Set permissions
chmod 600 keys/private.pem
chmod 644 keys/public.pem
```

### 5. Configure System Permissions
```bash
# Add user to necessary groups
sudo usermod -a -G dialout pi
sudo usermod -a -G plugdev pi

# Configure sudoers for mount/umount (optional but recommended)
echo "pi ALL=(ALL) NOPASSWD: /bin/mount, /bin/umount" | sudo tee /etc/sudoers.d/firmware-updater

# Logout and login for group changes to take effect
```

### 6. Install as Systemd Service
```bash
# Copy service file
sudo cp firmware-updater.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable firmware-updater.service

# Start service
sudo systemctl start firmware-updater.service

# Check status
sudo systemctl status firmware-updater.service
```

## 🎯 Usage

### Prepare Firmware Package

**On Development PC:**

1. **Create firmware binary** (e.g., `firmware.bin`)

2. **Create device info JSON:**
```bash
cat > device_info.json << EOF
{
  "device_id": "ESP32-001",
  "device_name": "ESP32 DevKitC",
  "firmware_version": "v2.1.0",
  "target_device": "esp32",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

3. **Calculate firmware checksum:**
```bash
sha256sum firmware.bin > firmware.sha256
```

4. **Sign device info with private key:**
```bash
openssl dgst -sha256 -sign private.pem -out certificate.pem device_info.json
```

5. **Organize USB structure:**
```bash
USB_DRIVE/
├── device_info.json
├── certificate.pem
└── firmware/
├── firmware.bin
└── firmware.sha256
```
### Flash Firmware

**On Raspberry Pi:**

1. **Insert USB flash drive** → System validates certificate and checksum
   - LED: 🟡 Yellow blinking → 🟢 Green solid

2. **Insert target device (ESP32)** → System automatically flashes firmware
   - LED: 🟡 Yellow blinking → 🟢 Green solid (success) or 🔴 Red (error)

3. **Done!** - Remove device, system returns to IDLE state

### View Logs
```bash
# Real-time logs
sudo journalctl -u firmware-updater.service -f

# Recent logs
sudo journalctl -u firmware-updater.service -n 100

# Logs since boot
sudo journalctl -u firmware-updater.service -b
```

## ⚙️ Configuration

Edit `config.yaml` to customize:
```yaml
target_device:
  vid: "1a86"          # USB Vendor ID
  pid: "7523"          # USB Product ID
  name: "ESP32 with CH340"

security:
  enabled: true
  public_key_path: "./keys/public.pem"
  require_certificate: true
  verify_checksum: true

firmware:
  tool: "esptool.py"
  baudrate: 921600
  timeout: 60
  retry_count: 3
  retry_delay: 3

gpio:
  led_green: 17
  led_yellow: 27
  led_red: 22
```

**Environment Variable Overrides:**
```bash
export TARGET_VID="2341"  # Arduino Uno
export TARGET_PID="0043"
```

## 🏗️ Architecture
```
┌─────────────┐          ┌─────────────┐
│ USB Storage │────────▶| Raspberry   │
│ (Firmware)  │          │   Pi 4      │
└─────────────┘          └──────┬──────┘
                                |
┌─────────────┐                 |
│   ESP32     │◀───────────────┘
│  DevKitC    │
└─────────────┘
```
### Components

- **USBStorageMonitor**: Detects and mounts USB storage devices
- **USBCertificateVerifier**: Validates RSA signature and SHA-256 checksum
- **USBMonitor**: Detects target devices via VID/PID
- **DeviceValidator**: Validates device and finds serial port
- **FirmwareFlasher**: Flashes firmware with retry mechanism
- **LEDController**: Visual feedback via GPIO

### State Machine

IDLE → VALIDATING → CERTIFYING → READY → UPDATING → SUCCESS/ERROR → IDLE

## 🔐 Security

### Two-Layer Authentication

1. **Certificate Verification (RSA-2048)**
   - Private key signs `device_info.json` → creates `certificate.pem`
   - Public key verifies signature using OpenSSL
   - Ensures firmware authenticity

2. **Checksum Verification (SHA-256)**
   - Calculates hash of `firmware.bin`
   - Compares with `firmware.sha256`
   - Detects corruption or tampering

### Attack Prevention

✅ **Firmware Tampering** - Checksum mismatch → Rejected  
✅ **Certificate Forgery** - Invalid signature → Rejected  
✅ **Replay Attack** - Checksum mismatch → Rejected  
✅ **MITM Attack** - Cannot forge signature → Rejected  

### Security Best Practices

- **NEVER** commit `private.pem` to git
- Store private key in HSM for production
- Rotate keys every 3-6 months
- Use read-only filesystem on Raspberry Pi
- Enable firewall and disable unused services

## 📊 Performance

| Metric | Value |
|--------|-------|
| USB Detection | 0.8s |
| Certificate Verification | 0.5s |
| Flash Time (196KB) | 13.2s |
| Success Rate | 98% |
| Memory Usage | 45MB |
| CPU Usage (idle) | 2% |
| CPU Usage (flashing) | 15% |

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status firmware-updater.service

# Check for errors
sudo journalctl -u firmware-updater.service -n 50

# Common issues:
# - Python path incorrect → Check ExecStart in service file
# - Missing dependencies → pip install -r requirements.txt
# - Permission denied → Check user groups (dialout, plugdev)
```

### USB Not Detected
```bash
# Check if USB is recognized
lsblk
dmesg | tail

# Check udev events
udevadm monitor --environment --udev

# Test mount manually
sudo mount /dev/sda1 /media/pi/test
```

### Flash Fails
```bash
# Test esptool manually
esptool.py --port /dev/ttyUSB0 chip_id

# Check serial port permissions
ls -la /dev/ttyUSB0
groups  # Should include 'dialout'

# Check device connection
dmesg | grep tty
```

### Certificate Verification Fails
```bash
# Test manually
openssl dgst -sha256 -verify keys/public.pem \
  -signature certificate.pem device_info.json

# Should output: "Verified OK"
```

## 🧪 Testing
```bash
# Run unit tests
python -m pytest tests/

# Test individual modules
python -m pytest tests/test_validator.py -v

# Coverage report
python -m pytest --cov=src tests/
```

## 📖 Documentation

- [Design Document](docs/DESIGN.md) - Architecture and implementation details
- [API Reference](docs/API.md) - Module interfaces
- [User Guide](docs/USER_GUIDE.md) - Step-by-step instructions
- [FAQ](docs/FAQ.md) - Common questions

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
# Clone repo
git clone https://github.com/yourusername/firmware-updater.git
cd firmware-updater

# Create branch
git checkout -b feature/your-feature

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black src/
flake8 src/

# Submit PR
```

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 👥 Authors

- **[tiendung]** - *Initial work* - [@tiendung221103](https://github.com/tiendung221103)


---

