#!/usr/bin/env python3
"""
rgb_controller.py

A complete, production-quality Raspberry Pi RGB LED Controller.
Automatically cycles through 19 interactive animation modes infinitely
while providing real-time keyboard adjustments and a terminal dashboard.

Hardware Requirements:
- Raspberry Pi
- RGB LED (Common Cathode)
- GPIO Mapping: RED=18, GREEN=13, BLUE=19

Author: Gemini (AI)
Date: June 2026
"""

import sys
import time
import math
import random
import select
import termios
import tty
import json
import os
import traceback

# Attempt to import RPi.GPIO. Fallback to mock for testing if not on a Pi.
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("WARNING: RPi.GPIO module not found. Running in simulation mode.")

# =====================================================================
# HELPER FUNCTIONS (Mathematical & Color Utilities)
# =====================================================================

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between two values."""
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t

def fade(color1: tuple, color2: tuple, t: float) -> tuple:
    """Fades between two RGB colors."""
    return (
        lerp(color1[0], color2[0], t),
        lerp(color1[1], color2[1], t),
        lerp(color1[2], color2[2], t)
    )

def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Converts 0-100 RGB values to a standard HEX color string."""
    r_255 = int(max(0, min(255, (r / 100.0) * 255.0)))
    g_255 = int(max(0, min(255, (g / 100.0) * 255.0)))
    b_255 = int(max(0, min(255, (b / 100.0) * 255.0)))
    return f"#{r_255:02X}{g_255:02X}{b_255:02X}"

def hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    """Converts HSV to RGB without using the colorsys module."""
    c = v * s
    x = c * (1 - abs(((h / 60.0) % 2) - 1))
    m = v - c

    if 0 <= h < 60:
        r_p, g_p, b_p = c, x, 0.0
    elif 60 <= h < 120:
        r_p, g_p, b_p = x, c, 0.0
    elif 120 <= h < 180:
        r_p, g_p, b_p = 0.0, c, x
    elif 180 <= h < 240:
        r_p, g_p, b_p = 0.0, x, c
    elif 240 <= h < 300:
        r_p, g_p, b_p = x, 0.0, c
    else:
        r_p, g_p, b_p = c, 0.0, x

    return ((r_p + m) * 100.0, (g_p + m) * 100.0, (b_p + m) * 100.0)

def rgb_cube(phase: float) -> tuple:
    """Traverses the RGB cube perimeter smoothly."""
    p = phase % 6.0
    if p < 1.0:
        return (100.0, p * 100.0, 0.0)
    elif p < 2.0:
        return (100.0 - (p - 1.0) * 100.0, 100.0, 0.0)
    elif p < 3.0:
        return (0.0, 100.0, (p - 2.0) * 100.0)
    elif p < 4.0:
        return (0.0, 100.0 - (p - 3.0) * 100.0, 100.0)
    elif p < 5.0:
        return ((p - 4.0) * 100.0, 0.0, 100.0)
    else:
        return (100.0, 0.0, 100.0 - (p - 5.0) * 100.0)

def random_color() -> tuple:
    """Returns a random RGB color tuple."""
    return (random.uniform(0, 100), random.uniform(0, 100), random.uniform(0, 100))

def rainbow(phase: float) -> tuple:
    """Generates rainbow spectrum colors based on phase angle."""
    h = (phase * 360) % 360
    return hsv_to_rgb(h, 1.0, 1.0)

def breathing(phase: float, base_color: tuple) -> tuple:
    """Applies a sinusoidal breathing brightness factor to a color."""
    intensity = (math.sin(phase) + 1.0) / 2.0
    return (base_color[0] * intensity, base_color[1] * intensity, base_color[2] * intensity)

# =====================================================================
# HARDWARE CONTROLLER
# =====================================================================

