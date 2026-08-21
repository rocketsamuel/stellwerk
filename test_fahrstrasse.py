import time

from rpi_ws281x import PixelStrip, Color


LED_COUNT = 20
LED_PIN = 18
LED_BRIGHTNESS = 64

YELLOW = (255, 180, 0)
OFF = (0, 0, 0)

ROUTE_LEDS = [1, 6, 7, 8]


def set_led(strip, led, color):

    strip.setPixelColor(
        led - 1,
        Color(*color)
    )


def show_route(strip):

    # Alles aus
    for led in range(1, LED_COUNT + 1):
        set_led(strip, led, OFF)

    strip.show()

    print("Fahrstraße ABS2 -> HBF4")

    # 5 Sekunden blinken
    for _ in range(10):

        for led in ROUTE_LEDS:
            set_led(strip, led, YELLOW)

        strip.show()

        time.sleep(0.5)

        for led in ROUTE_LEDS:
            set_led(strip, led, OFF)

        strip.show()

        time.sleep(0.5)

    # Fahrstraße aktiv:
    # LEDs dauerhaft an

    for led in ROUTE_LEDS:
        set_led(strip, led, YELLOW)

    strip.show()

    print("Fahrstraße aktiv")
    print("10 Sekunden warten...")

    time.sleep(5)

    # Alles wieder aus

    for led in range(1, LED_COUNT + 1):
        set_led(strip, led, OFF)

    strip.show()

    print("Test beendet")


def main():

    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        800000,
        10,
        False,
        LED_BRIGHTNESS,
        0
    )

    strip.begin()

    try:
        show_route(strip)

    except KeyboardInterrupt:
        print("Abbruch")

    finally:

        for led in range(1, LED_COUNT + 1):
            set_led(strip, led, OFF)

        strip.show()


if __name__ == "__main__":
    main()
