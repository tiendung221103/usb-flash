"""Main application - Secure version with USB firmware source."""

import sys
import signal
import time
from queue import Queue, Empty

from src.config import Config
from src.led_controller import LEDController
from src.usb_monitor import USBMonitor
from src.usb_storage_monitor import USBStorageMonitor
from src.device_validator import DeviceValidator
from src.usb_certificate_verifier import USBCertificateVerifier
from src.firmware_flasher import FirmwareFlasher

# Global state
shutdown_requested = False
current_usb_storage = None
current_firmware_path = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    print("\n[Main] Shutdown signal received...")
    shutdown_requested = True

def main():
    """Main application function."""
    global shutdown_requested, current_usb_storage, current_firmware_path
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*60)
    print("  SECURE FIRMWARE UPDATER")
    print("  with USB Certificate Verification")
    print("="*60)
    
    try:
        # 1. Load configuration
        print("\n[Main] Loading configuration...")
        config = Config()
        
        # 2. Initialize components
        print("\n[Main] Initializing components...")
        
        # Event queues
        device_event_queue = Queue(maxsize=32)
        storage_event_queue = Queue(maxsize=32)
        
        # LED Controller
        led = LEDController(
            pin_green=config['gpio']['led_green'],
            pin_yellow=config['gpio']['led_yellow'],
            pin_red=config['gpio']['led_red']
        )
        led.show_idle()
        
        # USB Certificate Verifier
        cert_verifier = USBCertificateVerifier(
            public_key_path=config['security']['public_key_path'],
            config=config.config
        )
        
        # Device Validator (for target device - ESP32)
        device_validator = DeviceValidator(
            target_vid=config['target_device']['vid'],
            target_pid=config['target_device']['pid']
        )
        
        # Firmware Flasher (will use dynamic firmware path from USB)
        flasher = FirmwareFlasher(config.config)
        
        # USB Monitors
        device_monitor = USBMonitor(device_event_queue)
        storage_monitor = USBStorageMonitor(
            storage_event_queue,
            mount_base=config['usb_storage']['mount_base']
        )
        
        # Start monitoring
        device_monitor.start_monitoring()
        storage_monitor.start_monitoring()
        
        print("\n" + "="*60)
        print("  SYSTEM READY")
        print("="*60)
        print("\nSecurity Status:")
        print(f"  Certificate Verification: {'ENABLED' if config['security']['require_certificate'] else 'DISABLED'}")
        print(f"  Checksum Verification: {'ENABLED' if config['security']['verify_checksum'] else 'DISABLED'}")
        print("\nTarget Device:")
        print(f"  VID: {config['target_device']['vid']}")
        print(f"  PID: {config['target_device']['pid']}")
        print(f"  Name: {config['target_device']['name']}")
        print("\nWaiting for USB storage and target device...")
        print("Press Ctrl+C to exit\n")
        
        # Main event loop
        while not shutdown_requested:
            try:
                # Check storage events (higher priority)
                try:
                    event_type, data = storage_event_queue.get(timeout=0.1)
                    
                    if event_type == 'usb_storage_mounted':
                        handle_storage_mounted(data, cert_verifier, led)
                    
                    elif event_type == 'usb_storage_removed':
                        handle_storage_removed(data, storage_monitor, led)
                    
                    storage_event_queue.task_done()
                    continue
                    
                except Empty:
                    pass
                
                # Check device events
                try:
                    event_type, device = device_event_queue.get(timeout=0.1)
                    
                    if event_type == 'device_connected':
                        handle_device_connected(
                            device,
                            device_validator,
                            flasher,
                            led
                        )
                    
                    elif event_type == 'device_disconnected':
                        print("[Main] Target device disconnected")
                    
                    device_event_queue.task_done()
                    
                except Empty:
                    pass
                
            except Exception as e:
                print(f"[Main] ERROR in event loop: {e}")
                import traceback
                traceback.print_exc()
    
    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user")
    
    except Exception as e:
        print(f"\n[Main] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup
        print("\n[Main] Shutting down...")
        
        try:
            device_monitor.stop_monitoring()
            storage_monitor.stop_monitoring()
            
            # Unmount USB storage if still mounted
            if current_usb_storage:
                print(f"[Main] Unmounting {current_usb_storage.mount_point}...")
                storage_monitor.unmount_device(current_usb_storage.mount_point)
            
            led.cleanup()
        except Exception as e:
            print(f"[Main] Cleanup error: {e}")
        
        print("[Main] Shutdown complete")
    
    return 0

def handle_storage_mounted(storage, cert_verifier, led):
    """Handle USB storage mounted event.
    
    Args:
        storage: USBStorage object
        cert_verifier: USBCertificateVerifier instance
        led: LEDController instance
    """
    global current_usb_storage, current_firmware_path
    
    print(f"\n{'='*60}")
    print(f"[Main] USB STORAGE MOUNTED")
    print(f"{'='*60}")
    print(f"Device: {storage.vendor} {storage.model}")
    print(f"Mount point: {storage.mount_point}")
    
    # Show validating state
    led.show_validating()
    
    # Verify USB certificate and firmware
    result = cert_verifier.verify_usb_device(storage.mount_point)
    
    if result.success:
        print(f"\n[Main] ✓ USB VERIFIED SUCCESSFULLY")
        print(f"[Main] Firmware ready: {result.firmware_path}")
        print(f"[Main] Device: {result.device_info.device_name}")
        print(f"[Main] Version: {result.device_info.firmware_version}")
        
        # Store verified USB info
        current_usb_storage = storage
        current_firmware_path = result.firmware_path
        
        # Show success - ready to flash
        led.show_success()
        time.sleep(2)
        led.show_idle()
        
        print(f"\n{'='*60}")
        print(f"  READY TO FLASH")
        print(f"{'='*60}")
        print(f"Firmware: {current_firmware_path}")
        print(f"Now plug in the target device (ESP32)...\n")
        
    else:
        print(f"\n[Main] ✗ USB VERIFICATION FAILED")
        print(f"[Main] Reason: {result.message}")
        
        # Show error
        led.show_error()
        time.sleep(5)
        led.show_idle()
        
        print("\nPlease check:")
        print("  1. USB contains valid certificate")
        print("  2. Firmware checksum is correct")
        print("  3. All required files are present\n")

def handle_storage_removed(device_node, storage_monitor, led):
    """Handle USB storage removed event.
    
    Args:
        device_node: Device node path
        storage_monitor: USBStorageMonitor instance
        led: LEDController instance
    """
    global current_usb_storage, current_firmware_path
    
    print(f"\n[Main] USB storage removed")
    
    if current_usb_storage:
        # Try to unmount
        storage_monitor.unmount_device(current_usb_storage.mount_point)
        
        # Clear current USB info
        current_usb_storage = None
        current_firmware_path = None
        
        print("[Main] Firmware source cleared")
        print("[Main] Waiting for new USB storage...\n")
    
    led.show_idle()

def handle_device_connected(device, device_validator, flasher, led):
    """Handle target device connected event.
    
    Args:
        device: USBDevice object
        device_validator: DeviceValidator instance
        flasher: FirmwareFlasher instance
        led: LEDController instance
    """
    global current_firmware_path
    
    print(f"\n{'='*60}")
    print(f"[Main] TARGET DEVICE CONNECTED")
    print(f"{'='*60}")
    print(f"Device: {device}")
    
    # Validate device
    led.show_validating()
    
    if not device_validator.is_valid_device(device):
        print("[Main] ✗ Unknown device, ignoring")
        led.show_idle()
        return
    
    print("[Main] ✓ Valid target device detected!")
    
    # Check if we have firmware ready
    if not current_firmware_path:
        print("\n[Main] ✗ NO FIRMWARE AVAILABLE")
        print("[Main] Please insert USB storage with firmware first!\n")
        
        led.show_error()
        time.sleep(3)
        led.show_idle()
        return
    
    # Get device port
    port = device_validator.get_device_port(device)
    
    if not port:
        print("[Main] ✗ No valid serial port found")
        led.show_error()
        time.sleep(3)
        led.show_idle()
        return
    
    print(f"[Main] Port: {port}")
    print(f"[Main] Firmware: {current_firmware_path}")
    
    # Flash firmware
    led.show_updating()
    
    # Update flasher with firmware from USB
    flasher.firmware_path = current_firmware_path
    
    result = flasher.flash(port)
    
    # Handle result
    if result.success:
        print(f"\n{'='*60}")
        print(f"  ✓ FLASH SUCCESSFUL!")
        print(f"{'='*60}")
        print(f"Duration: {result.duration:.1f}s")
        print(f"Attempts: {result.attempt}")
        print(f"Firmware: {current_firmware_path}")
        print(f"{'='*60}\n")
        
        led.show_success()
        time.sleep(5)
    else:
        print(f"\n{'='*60}")
        print(f"  ✗ FLASH FAILED!")
        print(f"{'='*60}")
        print(f"Error: {result.message}")
        print(f"{'='*60}\n")
        
        led.show_error()
        time.sleep(5)
    
    # Return to idle
    led.show_idle()

if __name__ == '__main__':
    sys.exit(main())