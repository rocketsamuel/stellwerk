import threading

from rpi_ws281x import PixelStrip, Color

from config import (
    LED_COUNT,
    LED_PIN,
    LED_BRIGHTNESS,
    SWITCH_LEDS,
    ROUTE_LEDS,
)


# ======================================================
# FARBEN
# ======================================================

YELLOW = (255, 180, 0)
OFF = (0, 0, 0)


class LEDs:

    def __init__(self):

        self.strip = PixelStrip(
            LED_COUNT,
            LED_PIN,
            800000,       # LED frequency
            10,           # DMA channel
            False,        # invert
            LED_BRIGHTNESS,
            0             # channel
        )

        self.blink_thread = None
        self.blink_stop_event = threading.Event()

    # ==================================================
    # START
    # ==================================================

    def start(self):

        self.strip.begin()

        self.all_off()

        print(
            f"WS2812B gestartet: "
            f"{LED_COUNT} LEDs, "
            f"GPIO {LED_PIN}, "
            f"Helligkeit {LED_BRIGHTNESS}"
        )

    # ==================================================
    # EINZELNE LED SETZEN
    # ==================================================

    def set(
        self,
        led,
        r,
        g,
        b
    ):

        if led < 1 or led > LED_COUNT:

            raise ValueError(
                f"Ungültige LED-Nummer: "
                f"{led} "
                f"(erlaubt: 1-{LED_COUNT})"
            )

        # Unsere Nummerierung beginnt bei 1.
        #
        # rpi_ws281x verwendet dagegen
        # eine Nummerierung ab 0.
        self.strip.setPixelColor(
            led - 1,
            Color(r, g, b)
        )

    # ==================================================
    # LEDs ANZEIGEN
    # ==================================================

    def show(self):

        self.strip.show()

    # ==================================================
    # ALLE LEDs AUS
    # ==================================================

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

    # ==================================================
    # WEICHENSTELLUNG ANZEIGEN
    # ==================================================

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

        # ----------------------------------------------
        # Alle LEDs dieser Weiche ausschalten
        # ----------------------------------------------

        for led in leds.values():

            self.set(
                led,
                *OFF
            )

        # ----------------------------------------------
        # LED der aktuellen Stellung bestimmen
        # ----------------------------------------------

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

        # ----------------------------------------------
        # Aktuelle Stellung gelb anzeigen
        # ----------------------------------------------

        self.set(
            led,
            *YELLOW
        )

        self.show()

        print(
            f"Weichen-LED: "
            f"{switch_name} = {position} "
            f"-> LED {led}"
        )

    # ==================================================
    # FAHRSTRASSEN-LEDs ERMITTELN
    # ==================================================

    def route_leds_for(
        self,
        route_name
    ):

        return ROUTE_LEDS.get(
            route_name,
            []
        )

    # ==================================================
    # FAHRSTRASSE DAUERHAFT EIN
    # ==================================================

    def route_on(
        self,
        route_name
    ):

        # ----------------------------------------------
        # Blinkthread stoppen
        # ----------------------------------------------

        self.stop_blink()

        leds = self.route_leds_for(
            route_name
        )

        if not leds:

            print(
                f"Keine LEDs für Fahrstraße "
                f"{route_name}"
            )

            return

        # ----------------------------------------------
        # Fahrstraßen-LEDs einschalten
        # ----------------------------------------------

        for led in leds:

            self.set(
                led,
                *YELLOW
            )

        self.show()

        print(
            f"Fahrstraßen-LEDs EIN: "
            f"{route_name} -> {leds}"
        )

    # ==================================================
    # FAHRSTRASSE BLINKEN
    # ==================================================

    def route_blink(
        self,
        route_name
    ):

        # ----------------------------------------------
        # Bereits laufendes Blinken stoppen
        # ----------------------------------------------

        self.stop_blink()

        leds = self.route_leds_for(
            route_name
        )

        if not leds:

            print(
                f"Keine LEDs für Fahrstraße "
                f"{route_name}"
            )

            return

        # ----------------------------------------------
        # Stop-Event zurücksetzen
        # ----------------------------------------------

        self.blink_stop_event.clear()

        # ----------------------------------------------
        # Blinkthread
        # ----------------------------------------------

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

                # 500 ms EIN / AUS
                #
                # wait() statt sleep(), damit der
                # Thread beim Stoppen sofort
                # reagieren kann.
                self.blink_stop_event.wait(
                    0.5
                )

        self.blink_thread = threading.Thread(
            target=blink,
            daemon=True
        )

        self.blink_thread.start()

        print(
            f"Fahrstraßen-LEDs BLINKEN: "
            f"{route_name} -> {leds}"
        )

    # ==================================================
    # BLINKEN STOPPEN
    # ==================================================

    def stop_blink(self):

        self.blink_stop_event.set()

        if self.blink_thread:

            self.blink_thread.join(
                timeout=1
            )

            self.blink_thread = None

    # ==================================================
    # FAHRSTRASSE AUS
    # ==================================================

    def route_off(
        self,
        route_name
    ):

        leds = self.route_leds_for(
            route_name
        )

        for led in leds:

            self.set(
                led,
                *OFF
            )

        self.show()

        print(
            f"Fahrstraßen-LEDs AUS: "
            f"{route_name}"
        )

    # ==================================================
    # ALLE FAHRSTRASSEN AUS
    # ==================================================

    def all_routes_off(self):

        for leds in ROUTE_LEDS.values():

            for led in leds:

                self.set(
                    led,
                    *OFF
                )

        self.show()

    # ==================================================
    # BEENDEN
    # ==================================================

    def shutdown(self):

        print(
            "LEDs werden ausgeschaltet..."
        )

        self.stop_blink()

        self.all_off()