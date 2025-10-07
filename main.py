from machine import Pin, I2C, ADC, deepsleep
import ssd1306_simple
import time
import urandom
from sound import Speaker
from ota import OTAUpdater

# --- Setup ---
i2c = I2C(0, scl=Pin(9), sda=Pin(8))
oled = ssd1306_simple.SSD1306Simple(128, 64, i2c)
button = Pin(0, Pin.IN, Pin.PULL_UP)
center = (0, 0)

blink_timer = 0
button_wink_timer = 0
last_ota_check = time.ticks_ms()
last_qr_time = time.ticks_ms()
idle_start = time.ticks_ms()
sleeping = False
mood = 'idle'

qr = ssd1306_simple.BITMAP(oled)
bat = ssd1306_simple.BITMAP(oled)

update_available = False
ssid = "Rogers Pod"
password = "W1toronto47"
repo = "https://github.com/USER-1145-desgin/Viro-ota/"
filename = "main.py"
ota = OTAUpdater(ssid, password, repo, filename)

# --- Battery setup ---
bat_adc = ADC(Pin(2))
bat_adc.atten(ADC.ATTN_11DB)
bat_adc.width(ADC.WIDTH_12BIT)
R1 = 10000
R2 = 10000
V_MIN = 3.0
V_MAX = 4.2
CALIBRATION = 3.2082202
LOW_THRESHOLD = 20

ok = 0
play = 0
transistor = Pin(21, Pin.OUT)
sp = Speaker(pin=4)
piano_keys = {
    'C4': 261, 'C#4': 277, 'D4': 293, 'D#4': 311,
    'E4': 329, 'F4': 349, 'F#4': 370, 'G4': 392,
    'G#4': 415, 'A4': 440, 'A#4': 466, 'B4': 493, 'C5': 523
}

# --- Functions ---
def read_battery_voltage(samples=50):
    total = 0
    for _ in range(samples):
        total += bat_adc.read()
    adc_avg = total / samples
    voltage = (adc_avg / 4095) * 3.3
    voltage = voltage * ((R1 + R2)/R2)
    voltage = voltage * CALIBRATION
    return voltage

def voltage_to_percent(voltage):
    percent = int((voltage - V_MIN) / (V_MAX - V_MIN) * 100)
    return max(0, min(percent, 100))

# --- Main loop ---
while True:
    oled.fill(0)
    now = time.ticks_ms()
    voltage = read_battery_voltage()
    percent = voltage_to_percent(voltage)

    # --- OTA check every 5 min ---
    if time.ticks_diff(now, last_ota_check) > 300000:
        if ota.check_for_updates():
            update_available = True
        last_ota_check = now

    # --- Battery status ---
    if percent <= LOW_THRESHOLD:
        print("Battery Voltage: {:.2f} V, Battery %: {}% - LOW BATTERY!".format(voltage, percent))
        bat.show_picture('lowbat')
        time.sleep(3)
        deepsleep()
    else:
        print("Battery Voltage: {:.2f} V, Battery %: {}%".format(voltage, percent))

    # --- OTA display ---
    if update_available:
        oled.write("New update available!", 25, 0)
        oled.write("Tap to update.", 40, 0)

    # --- Button and mood ---
    if button.value():
        idle_start = now
        sleeping = False
        last_qr_time = now
        mood = 'happy'
        if update_available:
            ota.update_and_reset()
    else:
        play = 0
        ok = 0
        mood = 'idle'

    # --- Determine sleeping state ---
    if time.ticks_diff(now, idle_start) > 20*60*1000:
        sleeping = True

    # --- Sleep animation ---
    if sleeping:
        oled.sleep_animation()
    else:
        # --- QR display every 15s ---
        if time.ticks_diff(now, last_qr_time) >= 15000:
            qr.show_QR()
            last_qr_time = now
            while True:
                now = time.ticks_ms()
                if button.value() or time.ticks_diff(now, last_qr_time) >= 10000:
                    break
            last_qr_time = now

        # --- Wink / blink ---
        if mood == 'happy':
            oled.draw_half_circle_eye('left', layers=5, direction="up")
            oled.draw_half_circle_eye('right', layers=5, direction="up")
            
            if button_wink_timer > 0:
                button_wink_timer = max(button_wink_timer - 1, 0)
            
            # Play sound once
            if play == 0 and ok == 0:
                transistor.value(1)
                sp.play_tone(piano_keys['C5'], 100)
                transistor.value(0)
                ok = 1

        else:
            if urandom.getrandbits(4) == 0:
                blink_timer = 1
            if blink_timer > 0:
                oled.draw_eye('left', blink=True)
                oled.draw_eye('right', blink=True)
            else:
                oled.draw_eye('left', pupil_offset=center, height=2)
                oled.draw_eye('right', pupil_offset=center, height=1)
            blink_timer -= 1

    oled.show()
    time.sleep(0.01)

