```python
import threading
import time
import os

from config import (
    LED_COUNT,
    LED_PIN,
    LED_BRIGHTNESS,
    SWITCH_LEDS,
    ROUTE_LEDS,
    BLINK_INTERVAL,
)


# ======================================================
# RP1 WS2812B PWM DEVICE
# ======================================================

WS281X_DEVICE = "/dev/ws281x_pwm"


# ======================================================
# FARBEN
# ======================================================

YELLOW = (255, 180, 0)
RED = (255, 0, 0)
OFF = (0, 0, 0)


class LEDs:

    def __init__(self):

        self.fd = None

        self.blink_thread = None
        self.blink_stop_event = threading.Event()

        # Lokaler LED-Puffer.
        #
        # set() verändert nur den Puffer.
        # show() überträgt den kompletten Puffer.
        #
        # Die Farbreihenfolge wird erst beim Erzeugen
        # des Datenstroms auf GRB umgesetzt.
        self.pixels = [
            OFF
            for _ in range(LED_COUNT)
        ]

    # ==================================================
    # WS2812B BYTE ENCODIEREN
    # ==================================================

    @staticmethod
    def _encode_byte(value):

        """
        Erzeugt aus einem 8-Bit-Wert acht 32-Bit-PWM-Werte.

        PWM-Takt:
            25.6 MHz

        PWM-Periode:
            32 Takte = 1.25 us

        WS2812B:
            0 -> ca. 0.39 us HIGH
            1 -> ca. 0.78 us HIGH

        Deshalb:
            0 = 10 Takte
            1 = 20 Takte

        Der RP1-Treiber sendet jedes 32-Bit-Wort über
        die PWM-Duty-FIFO.
        """

        value = max(
            0,
            min(255, int(value))
        )

        result = bytearray()

        for bit in range(7, -1, -1):

            if value & (1 << bit):

                # WS2812 logical 1
                duty = 20

            else:

                # WS2812 logical 0
                duty = 10

            result += duty.to_bytes(
                4,
                byteorder="little",
                signed=False
            )

        return result

    # ==================================================
    # WS2812B FRAME ERZEUGEN
    # ==================================================

    def _build_frame(self):

        data = bytearray()

        for r, g, b in self.pixels:

            # WS2812B erwartet GRB
            data += self._encode_byte(g)
            data += self._encode_byte(r)
            data += self._encode_byte(b)

        # --------------------------------------------------
        # RESET / LATCH
        #
        # 128 Bytes = 32 PWM-Worte
        # 32 * 1.25 us = 40 us LOW
        #
        # Damit ist die erforderliche WS2812B-Latch-Zeit
        # sicher länger als 50 us.
        #
        # Der letzte DMA-Wert ist 0 und nach dem Ende des
        # Transfers bleibt die PWM-Leitung LOW.
        # --------------------------------------------------

        data += bytes(128)

        return bytes(data)

    # ==================================================
    # START
    # ==================================================

    def start(self):

        print(
            f"Öffne WS2812B Device: "
            f"{WS281X_DEVICE}"
        )

        self.fd = os.open(
            WS281X_DEVICE,
            os.O_WRONLY
        )

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
                f"Ungültige LED-Nummer: {led} "
                f"(erlaubt: 1-{LED_COUNT})"
            )

        # --------------------------------------------------
        # Helligkeit wie bei PixelStrip berücksichtigen.
        #
        # 0   = aus
        # 255 = volle Helligkeit
        # --------------------------------------------------

        brightness = max(
            0,
            min(255, LED_BRIGHTNESS)
        )

        r = int(r * brightness / 255)
        g = int(g * brightness / 255)
        b = int(b * brightness / 255)

        self.pixels[led - 1] = (
            r,
            g,
            b
        )

    # ==================================================
    # LED-STRIP AKTUALISIEREN
    # ==================================================

    def show(self):

        if self.fd is None:

            raise RuntimeError(
                "WS2812B Device ist nicht gestartet"
            )

        data = self._build_frame()

        total = 0

        while total < len(data):

            written = os.write(
                self.fd,
                data[total:]
            )

            if written <= 0:

                raise RuntimeError(
                    "Fehler beim Schreiben "
                    "auf WS2812B Device"
                )

            total += written

    # ==================================================
    # ALLE LEDs AUS
    # ==================================================

    def all_off(self):

        self.stop_blink()

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
        # LED der aktuellen Stellung ermitteln
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
                    BLINK_INTERVAL
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
    # FAHRSTRASSE: KURZ ROT AUFBLINKEN
    #
    # Wird verwendet, wenn bereits eine andere
    # Fahrstraße aktiv ist und der Bediener versucht,
    # eine weitere Fahrstraße einzustellen.
    #
    # Die aktive Fahrstraße bleibt anschließend
    # dauerhaft GELB.
    # ==================================================

    def route_flash_red(
        self,
        route_name
    ):

        leds = self.route_leds_for(
            route_name
        )

        if not leds:

            print(
                f"Keine LEDs für Fahrstraße "
                f"{route_name}"
            )

            return

        print(
            f"Fahrstraße {route_name}: "
            f"kurz ROT aufblinken"
        )

        # ----------------------------------------------
        # ROT EIN
        # ----------------------------------------------

        for led in leds:

            self.set(
                led,
                *RED
            )

        self.show()

        # ----------------------------------------------
        # Kurz warten
        # ----------------------------------------------

        time.sleep(
            BLINK_INTERVAL
        )

        # ----------------------------------------------
        # Danach wieder GELB
        # ----------------------------------------------

        for led in leds:

            self.set(
                led,
                *YELLOW
            )

        self.show()

    # ==================================================
    # FAHRSTRASSE: FEHLERANZEIGE
    #
    # 5x rot blinken
    # ==================================================

    def route_error(
        self,
        route_name
    ):

        # ----------------------------------------------
        # Normales Blinken stoppen
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

        print(
            f"FEHLERANZEIGE: "
            f"{route_name} -> 5x ROT"
        )

        # ----------------------------------------------
        # Fünfmal rot blinken
        # ----------------------------------------------

        for _ in range(5):

            # ROT EIN
            for led in leds:

                self.set(
                    led,
                    *RED
                )

            self.show()

            time.sleep(
                BLINK_INTERVAL
            )

            # AUS
            for led in leds:

                self.set(
                    led,
                    *OFF
                )

            self.show()

            time.sleep(
                BLINK_INTERVAL
            )

    # ==================================================
    # ALLE FAHRSTRASSEN AUS
    # ==================================================

    def all_routes_off(self):

        self.stop_blink()

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

        if self.fd is not None:

            try:

                self.all_off()

            finally:

                os.close(self.fd)

                self.fd = None
```
