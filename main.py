from machine import Pin, I2C, ADC, deepsleep
import ssd1306_simple
import time
import urandom
from sound import Speaker
from ota import OTAUpdater
import uasyncio as asyncio

# --- Setup ---
i2c = I2C(0, scl=Pin(9), sda=Pin(8))
oled = ssd1306_simple.SSD1306Simple(128, 64, i2c)
button = Pin(0, Pin.IN, Pin.PULL_UP)
center = (0, 0)

blink_timer = 0
button_wink_timer = 0
last_qr_time = time.ticks_ms()
idle_start = time.ticks_ms()
sleeping = False
play = 0
ok = 0

qr = ssd1306_simple.BITMAP(oled)
bat = ssd1306_simple.BITMAP(oled)

# --- OTA Setup ---
ssid = "Rogers Pod"
password = "W1toronto47"
repo = "https://github.com/USER-1145-desgin/Viro-ota/"
filename = "main.py"
ota = OTAUpdater(ssid, password, repo, filename)
update_available = False

# --- Battery ---
bat_adc = ADC(Pin(2))
bat_adc.atten(ADC.ATTN_11DB)
bat_adc.width(ADC.WIDTH_12BIT)
R1, R2 = 10000, 10000
V_MIN, V_MAX = 3.0, 4.2
CALIBRATION = 3.2082202
LOW_THRESHOLD = 20

transistor = Pin(21, Pin.OUT)
sp = Speaker(pin=4)
piano_keys = {
    'C4': 261, 'C#4': 277, 'D4': 293, 'D#4': 311,
    'E4': 329, 'F4': 349, 'F#4': 370, 'G4': 392,
    'G#4': 415, 'A4': 440, 'A#4': 466, 'B4': 493, 'C5': 523
}

# --- Functions ---
def read_battery_voltage(samples=50):
    total = sum(bat_adc.read() for _ in range(samples))
    adc_avg = total / samples
    voltage = (adc_avg / 4095) * 3.3
    voltage = voltage * ((R1 + R2)/R2) * CALIBRATION
    return voltage

def voltage_to_percent(voltage):
    percent = int((voltage - V_MIN) / (V_MAX - V_MIN) * 100)
    return max(0, min(percent, 100))

CHECK_INTERVAL = 300  # seconds (5 minutes)
OTA_RETRIES = 3       # retry count for failed OTA checks

async def ota_task(ota):
    global update_available
    while True:
        for attempt in range(OTA_RETRIES):
            try:
                print("Checking OTA updates...")
                if ota.check_for_updates():
                    update_available = True
                    print("New update available! Downloading...")
                    # Only download and reset when ready
                    ota.download_and_install_update_if_available()
                else:
                    print("No new updates.")
                break  # success, exit retry loop
            except OSError as e:
                print(f"OTA check failed (attempt {attempt+1}/{OTA_RETRIES}):", e)
                await asyncio.sleep(2)  # short wait before retry
            except Exception as e:
                print("Unexpected OTA error:", e)
                break  # unexpected error, don't retry

        # Wait for the next OTA check
        await asyncio.sleep(CHECK_INTERVAL)

# --- Main loop task ---
async def main_loop():
    global blink_timer, button_wink_timer, idle_start, sleeping, last_qr_time, update_available, ok, play
    while True:
        oled.fill(0)
        now = time.ticks_ms()
        voltage = read_battery_voltage()
        percent = voltage_to_percent(voltage)

        # --- Battery check ---
        if percent <= LOW_THRESHOLD:
            print(f"Battery {percent}% - LOW BATTERY!")
            bat.show_picture('lowbat')
            await asyncio.sleep(3)
            deepsleep()

        # --- Button handling ---
        if button.value():
            idle_start = now
            sleeping = False
            if button_wink_timer == 0:
                button_wink_timer = 1
        else:
            play = 0
            ok = 0

        # --- Sleeping state ---
        sleeping = time.ticks_diff(now, idle_start) > 20*60*1000

        # --- Sleep or QR display ---
        if sleeping:
            oled.sleep_animation()
        else:
            if time.ticks_diff(now, last_qr_time) >= 15000:
                qr.show_QR()
                last_qr_time = now
                while True:
                    
                    now = time.ticks_ms()

                    if button.value() or time.ticks_diff(now, last_qr_time) >= 10000:
                        break
                    else:
                        pass
                last_qr_time = now
            
            # --- Wink / blink ---
            if button_wink_timer > 0:
                oled.draw_half_circle_eye('left', layers=5, direction="up")
                oled.draw_half_circle_eye('right', layers=5, direction="up")
                button_wink_timer -= 1
                if play == 0 and ok == 0:
                    for key in ['C4', 'C5']:
                        transistor.value(1)
                        sp.play_tone(piano_keys[key], 100)
                        transistor.value(0)
                        ok = 1
            else:
                if urandom.getrandbits(4) == 0:
                    blink_timer = 1
                if blink_timer > 0:
                    oled.draw_eye('left', blink=True)
                    oled.draw_eye('right', blink=True)
                else:
                    oled.draw_eye('left', pupil_offset=center, height=1)
                    oled.draw_eye('right', pupil_offset=center, height=1)
                blink_timer -= 1

        oled.show()
        await asyncio.sleep(0.01)

# --- Run both tasks concurrently ---
async def main():
    asyncio.create_task(ota_task(ota))  # start OTA in background
    await main_loop()  # your existing main_loop() task
 

asyncio.run(main())
