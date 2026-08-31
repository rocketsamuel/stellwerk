
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

# Reihenfolge der LEDs beim Programmstart. Hier die gewünschte
# Reihenfolge eintragen; die LEDs bleiben bis zum Ende der Sequenz an.
STARTUP_LED_FLASH_TIME = 0.2
STARTUP_LED_FLASH_OFF_TIME = 0.2
STARTUP_LED_FLASH_COUNT = 2
STARTUP_LED_ORDER = list(range(1, LED_COUNT + 1))
STARTUP_LED_DELAY = 0.1

SHUTDOWN_HOLD_TIME = 5.0
SHUTDOWN_FLASH_COUNT = 3

# ---------------------------------------------------------
# TASTER
# BCM-GPIO-Nummern
# ---------------------------------------------------------

BUTTON_PINS = {
    "HBF4": 22,
    "ABS1": 27,
    "ABS2": 23,
    "ABS3": 24,
    "BW": None,
    "RELEASE": 17,
    "SHUTDOWN": 25,
}

# ---------------------------------------------------------
# WEICHEN
# ---------------------------------------------------------

SWITCHES = {
    "sw46": {
        "type": "turnout",
        "address": 5,
    },
    "eow1": {
        "type": "turnout",
        "address": 127,
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
    "HBF4_ABS1": {
     "start": "HBF4",
     "target": "ABS1",
     "switches": {
        "sw46": "turnout",
        "sw42": "straight"
     },
  },
    "HBF4_ABS2": {
     "start": "HBF4",
     "target": "ABS2",
     "switches": {
         "sw46": "straight",
         "sw42": "straight"
     },
  },
    "HBF4_ABS3": {
     "start": "HBF4",
     "target": "ABS3",
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
    "eow1": {
        "straight": 16,
        "turnout": 15,
    },
}

ROUTE_LEDS = {
    "ABS1_HBF4": [1, 2, 9, 13],
    "ABS2_HBF4": [5, 9, 13],
    "ABS3_HBF4": [6, 7, 8, 13, 14],
    "HBF4_ABS1": [1, 2, 9, 13],
    "HBF4_ABS2": [5, 9, 13],
    "HBF4_ABS3": [6, 7, 8, 13, 14]
}