class RGBController:
    """Manages the low-level hardware interface for PWM color control."""
    def __init__(self, pin_r: int = 18, pin_g: int = 13, pin_b: int = 19, freq: int = 2000):
        self.pin_r = pin_r
        self.pin_g = pin_g
        self.pin_b = pin_b
        self.freq = freq
        
        self.current_rgb = (0.0, 0.0, 0.0)
        self.current_duty = (0.0, 0.0, 0.0)

        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup([self.pin_r, self.pin_g, self.pin_b], GPIO.OUT)
            
            self.pwm_r = GPIO.PWM(self.pin_r, self.freq)
            self.pwm_g = GPIO.PWM(self.pin_g, self.freq)
            self.pwm_b = GPIO.PWM(self.pin_b, self.freq)
            
            self.pwm_r.start(0)
            self.pwm_g.start(0)
            self.pwm_b.start(0)
        else:
            self.pwm_r = self.pwm_g = self.pwm_b = None

    def set_color(self, r: float, g: float, b: float, brightness: float = 1.0) -> tuple:
        """Applies values directly to hardware channels with global scaling."""
        self.current_rgb = (r, g, b)
        
        duty_r = max(0.0, min(100.0, r * brightness))
        duty_g = max(0.0, min(100.0, g * brightness))
        duty_b = max(0.0, min(100.0, b * brightness))
        
        self.current_duty = (duty_r, duty_g, duty_b)

        if GPIO_AVAILABLE:
            self.pwm_r.ChangeDutyCycle(duty_r)
            self.pwm_g.ChangeDutyCycle(duty_g)
            self.pwm_b.ChangeDutyCycle(duty_b)

        return self.current_duty

    def cleanup(self):
        """Releases hardware components cleanly."""
        if GPIO_AVAILABLE:
            self.pwm_r.stop()
            self.pwm_g.stop()
            self.pwm_b.stop()
            GPIO.cleanup()

# =====================================================================
# INPUT MANAGER (Non-Blocking Keyboard)
# =====================================================================

class InputManager:
    """Captures keyboard hits without pausing loop thread performance."""
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)

    def get_key(self):
        """Checks stream state for incoming characters without waiting."""
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None

    def cleanup(self):
        """Restores original operational environmental constraints."""
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

# =====================================================================
# ANIMATION ENGINE
# =====================================================================

