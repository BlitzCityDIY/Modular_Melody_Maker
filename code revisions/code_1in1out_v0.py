import board
import busio
import displayio
import terminalio
import adafruit_aw9523
from digitalio import DigitalInOut, Direction, Pull
import time
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import simpleio
import adafruit_ads1x15
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1x15 import Mode
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_mcp4728
from volts import volts

displayio.release_displays()

oled_reset = board.GP28

i2c = busio.I2C(board.GP5, board.GP4)

display_bus = displayio.I2CDisplay(i2c, device_address=0x3D)
WIDTH = 128
HEIGHT = 64  # Change to 64 if needed
BORDER = 5

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

switch_pins = [board.GP0, board.GP1, board.GP2, board.GP3, board.GP6, board.GP7,
				board.GP8, board.GP9, board.GP10, board.GP11, board.GP12, board.GP13]
buttons = []
for pin in switch_pins:
    switch_pin = DigitalInOut(pin)
    switch_pin.direction = Direction.INPUT
    switch_pin.pull = Pull.UP
    buttons.append(switch_pin)

aw = adafruit_aw9523.AW9523(i2c)
# Set all pins to outputs and LED (const current) mode
aw.LED_modes = 0xFFFF
aw.directions = 0xFFFF

# Make the display context
splash = displayio.Group()
display.show(splash)

# Draw a label
pitch_text = "Hello World!"
pitch_area = label.Label(
    terminalio.FONT, text=pitch_text, color=0xFFFFFF, x=5, y=10
)
quant_text = "Hello World!"
quant_area = label.Label(
    terminalio.FONT, text=quant_text, color=0xFFFFFF, x=5, y=25
)
volt_text = "Hello World!"
volt_area = label.Label(
    terminalio.FONT, text=volt_text, color=0xFFFFFF, x=5, y=40
)
key_text = "Hello World!"
key_area = label.Label(
    terminalio.FONT, text=key_text, color=0xFFFFFF, x=5, y=55
)
splash.append(pitch_area)
splash.append(quant_area)
splash.append(volt_area)
splash.append(key_area)

ads = ADS.ADS1115(i2c)

chan = AnalogIn(ads, ADS.P0)
ads.mode = Mode.CONTINUOUS

mcp4728 = adafruit_mcp4728.MCP4728(i2c)

FULL_VREF_RAW_VALUE = 4095
mcp4728.channel_a.raw_value = 0

def map_volts(volt, vref, bits):
    n = simpleio.map_range(volt, 0, vref, 0, bits)
    return n

sw0_state = False
sw1_state = False
sw2_state = False
sw3_state = False
sw4_state = False
sw5_state = False
sw6_state = False
sw7_state = False
sw8_state = False
sw9_state = False
sw10_state = False
sw11_state = False
states = [sw0_state, sw1_state, sw2_state, sw3_state, sw4_state, sw5_state,
			sw6_state, sw7_state, sw8_state, sw9_state, sw10_state, sw11_state]

key_names = ["C", "Db", "D", "Eb", "E", "F",
             "Gb", "G", "Ab", "A", "Bb", "B"]

octave = 0
key_on = [0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0]
volt = []
active_volts = []
active_keys = []
octave_jump = [0, 12, 24, 36, 48]
for v in volts:
    volt.append(v['1vOct'])
play = [0.000]

led_currents = [0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0]

while True:
    for s in range(12):
        if not buttons[s].value and states[s] is True:
            if led_currents[s] == 0:
                aw.set_constant_current(s, 125)
                led_currents[s] = 125
            else:
                aw.set_constant_current(s, 0)
                led_currents[s] = 0
            states[s] = False
            print(s)
        if buttons[s].value and states[s] is False:
            play.clear()
            active_keys.clear()
            states[s] = True
            key_on[s] = (key_on[s] + 1) % 2
            active_volts = [i for i, j in enumerate(key_on) if j == 1]
            for v in active_volts:
                the_keys = key_names[v]
                for j in range(5):
                    notes = volt[v]
                    play.append(notes)
                    v = v + 12
                #leds[v].value = True
                active_keys.append(the_keys)
            print(play)
        if len(play) < 1:
            play.append(0.000)
    quant = min(play, key=lambda x: abs(x-chan.voltage))
    pitch = map_volts(quant, 5, 4095)
    mcp4728.channel_a.raw_value = int(pitch)
    quant_area.text = str(quant)
    pitch_area.text = str(pitch)
    volt_area.text = str(chan.voltage)
    key_area.text = str(active_keys)
    # uncomment time.sleep if printing to REPL to avoid disaster
    # print((pitch, quant, chan.voltage),)
    # print((mcp4728.channel_a.raw_value,))
    # time.sleep(0.001)
