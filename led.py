#!/usr/bin/env python3

import sys
from rpi_ws281x import PixelStrip, Color


# -----------------------------
# WS2812B Konfiguration
# -----------------------------

LED_COUNT = 1
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10

# Zum Testen zunächst nur 25 % Helligkeit
LED_BRIGHTNESS = 32 # 64

LED_INVERT = False
LED_CHANNEL = 0
BLINK_INTERVAL = 0.5

# -----------------------------
# Farben
# -----------------------------

COLORS = {
    "red":     (255, 0, 0),
    "green":   (0, 255, 0),
    "blue":    (0, 0, 255),
    "yellow":  (255, 255, 0),
    "cyan":    (0, 255, 255),
    "magenta": (255, 0, 255),
    "white":   (255, 255, 255),
    "off":     (0, 0, 0),
}


def get_color(value):
    value = value.lower()

    if value in COLORS:
        return COLORS[value]

    # HEX-Farbe, z.B. #ff8000
    if value.startswith("#") and len(value) == 7:
        try:
            r = int(value[1:3], 16)
            g = int(value[3:5], 16)
            b = int(value[5:7], 16)
            return r, g, b
        except ValueError:
            pass

    raise ValueError(f"Unbekannte Farbe: {value}")


def main():
    if len(sys.argv) != 2:
        print("Verwendung:")
        print("  ./led.sh red")
        print("  ./led.sh green")
        print("  ./led.sh blue")
        print("  ./led.sh '#ff8000'")
        print("  ./led.sh off")
        sys.exit(1)

    try:
    except ValueError as error:
        print(error)
        sys.exit(1)

    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL
    )

    strip.begin()

    strip.setPixelColor(0, Color(r, g, b))
    strip.show()

    print(f"LED → RGB({r}, {g}, {b})")


if __name__ == "__main__":
    main()
