"""LED controller module - Simple version with blinking."""

from gpiozero import LED
from threading import Thread, Event
import time

class LEDController:
    """Control 3 LEDs for status indication."""
    
    def __init__(self, pin_green=17, pin_yellow=27, pin_red=22):
        """Initialize LED controller.
        
        Args:
            pin_green: GPIO pin for green LED
            pin_yellow: GPIO pin for yellow LED
            pin_red: GPIO pin for red LED
        """
        self.led_green = LED(pin_green)
        self.led_yellow = LED(pin_yellow)
        self.led_red = LED(pin_red)
        
        # Blinking control
        self.blink_thread = None
        self.blink_stop = Event()
        
        self.all_off()
        print(f"[LED] Initialized: Green={pin_green}, Yellow={pin_yellow}, Red={pin_red}")
    
    def all_off(self):
        """Turn all LEDs off."""
        self.stop_blinking()
        self.led_green.off()
        self.led_yellow.off()
        self.led_red.off()
    
    def show_idle(self):
        """Show idle state - green solid."""
        self.all_off()
        self.led_green.on()
        print("[LED] IDLE: Green ON")
    
    def show_validating(self):
        """Show validating state - yellow blink fast."""
        self.all_off()
        self.start_blinking(self.led_yellow, interval=0.2)
        print("[LED] VALIDATING: Yellow BLINK fast")
    
    def show_updating(self):
        """Show updating state - yellow blink slow."""
        self.all_off()
        self.start_blinking(self.led_yellow, interval=0.5)
        print("[LED] UPDATING: Yellow BLINK slow")
    
    def show_success(self):
        """Show success state - green solid."""
        self.all_off()
        self.led_green.on()
        print("[LED] SUCCESS: Green ON")
    
    def show_error(self):
        """Show error state - red solid."""
        self.all_off()
        self.led_red.on()
        print("[LED] ERROR: Red ON")
    
    def start_blinking(self, led, interval=0.5):
        """Start LED blinking.
        
        Args:
            led: LED object to blink
            interval: Blink interval in seconds
        """
        self.stop_blinking()
        
        self.blink_stop.clear()
        self.blink_thread = Thread(
            target=self._blink_loop,
            args=(led, interval),
            daemon=True
        )
        self.blink_thread.start()
    
    def stop_blinking(self):
        """Stop LED blinking."""
        if self.blink_thread and self.blink_thread.is_alive():
            self.blink_stop.set()
            self.blink_thread.join(timeout=1.0)
    
    def _blink_loop(self, led, interval):
        """LED blink loop (runs in thread)."""
        while not self.blink_stop.is_set():
            led.on()
            if self.blink_stop.wait(interval):
                break
            led.off()
            if self.blink_stop.wait(interval):
                break
        led.off()
    
    def cleanup(self):
        """Cleanup GPIO."""
        self.stop_blinking()
        self.all_off()
        self.led_green.close()
        self.led_yellow.close()
        self.led_red.close()
        print("[LED] Cleaned up")