class Animation:
    """Maintains time deltas, configurations, and vector calculations for 20 modes."""
    def __init__(self, mode: int = 1):
        self.mode = mode
        self.phase = 0.0
        self.timer = 0.0
        
        self.target_color = (0.0, 0.0, 0.0)
        self.prev_color = (0.0, 0.0, 0.0)
        self.step_index = 0
        
        self.primary = [(100,0,0), (0,100,0), (0,0,100)]
        self.secondary = [(100,100,0), (0,100,100), (100,0,100)]
        self.warm = [(100,30,0), (100,60,0), (100,80,0), (100,90,50)]
        self.cool = [(0,0,100), (0,50,100), (0,80,100), (0,100,100), (50,0,100)]
        self.white_temps = [(100,80,50), (100,90,80), (100,100,100)]
        
        self.reset_state()

    def reset_state(self):
        """Normalizes parameters safely across state changes."""
        self.phase = 0.0
        self.timer = 0.0
        self.step_index = 0
        self.prev_color = random_color()
        self.target_color = random_color()

    def update(self, dt: float, speed: float) -> tuple:
        """Executes corresponding logic loops based on current configuration index."""
        mode_method = getattr(self, f"mode_{self.mode}", self.mode_1)
        return mode_method(dt, speed)

    def mode_1(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 0.2
        return rainbow(self.phase)

    def mode_2(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 0.5
        return rgb_cube(self.phase)

    def mode_3(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 0.5
        if self.phase >= 1.0:
            self.phase = 0.0
            self.prev_color = self.target_color
            self.target_color = random_color()
        return fade(self.prev_color, self.target_color, self.phase)

    def mode_4(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 0.2
        self.timer += dt * speed * 2.0
        return breathing(self.timer, rainbow(self.phase))

    def mode_5(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed
        if self.timer > 0.4:
            self.timer = 0.0
            self.phase += 0.1
            if self.phase > 1.05:
                self.phase = 0.0
                self.step_index = (self.step_index + 1) % len(self.primary)
        color = self.primary[self.step_index]
        intensity = min(1.0, max(0.0, self.phase))
        return (color[0]*intensity, color[1]*intensity, color[2]*intensity)

    def mode_6(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed
        if self.timer > 1.0:
            self.timer = 0.0
            self.step_index = (self.step_index + 1) % len(self.primary)
        return self.primary[self.step_index]

    def mode_7(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed
        if self.timer > 1.0:
            self.timer = 0.0
            self.step_index = (self.step_index + 1) % len(self.secondary)
        return self.secondary[self.step_index]

    def mode_8(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed * 0.5
        idx1 = int(self.timer) % len(self.warm)
        idx2 = (idx1 + 1) % len(self.warm)
        return fade(self.warm[idx1], self.warm[idx2], self.timer - int(self.timer))

    def mode_9(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed * 0.5
        idx1 = int(self.timer) % len(self.cool)
        idx2 = (idx1 + 1) % len(self.cool)
        return fade(self.cool[idx1], self.cool[idx2], self.timer - int(self.timer))

    def mode_10(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed * 0.5
        idx1 = int(self.timer) % len(self.white_temps)
        idx2 = (idx1 + 1) % len(self.white_temps)
        return fade(self.white_temps[idx1], self.white_temps[idx2], self.timer - int(self.timer))

    def mode_11(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 2.0
        val = (math.sin(self.phase) + 1.0) / 2.0 * 100.0
        cycle = int(self.phase / (2 * math.pi)) % 3
        if cycle == 0: return (val, 0.0, 0.0)
        elif cycle == 1: return (0.0, val, 0.0)
        else: return (0.0, 0.0, val)

    def mode_12(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed * 2.0
        if self.timer > 0.1:
            self.timer = 0.0
            self.phase += 5.0
            if self.phase > 105.0:
                self.phase = 0.0
                self.step_index = (self.step_index + 1) % 3
        val = min(100.0, max(0.0, self.phase))
        if self.step_index == 0: return (val, 0, 0)
        elif self.step_index == 1: return (0, val, 0)
        else: return (0, 0, val)

    def mode_13(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed
        sim_fps = 1.0 + (math.sin(self.timer * 0.5) + 1.0) * 30.0
        frame_time = 1.0 / sim_fps
        self.phase += dt
        if self.phase >= frame_time:
            self.phase = 0.0
            self.target_color = rgb_cube(self.timer)
        return self.target_color

    def mode_14(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed
        return (
            50.0 + 50.0 * math.sin(self.phase * 0.7),
            50.0 + 50.0 * math.sin(self.phase * 1.1),
            50.0 + 50.0 * math.sin(self.phase * 1.3)
        )

    def mode_15(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed
        return (
            (math.sin(self.phase) + 1.0) / 2.0 * 100.0,
            (math.sin(self.phase + 2.0*math.pi/3.0) + 1.0) / 2.0 * 100.0,
            (math.sin(self.phase + 4.0*math.pi/3.0) + 1.0) / 2.0 * 100.0
        )

    def mode_16(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 8.0
        return (100.0, 0.0, 0.0) if int(self.phase) % 2 == 0 else (0.0, 0.0, 100.0)

    def mode_17(self, dt: float, speed: float) -> tuple:
        self.timer += dt * speed * 15.0
        if self.timer > 1.0:
            self.timer = 0.0
            self.prev_color = self.target_color
            self.target_color = (random.uniform(80.0, 100.0), random.uniform(10.0, 35.0), random.uniform(0.0, 4.0))
        return fade(self.prev_color, self.target_color, self.timer)

    def mode_18(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 0.4
        return (0.0, 25.0 + 25.0 * math.sin(self.phase * 1.4), 65.0 + 35.0 * math.sin(self.phase))

    def mode_19(self, dt: float, speed: float) -> tuple:
        self.phase += dt * speed * 0.3
        return (
            15.0 + 15.0 * math.sin(self.phase * 0.7),
            55.0 + 45.0 * math.sin(self.phase),
            40.0 + 40.0 * math.sin(self.phase * 1.2)
        )

# =====================================================================
# TERMINAL GRAPHICS INTERFACE
# =====================================================================

class Menu:
    """Manages stdout rendering of real-time operational states."""
    MODES = [
        "Smooth HSV Rainbow", "RGB Cube Traversal", "Random Smooth Colors",
        "Breathing Rainbow", "Brightness Demo", "Primary Colors",
        "Secondary Colors", "Warm Colors", "Cool Colors",
        "White Temperature Demo", "Individual Channel Fade", "Duty Cycle Demonstration",
        "Frequency Demonstration", "Million Color Sweep", "Rainbow Wave",
        "Police Lights", "Fire Simulation", "Ocean Mode", "Aurora Mode"
    ]

    def clear_screen(self):
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    def display_dashboard(self, mode: int, fps: float, freq: int, brightness: float, 
                          rgb: tuple, hex_color: str, duty: tuple, speed: float, remaining: float):
        """Overwrites parameters cleanly from row 0 using ANSI vector offsets."""
        sys.stdout.write("\033[H")
        dashboard = (
            f"====================================================\n"
            f"          AUTOMATED RGB TELEMETRY ACTIVE            \n"
            f"====================================================\n"
            f"Current Mode:        [{mode:02d}] {self.MODES[mode-1]:<25}\n"
            f"Next Mode Swap In:   {remaining:<4.1f} seconds\n"
            f"Current FPS:         {fps:<5.1f} HZ\n"
            f"PWM Carrier Freq:    {freq} Hz\n"
            f"Global Brightness:   {int(brightness*100):>3d} %\n"
            f"Vector Core Output:  R: {int(rgb[0]):>3d} | G: {int(rgb[1]):>3d} | B: {int(rgb[2]):>3d}\n"
            f"Hexadecimal Map:     {hex_color:<8}\n"
            f"Active Duty Cycles:  Red: {duty[0]:>4.1f}% Green: {duty[1]:>4.1f}% Blue: {duty[2]:>4.1f}%\n"
            f"Time Dilator Scale:  {speed:<4.2f}x\n"
            f"====================================================\n"
            f"Override Controls:   [+] Speed up       [-] Slow down\n"
            f"                     [B] Brighten       [N] Dim\n"
            f"                     [S] Store State    [R] Reset Core\n"
            f"                     [Q] Disconnect Hardware Platform\n"
        )
        sys.stdout.write(dashboard)
        sys.stdout.flush()

# =====================================================================
# SYSTEM APPLICATION ORCHESTRATION
# =====================================================================

class App:
    """System engine tracking timers, user configurations, and clock ticks."""
    def __init__(self):
        self.settings_file = "rgb_settings.json"
        self.mode = 1
        self.speed = 1.0
        self.brightness = 1.0
        self.running = True
        self.cycle_interval = 10.0  # Duration per mode in seconds
        
        self.load_settings()
        
        self.controller = RGBController(freq=2000)
        self.animator = Animation(self.mode)
        self.menu = Menu()
        
        self.target_fps = 120.0
        self.frame_time = 1.0 / self.target_fps

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.speed = data.get("speed", 1.0)
                    self.brightness = data.get("brightness", 1.0)
            except Exception:
                pass

    def save_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump({"speed": self.speed, "brightness": self.brightness}, f)
        except Exception:
            pass

    def run(self):
        """Executes unhindered loop execution path across the 19 animation structures."""
        self.menu.clear_screen()
        input_mgr = InputManager()
        
        try:
            last_time = time.perf_counter()
            fps_timer = last_time
            frame_count = 0
            current_fps = 0.0
            mode_accumulator = 0.0

            while self.running:
                now = time.perf_counter()
                dt = now - last_time
                last_time = now
                
                # Mode automatic transition pacing
                mode_accumulator += dt
                if mode_accumulator >= self.cycle_interval:
                    mode_accumulator = 0.0
                    self.mode = (self.mode % 19) + 1
                    self.animator.mode = self.mode
                    self.animator.reset_state()

                # Dynamic FPS metering
                frame_count += 1
                if now - fps_timer >= 0.5:
                    current_fps = frame_count / (now - fps_timer)
                    frame_count = 0
                    fps_timer = now

                # Real-time interactive asynchronous event monitoring
                key = input_mgr.get_key()
                if key:
                    k = key.upper()
                    if k == 'Q':
                        self.running = False
                    elif k == '+':
                        self.speed = min(5.0, self.speed + 0.1)
                    elif k == '-':
                        self.speed = max(0.1, self.speed - 0.1)
                    elif k == 'B':
                        self.brightness = min(1.0, self.brightness + 0.1)
                    elif k == 'N':
                        self.brightness = max(0.0, self.brightness - 0.1)
                    elif k == 'S':
                        self.save_settings()
                    elif k == 'R':
                        self.speed = 1.0
                        self.brightness = 1.0
                        mode_accumulator = 0.0
                        self.animator.reset_state()

                if not self.running:
                    break

                # Vector transforms and hardware updates
                r, g, b = self.animator.update(dt, self.speed)
                duty = self.controller.set_color(r, g, b, self.brightness)
                hex_str = rgb_to_hex(r, g, b)

                # Output formatting throttle (reduces screen rendering overhead)
                if frame_count % 4 == 0:
                    self.menu.display_dashboard(
                        mode=self.mode,
                        fps=current_fps,
                        freq=self.controller.freq,
                        brightness=self.brightness,
                        rgb=(r, g, b),
                        hex_color=hex_str,
                        duty=duty,
                        speed=self.speed,
                        remaining=max(0.0, self.cycle_interval - mode_accumulator)
                    )

                # Frame cadence limiter logic to prevent high CPU utilization
                sleep_remainder = self.frame_time - (time.perf_counter() - now)
                if sleep_remainder > 0:
                    time.sleep(sleep_remainder)

        except KeyboardInterrupt:
            self.running = False
        except Exception as e:
            print(f"\nSystem Error encountered: {e}")
            traceback.print_exc()
        finally:
            input_mgr.cleanup()
            self.controller.cleanup()
            print("\nGPIO hardware structures released cleanly. Process execution terminated.")

def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
