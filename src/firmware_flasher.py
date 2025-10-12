"""Firmware flashing module with retry logic."""

import subprocess
import time
from dataclasses import dataclass

@dataclass
class FlashResult:
    """Result of firmware flashing."""
    success: bool
    message: str
    duration: float
    attempt: int = 1

class FirmwareFlasher:
    """Flash firmware with retry logic."""
    
    def __init__(self, config):
        """Initialize flasher.
        
        Args:
            config: Configuration dictionary
        """
        self.firmware_path = config['firmware']['path']
        self.tool_command = config['firmware']['command']
        self.timeout = config['firmware']['timeout']
        self.baudrate = config['firmware']['baudrate']
        self.retry_count = config['firmware']['retry_count']
        self.retry_delay = config['firmware']['retry_delay']
        
        print(f"[Flasher] Initialized")
        print(f"  Firmware: {self.firmware_path}")
        print(f"  Retry: {self.retry_count} times, delay {self.retry_delay}s")
    
    def flash(self, device_port):
        """Flash firmware with retry logic.
        
        Args:
            device_port: Serial port path
            
        Returns:
            FlashResult object
        """
        print(f"\n{'='*60}")
        print(f"[Flasher] Starting flash to {device_port}")
        print(f"{'='*60}")
        
        last_error = None
        
        # Retry loop
        for attempt in range(1, self.retry_count + 1):
            print(f"\n[Flasher] Attempt {attempt}/{self.retry_count}")
            
            try:
                result = self._execute_flash(device_port, attempt)
                
                if result.success:
                    print(f"[Flasher] ✓ SUCCESS on attempt {attempt}")
                    return result
                else:
                    last_error = result.message
                    print(f"[Flasher] ✗ FAILED: {result.message}")
                    
            except Exception as e:
                last_error = str(e)
                print(f"[Flasher] ✗ ERROR: {e}")
            
            # Delay before retry (except last attempt)
            if attempt < self.retry_count:
                print(f"[Flasher] Waiting {self.retry_delay}s before retry...")
                time.sleep(self.retry_delay)
        
        # All attempts failed
        error_msg = f"Flash failed after {self.retry_count} attempts. Last error: {last_error}"
        print(f"\n[Flasher] ✗ {error_msg}")
        
        return FlashResult(
            success=False,
            message=error_msg,
            duration=0.0,
            attempt=self.retry_count
        )
    
    def _execute_flash(self, device_port, attempt):
        """Execute single flash attempt.
        
        Args:
            device_port: Serial port path
            attempt: Attempt number
            
        Returns:
            FlashResult
        """
        start_time = time.time()

        print(f"[Flasher] Waiting for device to be ready...")
        time.sleep(0.2)
        
        # Build command
        command = self._build_command(device_port)
        print(f"[Flasher] Command: {' '.join(command)}")
        
        try:
            # Execute flash command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            # Check return code
            if result.returncode == 0:
                return FlashResult(
                    success=True,
                    message="Flash completed successfully",
                    duration=duration,
                    attempt=attempt
                )
            else:
                return FlashResult(
                    success=False,
                    message=f"Tool returned error code {result.returncode}",
                    duration=duration,
                    attempt=attempt
                )
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return FlashResult(
                success=False,
                message=f"Flash timeout after {self.timeout}s",
                duration=duration,
                attempt=attempt
            )
        
        except FileNotFoundError:
            return FlashResult(
                success=False,
                message=f"Flash tool not found: {command[0]}",
                duration=0.0,
                attempt=attempt
            )
    
    def _build_command(self, device_port):
        """Build flash command.
        
        Args:
            device_port: Serial port path
            
        Returns:
            Command as list
        """
        cmd_str = self.tool_command.format(
            port=device_port,
            firmware=self.firmware_path,
            baudrate=self.baudrate
        )
        
        return cmd_str.split()
    
    def verify_tool_available(self):
        """Check if flash tool is available.
        
        Returns:
            True if tool found
        """
        tool_name = self.tool_command.split()[0]
        
        try:
            result = subprocess.run(
                [tool_name, '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
