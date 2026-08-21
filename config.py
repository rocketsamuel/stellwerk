
Z21_IP = "192.168.178.223"
Z21_PORT = 21105

TURNOUT_PULSE_TIME = 0.2
BROADCAST_KEEPALIVE = 5.0
ROUTE_TIMEOUT = 10.0

# WS2812B
LED_COUNT = 20
LED_PIN = 18
LED_BRIGHTNESS = 64

BLINK_INTERVAL = 0.5
ROUTE_MIN_BLINK_TIME = 1

# ---------------------------------------------------------
# TASTER
# BCM-GPIO-Nummern
# ---------------------------------------------------------

BUTTON_PINS = {
    "HBF4": None,
    "ABS1": None,
    "ABS2": None,
    "ABS3": None,
    "BW": None,
    "ABS0": None,
}

# ---------------------------------------------------------
# WEICHEN
# ---------------------------------------------------------

SWITCHES = {
   "sw46": {
     "type": "turnout",
     "address": 5,
   },

    
    # DKW:
    #
    # "DKW1": {
    #     "type": "double_slip",
    #     "addresses": [10, 11],
    #
    #     "positions": {
    #         "straight": {
    #             10: "straight",
    #             11: "straight",
    #         },
    #         ...
    #     },
    # },
}

# ---------------------------------------------------------
# FAHRSTRASSEN
# ---------------------------------------------------------

ROUTES = {
  "ABS1_HBF4": {
     "start": "ABS1",
     "target": "HBF4",
     "switches": {
         "sw46": "turnout",
     },
  },
  "ABS2_HBF4": {
     "start": "ABS2",
     "target": "HBF4",
     "switches": {
         "sw46": "straight",
     },
  },
}


# ---------------------------------------------------------
# LEDS
# ---------------------------------------------------------

SWITCH_LEDS = {
  "sw46": {
    "straight": 4,
    "turnout": 3
  }
}

ROUTE_LEDS = {
    "ABS1_HBF4": [1, 2],
    "ABS2_HBF4": [5],
    "ABS3_HBF4": [6, 7]
}
