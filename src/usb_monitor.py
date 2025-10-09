import pyudev
from queue import Queue
from dataclasses import dataclass

@dataclass
class USBDevice:
    """USB device information."""
    sys_name: str
    device_node: str
    vid: str
    pid: str
    
    def __repr__(self):
        return f"USBDevice(vid={self.vid}, pid={self.pid}, port={self.device_node})"

class USBMonitor:
    """Monitor USB device events."""
    
    def __init__(self, event_queue):
        """Initialize USB monitor.
        
        Args:
            event_queue: Queue to post events
        """
        self.event_queue = event_queue
        
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='usb')
        
        self.observer = None
        print("[USB] Monitor initialized")
    
    def start_monitoring(self):
        """Start monitoring in background."""
        self.observer = pyudev.MonitorObserver(
            self.monitor,
            callback=self._handle_event,
            name='usb-monitor'
        )
        self.observer.start()
        print("[USB] Monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        if self.observer:
            self.observer.stop()
            self.observer = None
        print("[USB] Monitoring stopped")
    
    def _find_serial_port(self, usb_device):
      """Find serial port for USB device.
      
      Args:
          usb_device: pyudev USB device
          
      Returns:
          Serial port path or None
      """
      import time
      
      # Wait for TTY device to be created
      time.sleep(0.5)
      
      try:
          # List all TTY devices
          for tty in self.context.list_devices(subsystem='tty'):
              # Get parent USB device
              parent = tty.find_parent('usb', 'usb_device')
              
              if parent and parent.device_path == usb_device.device_path:
                  port = tty.device_node
                  if port:
                      print(f"[USB] Found serial port: {port}")
                      return port
      except Exception as e:
          print(f"[USB] Error finding serial port: {e}")
      
      return None
    
    def _handle_event(self, device):
      """Handle USB event - IMPROVED VERSION."""
      action = device.action
      
      if action not in ('add', 'remove'):
          return
      
      # Get device info
      vid = device.get('ID_VENDOR_ID', '')
      pid = device.get('ID_MODEL_ID', '')
      
      if not vid or not pid:
          return
      
      # Find serial port for USB device
      serial_port = self._find_serial_port(device)
      
      if not serial_port:
          # Fallback to device_node
          serial_port = device.device_node or ''
      
      usb_device = USBDevice(
          sys_name=device.sys_name,
          device_node=serial_port,  # Use found serial port
          vid=vid,
          pid=pid
      )
      
      # Post event to queue
      event_type = 'device_connected' if action == 'add' else 'device_disconnected'
      self.event_queue.put((event_type, usb_device))
      
      print(f"[USB] {event_type}: {usb_device}")