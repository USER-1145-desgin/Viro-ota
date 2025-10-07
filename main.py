from machine import Pin, I2C, ADC, deepsleep
import ssd1306_simple

# --- Setup ---
i2c = I2C(0, scl=Pin(9), sda=Pin(8))
oled = ssd1306_simple.SSD1306Simple(128, 64, i2c)

oled.write('Hello',0,0)
