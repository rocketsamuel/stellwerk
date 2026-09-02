
Z21_IP = "192.168.178.223"
Z21_PORT = 21105

TURNOUT_PULSE_TIME = 0.2
BROADCAST_KEEPALIVE = 5.0

# Nur Schaltmeldungen und R-Bus-Rückmelder abonnieren.
# Die Z21 fasst Fahren und Schalten unter Flag 0x01 zusammen;
# nicht benötigte Fahrmeldungen werden bei der Ausgabe gefiltert.
Z21_BROADCAST_FLAGS = 0x00000003

# Jedes empfangene Z21-Dataset als Hex-Zeile ausgeben.
Z21_LOG_BROADCASTS = False
ROUTE_TIMEOUT = 10.0

# WS2812B
LED_COUNT = 25
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
    "BW": 16,
    "EOW5": 26,
    "EOW6": 20,
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
        "inverted": True
    },
    "eow2": {
        "type": "turnout",
        "address": 126,
        "inverted": True
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
# SIGNALE
# ---------------------------------------------------------

SIGNALS = {
    "signal_abs": {
        "type": "four_aspect",
        "addresses": [49, 50],
        "aspects": {
            "Hp0": [
                {"address": 49, "position": "straight"},
                {"address": 50, "position": "straight"},
            ],
            "Hp1": [
                {"address": 49, "position": "turnout"},
            ],
            "Hp2": [
                {"address": 49, "position": "straight"},
                {"address": 50, "position": "turnout"},
            ],
            "Hp0_Sh1": [
                {"address": 49, "position": "turnout"},
                {"address": 50, "position": "turnout"},
            ],
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
  "ABS1_BW": {
     "start": "ABS1",
     "target": "BW",
     "switches": {
        "sw46": "turnout",
        "sw42": "straight",
        "eow1": "straight"
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
  "ABS2_BW": {
     "start": "ABS2",
     "target": "BW",
     "switches": {
         "sw46": "straight",
         "sw42": "straight",
         "eow1": "straight"
     },
  },
  "ABS3_HBF4": {
     "start": "ABS3",
     "target": "HBF4",
     "switches": {
         "sw42": "left"
     },
  },
  "ABS3_BW": {
     "start": "ABS3",
     "target": "BW",
     "switches": {
         "sw42": "left",
         "eow1": "straight"
     },
  },
  "HBF4_ABS1": {
     "start": "HBF4",
     "target": "ABS1",
     "switches": {
        "sw46": "turnout",
        "sw42": "straight"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "HBF4_ABS2": {
     "start": "HBF4",
     "target": "ABS2",
     "switches": {
         "sw46": "straight",
         "sw42": "straight"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "HBF4_ABS3": {
     "start": "HBF4",
     "target": "ABS3",
     "switches": {
         "sw42": "left"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "HBF4_BW": {
     "start": "HBF4",
     "target": "BW",
     "switches": {
         "eow1": "straight"
     },
  },
  "BW_HBF4": {
     "start": "BW",
     "target": "HBF4",
     "switches": {
         "eow1": "straight"
     },
  },
  "BW_ABS1": {
     "start": "BW",
     "target": "ABS1",
     "switches": {
        "sw46": "turnout",
        "sw42": "straight",
        "eow1": "straight"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "BW_ABS2": {
     "start": "BW",
     "target": "ABS2",
     "switches": {
         "sw46": "straight",
         "sw42": "straight",
         "eow1": "straight"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "BW_ABS3": {
     "start": "BW",
     "target": "ABS3",
     "switches": {
         "sw42": "left",
         "eow1": "straight"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "EOW5_HBF4": {
     "start": "EOW5",
     "target": "HBF4",
     "switches": {
         "eow1": "turnout"
     },
  },
  "EOW5_ABS1": {
     "start": "EOW5",
     "target": "ABS1",
     "switches": {
         "eow1": "turnout",
         "sw42": "straight",
         "sw46": "turnout"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "EOW5_ABS2": {
     "start": "EOW5",
     "target": "ABS2",
     "switches": {
         "eow1": "turnout",
         "sw42": "straight",
         "sw46": "straight"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "EOW5_ABS3": {
     "start": "EOW5",
     "target": "ABS3",
     "switches": {
         "eow1": "turnout",
         "sw42": "left"
     },
     "signals": {"signal_abs": "Hp0_Sh1"},
  },
  "HBF4_EOW5": {
     "start": "HBF4",
     "target": "EOW5",
     "switches": {
         "eow1": "turnout",
         "eow2": "turnout"
     },
  },
  "ABS1_EOW5": {
     "start": "ABS1",
     "target": "EOW5",
     "switches": {
         "sw46": "turnout",
         "sw42": "straight",
         "eow1": "turnout"
     },
  },
  "ABS2_EOW5": {
     "start": "ABS2",
     "target": "EOW5",
     "switches": {
         "sw46": "straight",
         "sw42": "straight",
         "eow1": "turnout"
     },
  },
  "ABS3_EOW5": {
     "start": "ABS3",
     "target": "EOW5",
     "switches": {
         "sw42": "left",
         "eow1": "turnout"
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
    "eow2": {
        "straight": 25,
        "turnout": 24,
    },
}

ROUTE_LEDS = {
    "ABS1_HBF4": [1, 2, 9, 13],
    "ABS1_BW": [1, 2, 9, 13, 18, 19, 20],
    "ABS2_HBF4": [5, 9, 13],
    "ABS2_BW": [5, 9, 13, 18, 19, 20],
    "ABS3_HBF4": [6, 7, 8, 13, 14],
    "ABS3_BW": [6, 7, 8, 13, 14, 18, 19, 20],
    "HBF4_ABS1": [1, 2, 9, 13],
    "HBF4_ABS2": [5, 9, 13],
    "HBF4_ABS3": [6, 7, 8, 13, 14],
    "HBF4_BW": [13, 18, 19, 20],
    "BW_HBF4": [13, 18, 19, 20],
    "BW_ABS1": [1, 2, 9, 13, 18, 19, 20],
    "BW_ABS2": [5, 9, 13, 18, 19, 20],
    "BW_ABS3": [6, 7, 8, 13, 14, 18, 19, 20],
    "EOW5_HBF4": [13, 17],
    "EOW5_ABS1": [1, 2, 9, 13, 17],
    "EOW5_ABS2": [5, 9, 13, 17],
    "EOW5_ABS3": [6, 7, 8, 13, 14, 17],
    "HBF4_EOW5": [13, 17],
    "ABS1_EOW5": [1, 2, 9, 13, 17],
    "ABS2_EOW5": [5, 9, 13, 17],
    "ABS3_EOW5": [6, 7, 8, 13, 14, 17],
}
