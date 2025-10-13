"""USB Storage Monitor - Detect and mount USB storage devices."""

import os
import time
import subprocess
import pyudev
from queue import Queue
from dataclasses import dataclass

@dataclass
class USBStorage:
    """USB storage device information."""
    device_node: str
    mount_point: str
    vendor: str
    model: str
    
    def __repr__(self):
        return f"USBStorage(device={self.device_node}, mount={self.mount_point})"

class USBStorageMonitor:
    """Monitor for USB storage devices (flash drives)."""
    
    def __init__(self, event_queue, mount_base="/media/pi"):
        """Initialize USB storage monitor.
        
        Args:
            event_queue: Queue to post events
            mount_base: Base directory for mounting
        """
        self.event_queue = event_queue
        self.mount_base = mount_base
        
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        
        # Monitor block devices (storage)
        self.monitor.filter_by(subsystem='block', device_type='partition')
        
        self.observer = None
        
        # Ensure mount base exists
        os.makedirs(mount_base, exist_ok=True)
        
        print(f"[USBStorage] Monitor initialized, mount base: {mount_base}")
    
    def start_monitoring(self):
        """Start monitoring USB storage devices."""
        self.observer = pyudev.MonitorObserver(
            self.monitor,
            callback=self._handle_event,
            name='usb-storage-monitor'
        )
        self.observer.start()
        print("[USBStorage] Monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        if self.observer:
            self.observer.stop()
            self.observer = None
        print("[USBStorage] Monitoring stopped")
    
    def _handle_event(self, device):
        """Handle USB storage event.
        
        Args:
            device: pyudev device object
        """
        action = device.action
        
        if action not in ('add', 'remove'):
            return
        
        # Check if it's a USB device
        if not self._is_usb_device(device):
            return
        
        device_node = device.device_node
        
        if action == 'add':
            print(f"\n[USBStorage] USB storage detected: {device_node}")
            
            # Try to mount
            storage = self._mount_device(device)
            
            if storage:
                print(f"[USBStorage] ✓ Mounted at: {storage.mount_point}")
                self.event_queue.put(('usb_storage_mounted', storage))
            else:
                print(f"[USBStorage] ✗ Failed to mount")
        
        elif action == 'remove':
            print(f"\n[USBStorage] USB storage removed: {device_node}")
            self.event_queue.put(('usb_storage_removed', device_node))
    
    def _is_usb_device(self, device):
        """Check if device is a USB storage device.
        
        Args:
            device: pyudev device
            
        Returns:
            True if USB device
        """
        # Find parent USB device
        parent = device.find_parent('usb', 'usb_device')
        return parent is not None
    
    def _mount_device(self, device):
        """Mount USB storage device.
        
        Args:
            device: pyudev device
            
        Returns:
            USBStorage object or None
        """
        device_node = device.device_node
        
        # Wait for device to be ready
        time.sleep(1)
        
        # Create mount point
        mount_name = os.path.basename(device_node)
        mount_point = os.path.join(self.mount_base, mount_name)
        
        try:
            # Create mount directory
            os.makedirs(mount_point, exist_ok=True)
            
            # Try to mount
            print(f"[USBStorage] Mounting {device_node} to {mount_point}...")
            
            result = subprocess.run(
                ['sudo', 'mount', device_node, mount_point],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Get device info
                vendor = device.get('ID_VENDOR', 'Unknown')
                model = device.get('ID_MODEL', 'Unknown')
                
                return USBStorage(
                    device_node=device_node,
                    mount_point=mount_point,
                    vendor=vendor,
                    model=model
                )
            else:
                print(f"[USBStorage] Mount failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"[USBStorage] Mount timeout")
            return None
        except Exception as e:
            print(f"[USBStorage] Mount error: {e}")
            return None
    
    def unmount_device(self, mount_point):
        """Unmount USB storage device.
        
        Args:
            mount_point: Mount point path
            
        Returns:
            True if successful
        """
        try:
            print(f"[USBStorage] Unmounting {mount_point}...")
            
            result = subprocess.run(
                ['sudo', 'umount', mount_point],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"[USBStorage] ✓ Unmounted")
                
                # Remove mount directory
                try:
                    os.rmdir(mount_point)
                except:
                    pass
                
                return True
            else:
                print(f"[USBStorage] Unmount failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[USBStorage] Unmount error: {e}")
            return False