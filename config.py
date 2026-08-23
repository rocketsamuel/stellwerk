
Z21_IP = "192.168.178.223"
Z21_PORT = 21105

TURNOUT_PULSE_TIME = 0.2
BROADCAST_KEEPALIVE = 5.0
ROUTE_TIMEOUT = 10.0

# WS2812B
LED_COUNT = 20
LED_PIN = 18
LED_BRIGHTNESS = 32

BLINK_INTERVAL = 0.5
ROUTE_MIN_BLINK_TIME = 1

# ---------------------------------------------------------
# TASTER
# BCM-GPIO-Nummern
# ---------------------------------------------------------

BUTTON_PINS = {
    "HBF4": 22,
    "ABS1": 27,
    "ABS2": None,
    "ABS3": None,
    "BW": None,
    "ABS0": None,
    "RELEASE": 17,
}

# ---------------------------------------------------------
# WEICHEN
# ---------------------------------------------------------

SWITCHES = {
    "sw46": {
        "type": "turnout",
        "address": 5,
    },

    "sw42": {
        "type": "three_way",
        "addresses": [25, 26],

        "positions": {
            "straight": {
                25: "straight",
                26: "straight",
            },

            "right": {
                25: "turnout",
                26: "straight",
            },

            "left": {
                25: "straight",
                26: "turnout",
            },
        },
    },
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
        "sw42": "straight"
     },
  },
  "ABS2_HBF4": {
     "start": "ABS2",
     "target": "HBF4",
     "switches": {
         "sw46": "straight",
         "sw42": "straight"
     },
  },
    "ABS3_HBF4": {
     "start": "ABS3",
     "target": "HBF4",
     "switches": {
         "sw42": "left"
     },
  },
}


# ---------------------------------------------------------
# LEDS
# ---------------------------------------------------------

SWITCH_LEDS = {
    "sw46": {
        "straight": 4,
        "turnout": 3,
    },
    "sw42": {
        "left": 12,
        "straight": 11,
        "right": 10,
    },
}

ROUTE_LEDS = {
    "ABS1_HBF4": [1, 2, 9, 13],
    "ABS2_HBF4": [5, 9, 13],
    "ABS3_HBF4": [6, 7, 8, 13, 14]
}
