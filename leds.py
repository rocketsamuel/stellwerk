import threading

from rpi_ws281x import PixelStrip, Color

from config import (
    LED_COUNT,
    LED_PIN,
    LED_BRIGHTNESS,
    SWITCH_LEDS,
    ROUTE_LEDS,
)


YELLOW = (255, 180, 0)
OFF = (0, 0, 0)


class LEDs:

    def __init__(self):

        self.strip = PixelStrip(
            LED_COUNT,
            LED_PIN,
            800000,
            10,
            False,
            LED_BRIGHTNESS,
            0
        )

        self.blink_thread = None
        self.blink_stop_event = threading.Event()

    # --------------------------------------------------
    # START
    # --------------------------------------------------

    def start(self):

        self.strip.begin()

        self.all_off()

    # --------------------------------------------------
    # EINZELNE LED
    # --------------------------------------------------

    def set(
        self,
        led,
        r,
        g,
        b
    ):

        if led < 1 or led > LED_COUNT:
            raise ValueError(
                f"Ungültige LED-Nummer: {led}"
            )

        # Unsere Nummerierung beginnt bei 1.
        # rpi_ws281x beginnt bei 0.
        self.strip.setPixelColor(
            led - 1,
            Color(r, g, b)
        )

    # --------------------------------------------------
    # ANZEIGEN
    # --------------------------------------------------

    def show(self):

        self.strip.show()

    # --------------------------------------------------
    # ALLE AUS
    # --------------------------------------------------

    def all_off(self):

        for led in range(
            1,
            LED_COUNT + 1
        ):

            self.set(
                led,
                *OFF
            )

        self.show()

    # --------------------------------------------------
    # WEICHENSTELLUNG ANZEIGEN
    # --------------------------------------------------

    def switch_position(
        self,
        switch_name,
        position
    ):

        leds = SWITCH_LEDS.get(
            switch_name
        )

        if not leds:

            print(
                f"Keine LED-Zuordnung für "
                f"Weiche {switch_name}"
            )

            return

        # Alle LEDs dieser Weiche ausschalten.
        for led in leds.values():

            self.set(
                led,
                *OFF
            )

        # LED der aktuellen Stellung einschalten.
        led = leds.get(
            position
        )

        if led is None:

            print(
                f"Keine LED-Zuordnung für "
                f"{switch_name} = {position}"
            )

            self.show()

            return

        self.set(
            led,
            *YELLOW
        )

        self.show()

        print(
            f"LED Weiche {switch_name}: "
            f"{position} -> LED {led}"
        )

    # --------------------------------------------------
    # FAHRSTRASSE EIN
    # --------------------------------------------------

    def route_on(
        self,
        route_name
    ):

        self.stop_blink()

        leds = ROUTE_LEDS.get(
            route_name,
            []
        )

        for led in leds:

            self.set(
                led,
                *YELLOW
            )

        self.show()

    # --------------------------------------------------
    # FAHRSTRASSE BLINKEN
    # --------------------------------------------------

    def route_blink(
        self,
        route_name
    ):

        self.stop_blink()

        leds = ROUTE_LEDS.get(
            route_name,
            []
        )

        if not leds:

            print(
                f"Keine LEDs für Fahrstraße "
                f"{route_name}"
            )

            return

        self.blink_stop_event.clear()

        def blink():

            state = False

            while not self.blink_stop_event.is_set():

                state = not state

                for led in leds:

                    if state:

                        self.set(
                            led,
                            *YELLOW
                        )

                    else:

                        self.set(
                            led,
                            *OFF
                        )

                self.show()

                self.blink_stop_event.wait(
                    0.5
                )

        self.blink_thread = threading.Thread(
            target=blink,
            daemon=True
        )

        self.blink_thread.start()

    # --------------------------------------------------
    # BLINKEN STOPPEN
    # --------------------------------------------------

    def stop_blink(self):

        self.blink_stop_event.set()

        if self.blink_thread:

            self.blink_thread.join(
                timeout=1
            )

            self.blink_thread = None

    # --------------------------------------------------
    # BEENDEN
    # --------------------------------------------------

    def shutdown(self):

        self.stop_blink()

        self.all_off()
