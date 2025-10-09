"""Main application - Integrates all components."""

import sys
import signal
import time
from queue import Queue, Empty

from src.config import Config
from src.led_controller import LEDController
from src.usb_monitor import USBMonitor
from src.device_validator import DeviceValidator
from src.firmware_flasher import FirmwareFlasher

# Global flag for shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    print("\n[Main] Shutdown signal received...")
    shutdown_requested = True

def main():
    """Main application function."""
    global shutdown_requested
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*60)
    print("  FIRMWARE UPDATER")
    print("="*60)
    
    try:
        # 1. Load configuration
        print("\n[Main] Loading configuration...")
        config = Config()
        
        # 2. Initialize components
        print("\n[Main] Initializing components...")
        
        # Event queue
        event_queue = Queue(maxsize=32)
        
        # LED Controller
        led = LEDController(
            pin_green=config['gpio']['led_green'],
            pin_yellow=config['gpio']['led_yellow'],
            pin_red=config['gpio']['led_red']
        )
        
        # Start with IDLE state
        led.show_idle()
        
        # Device Validator
        validator = DeviceValidator(
            target_vid=config['target_device']['vid'],
            target_pid=config['target_device']['pid']
        )
        
        # Firmware Flasher
        flasher = FirmwareFlasher(config.config)
        
        # Verify flash tool
        if not flasher.verify_tool_available():
            print("\n⚠️  WARNING: Flash tool may not be available!")
            print("    Make sure avrdude/esptool is installed")
        
        # USB Monitor
        monitor = USBMonitor(event_queue)
        monitor.start_monitoring()
        
        print("\n" + "="*60)
        print("  SYSTEM READY - Waiting for devices...")
        print("="*60)
        print("\nTarget Device:")
        print(f"  VID: {config['target_device']['vid']}")
        print(f"  PID: {config['target_device']['pid']}")
        print(f"  Name: {config['target_device']['name']}")
        print("\nPress Ctrl+C to exit\n")
        
        # Main event loop
        while not shutdown_requested:
            try:
                # Get event with timeout
                event_type, device = event_queue.get(timeout=1.0)
                
                print(f"\n[Main] Event: {event_type}")
                print(f"[Main] Device: {device}")
                
                if event_type == 'device_connected':
                    # Validate device
                    led.show_validating()
                    
                    if validator.is_valid_device(device):
                        print("[Main] ✓ Valid device detected!")
                        
                        # Get device port
                        port = validator.get_device_port(device)
                        
                        if port:
                            print(f"[Main] Port: {port}")
                            
                            # Flash firmware
                            led.show_updating()
                            result = flasher.flash(port)
                            
                            # Handle result
                            if result.success:
                                print(f"\n{'='*60}")
                                print(f"  ✓ FLASH SUCCESSFUL!")
                                print(f"{'='*60}")
                                print(f"Duration: {result.duration:.1f}s")
                                print(f"Attempts: {result.attempt}")
                                
                                led.show_success()
                                time.sleep(5)
                            else:
                                print(f"\n{'='*60}")
                                print(f"  ✗ FLASH FAILED!")
                                print(f"{'='*60}")
                                print(f"Error: {result.message}")
                                
                                led.show_error()
                                time.sleep(5)
                            
                            # Return to idle
                            led.show_idle()
                        else:
                            print("[Main] ✗ No valid port found")
                            led.show_error()
                            time.sleep(3)
                            led.show_idle()
                    else:
                        print("[Main] ✗ Unknown device, ignoring")
                        led.show_idle()
                
                elif event_type == 'device_disconnected':
                    print("[Main] Device disconnected")
                
                event_queue.task_done()
                
            except Empty:
                # Timeout, continue
                continue
            
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
            monitor.stop_monitoring()
            led.cleanup()
        except:
            pass
        
        print("[Main] Shutdown complete")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
