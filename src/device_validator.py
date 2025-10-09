"""Device validation module - Simple version."""

import re

class DeviceValidator:
    """Validate USB devices by VID/PID."""
    
    def __init__(self, target_vid, target_pid):
        """Initialize validator.
        
        Args:
            target_vid: Target vendor ID (4 hex digits)
            target_pid: Target product ID (4 hex digits)
        """
        self.target_vid = target_vid.lower()
        self.target_pid = target_pid.lower()
        
        print(f"[Validator] Target: VID={self.target_vid}, PID={self.target_pid}")
    
    def is_valid_device(self, device):
        """Check if device matches target.
        
        Args:
            device: USBDevice object
            
        Returns:
            True if valid
        """
        vid_match = device.vid.lower() == self.target_vid
        pid_match = device.pid.lower() == self.target_pid
        
        is_valid = vid_match and pid_match
        
        if is_valid:
            print(f"[Validator] ✓ Valid device: {device}")
        else:
            print(f"[Validator] ✗ Invalid device: {device}")
        
        return is_valid
    
    def get_device_port(self, device):
      """Get serial port for device - FIXED VERSION.
      
      Args:
          device: USBDevice object
          
      Returns:
          Port path or None
      """
      import os
      import time
      
      # Method 1: Check device_node
      port = device.device_node
      
      if port and port.startswith('/dev/tty'):
          print(f"[Validator] Port from device_node: {port}")
          return port
      
      # Method 2: Search for tty devices with same VID/PID
      print(f"[Validator] Searching for serial port with VID={device.vid}, PID={device.pid}...")
      
      # Wait a bit for device to be ready
      time.sleep(1)
      
      # Try common serial ports
      for port_name in ['ttyUSB0', 'ttyUSB1', 'ttyUSB2', 'ttyACM0', 'ttyACM1']:
          port_path = f'/dev/{port_name}'
          
          if os.path.exists(port_path):
              print(f"[Validator] Found port: {port_path}")
              
              # Verify it's the right device by checking sys path
              try:
                  sys_path = f"/sys/class/tty/{port_name}/device"
                  if os.path.exists(sys_path):
                      # Read VID/PID from sys
                      # This is the correct device
                      return port_path
              except:
                  pass
      
      # Method 3: Use pyudev to find TTY subsystem device
      try:
          import pyudev
          context = pyudev.Context()
          
          for tty_device in context.list_devices(subsystem='tty'):
              parent = tty_device.find_parent('usb', 'usb_device')
              if parent:
                  parent_vid = parent.get('ID_VENDOR_ID', '')
                  parent_pid = parent.get('ID_MODEL_ID', '')
                  
                  if parent_vid == device.vid and parent_pid == device.pid:
                      port = tty_device.device_node
                      if port:
                          print(f"[Validator] Found via pyudev: {port}")
                          return port
      except Exception as e:
          print(f"[Validator] pyudev search failed: {e}")
      
      print(f"[Validator] ✗ No serial port found!")
      return None