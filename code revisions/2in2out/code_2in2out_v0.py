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
from adafruit_seesaw import seesaw, rotaryio, digitalio

displayio.release_displays()

oled_reset = board.GP28

i2c = busio.I2C(board.GP5, board.GP4)

display_bus = displayio.I2CDisplay(i2c, device_address=0x3D)
WIDTH = 128
HEIGHT = 64
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

aw.LED_modes = 0xFFFF
aw.directions = 0xFFFF

seesaw = seesaw.Seesaw(i2c, addr=0x36)

seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button = digitalio.DigitalIO(seesaw, 24)
button_held = False

encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

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

adc_chan0 = AnalogIn(ads, ADS.P0)
adc_chan1 = AnalogIn(ads, ADS.P1)
adc_chan2 = AnalogIn(ads, ADS.P2)
adc_chan3 = AnalogIn(ads, ADS.P3)
ads.mode = Mode.CONTINUOUS

dac = adafruit_mcp4728.MCP4728(i2c)

FULL_VREF_RAW_VALUE = 4095
dac.channel_a.raw_value = 0
dac.channel_b.raw_value = 0
dac.channel_c.raw_value = 0
dac.channel_d.raw_value = 0

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
key_on0 = [0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0]
key_on1 = [0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0]
volt = []

active_volts0 = []
active_volts1 = []
active_volts2 = []
active_volts3 = []

active_keys0 = []
active_keys1 = []
active_keys2 = []
active_keys3 = []

for v in volts:
    volt.append(v['1vOct'])
play0 = [0.000]
play1 = [0.000]
play2 = [0.000]
play3 = [0.000]

led_currents0 = [0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0]
led_currents1 = [0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0]
led_currents2 = [0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0]
led_currents3 = [0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0]

adc_channels = [adc_chan0, adc_chan1, adc_chan2, adc_chan3]
dac_channels = [dac.channel_a.raw_value, dac.channel_b.raw_value, 
                dac.channel_c.raw_value, dac.channel_d.raw_value]

channel = 0

def led_channel_select(led, z):
    if led[z] == 0:
        aw.set_constant_current(z, 125)
        led[z] = 125
    else:
        aw.set_constant_current(z, 0)
        led[z] = 0

def set_notes(volts, keys, key_on, play, chan):
    play.clear()
    keys.clear()
    states[s] = True
    key_on[s] = (key_on[s] + 1) % 2
    volts = [i for i, j in enumerate(key_on) if j == 1]
    for v in volts:
        the_keys = key_names[v]
        for j in range(5):
            notes = volt[v]
            play.append(notes)
            v = v + 12
        keys.append(the_keys)
    print("Channel %d's notes are: %s" % (chan, play))

def clear(play):
    if len(play) < 1:
        play.append(0.000)

def channel_output(adc, dac, play):
    quant = min(play, key=lambda x: abs(x-adc.voltage))
    pitch = map_volts(quant, 5, 4095)
    dac = int(pitch)

def channel_info(chan, quant, adc, keys, play):
    pitch_area.text = "Channel: %d" % chan
    quant_area.text = str(quant)
    volt_area.text = str(adc.voltage)
    key_area.text = str(keys)
    
total_channels = 4

while True:
    position = -encoder.position
    if position != last_position:
        if position > last_position:
            channel = (channel + 1) % total_channels
        if position < last_position:
            channel = (channel - 1) % total_channels
        for pin in range(12):
            if channel is 0:
                aw.set_constant_current(pin, led_currents0[pin])
            if channel is 1:
                aw.set_constant_current(pin, led_currents1[pin])
            if channel is 2:
                aw.set_constant_current(pin, led_currents2[pin])
            if channel is 3:
                aw.set_constant_current(pin, led_currents3[pin])
        last_position = position
    for s in range(12):
        if not buttons[s].value and states[s] is True:
            if channel is 0:
                led_channel_select(led_currents0, s)
            if channel is 1:
                led_channel_select(led_currents1, s)
            if channel is 2:
                led_channel_select(led_currents2, s)
            if channel is 3:
                led_channel_select(led_currents3, s)
            states[s] = False
        if buttons[s].value and states[s] is False:
            if channel is 0:
                set_notes(active_volts0, active_keys0, key_on0, play0, channel)
            if channel is 1:
                set_notes(active_volts1, active_keys1, key_on1, play1, channel)
            if channel is 2:
                set_notes(active_volts2, active_keys2, key_on2, play2, channel)
            if channel is 3:
                set_notes(active_volts3, active_keys3, key_on3, play3, channel)
        if channel is 0:
            clear(play0)
        if channel is 1:
            clear(play1)
        if channel is 2:
            clear(play2)
        if channel is 3:
            clear(play3)
    quant0 = min(play0, key=lambda x: abs(x-adc_chan0.voltage))
    quant1 = min(play1, key=lambda x: abs(x-adc_chan1.voltage))
    quant2 = min(play2, key=lambda x: abs(x-adc_chan2.voltage))
    quant3 = min(play3, key=lambda x: abs(x-adc_chan3.voltage))
    pitch0 = map_volts(quant0, 5, 4095)
    pitch1 = map_volts(quant1, 5, 4095)
    pitch2 = map_volts(quant2, 5, 4095)
    pitch3 = map_volts(quant3, 5, 4095)
    dac.channel_a.raw_value = int(pitch0)
    dac.channel_b.raw_value = int(pitch1)
    dac.channel_c.raw_value = int(pitch2)
    dac.channel_d.raw_value = int(pitch3)
    if channel is 0:
        channel_info(channel, quant0, adc_chan0, active_keys0, play0)
    if channel is 1:
        channel_info(channel, quant1, adc_chan1, active_keys1, play1)
    if channel is 2:
        channel_info(channel, quant2, adc_chan2, active_keys2, play2)
    if channel is 3:
        channel_info(channel, quant3, adc_chan3, active_keys3, play3)
