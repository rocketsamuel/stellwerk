import threading
import time

from rpi_ws281x import PixelStrip, Color

from config import (
    LED_COUNT,
    LED_PIN,
    LED_BRIGHTNESS,
    SWITCH_LEDS,
    ROUTE_LEDS,
)


class LEDs:

    def __init__(self):

        self.strip = PixelStrip(
            LED_COUNT,
            LED_PIN,
            800000,
            10,
            False,
            LED_BRIGHTNESS,
            0,
        )

        self.running = False

        self.lock = threading.Lock()

        # Aktuelle logische Zustände
        self.switch_states = {}
        self.route_states = {}

        # Blinkthreads
        self.blink_threads = {}
        self.blink_stop_events = {}

    # =====================================================
    # START
    # =====================================================

    def start(self):

        self.strip.begin()

        self.running = True

        self.clear()

        print("LEDs gestartet.")

    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        self.running = False

        # Alle Blinkthreads stoppen
        for event in self.blink_stop_events.values():
            event.set()

        self.blink_stop_events.clear()
        self.blink_threads.clear()

        self.clear()

    # =====================================================
    # LED SETZEN
    # =====================================================

    def set_pixel(
        self,
        led,
        color,
    ):

        if led < 1 or led > LED_COUNT:
            print(
                f"Warnung: LED {led} "
                f"liegt außerhalb des Bereichs."
            )
            return

        with self.lock:

            self.strip.setPixelColor(
                led - 1,
                color
            )

            self.strip.show()

    # =====================================================
    # LED AUSSCHALTEN
    # =====================================================

    def off(
        self,
        led,
    ):

        self.set_pixel(
            led,
            Color(0, 0, 0)
        )

    # =====================================================
    # ALLE LEDS AUS
    # =====================================================

    def clear(self):

        with self.lock:

            for i in range(LED_COUNT):

                self.strip.setPixelColor(
                    i,
                    Color(0, 0, 0)
                )

            self.strip.show()

    # =====================================================
    # WEICHENSTELLUNG ANZEIGEN
    # =====================================================

    def set_switch_state(
        self,
        switch_name,
        position,
    ):

        if switch_name not in SWITCH_LEDS:
            return

        positions = SWITCH_LEDS[switch_name]

        # -------------------------------------------------
        # Alte Anzeige der Weiche ausschalten
        # -------------------------------------------------

        for led in positions.values():

            self.off(led)

        # -------------------------------------------------
        # Neue Stellung einschalten
        # -------------------------------------------------

        if position not in positions:

            print(
                f"Keine LED-Zuordnung für "
                f"{switch_name} -> {position}"
            )

            return

        led = positions[position]

        self.set_pixel(
            led,
            Color(0, 255, 0)
        )

        self.switch_states[switch_name] = position

        print(
            f"LED: {switch_name} -> "
            f"{position} (LED {led})"
        )

    # =====================================================
    # FAHRSTRASSEN-LEDS
    # =====================================================

    def set_route(
        self,
        route_name,
    ):

        if route_name not in ROUTE_LEDS:
            return

        # Alte Routeanzeige ggf. überschreiben
        self.route_states[route_name] = "active"

        for led in ROUTE_LEDS[route_name]:

            self.set_pixel(
                led,
                Color(0, 255, 0)
            )

    # =====================================================
    # FAHRSTRASSE AUS
    # =====================================================

    def clear_route(
        self,
        route_name,
    ):

        if route_name not in ROUTE_LEDS:
            return

        self.route_states[route_name] = "off"

        for led in ROUTE_LEDS[route_name]:

            self.off(led)

    # =====================================================
    # FAHRSTRASSE ROT BLINKEN
    # =====================================================

    def flash_route_red(
        self,
        route_name,
        count=5,
        interval=0.25,
    ):

        if route_name not in ROUTE_LEDS:
            return

        # Falls bereits ein Blinkthread läuft,
        # diesen zuerst stoppen.
        self.stop_route_blink(
            route_name
        )

        stop_event = threading.Event()

        self.blink_stop_events[
            route_name
        ] = stop_event

        def worker():

            leds = ROUTE_LEDS[route_name]

            for _ in range(count):

                if stop_event.is_set():
                    return

                # ROT EIN
                for led in leds:

                    self.set_pixel(
                        led,
                        Color(255, 0, 0)
                    )

                time.sleep(interval)

                if stop_event.is_set():
                    return

                # AUS
                for led in leds:

                    self.off(led)

                time.sleep(interval)

            # Nach dem Blinken endgültig aus
            for led in leds:

                self.off(led)

            self.route_states[
                route_name
            ] = "off"

            self.blink_stop_events.pop(
                route_name,
                None
            )

            self.blink_threads.pop(
                route_name,
                None
            )

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        self.blink_threads[
            route_name
        ] = thread

        thread.start()

    # =====================================================
    # BLINKEN STOPPEN
    # =====================================================

    def stop_route_blink(
        self,
        route_name,
    ):

        event = self.blink_stop_events.get(
            route_name
        )

        if event:
            event.set()

    # =====================================================
    # LED-TEST
    # =====================================================

    def test_all(
        self,
        delay=0.2,
    ):

        print(
            "LED-Test: alle LEDs einschalten."
        )

        with self.lock:

            for i in range(LED_COUNT):

                self.strip.setPixelColor(
                    i,
                    Color(255, 0, 0)
                )

            self.strip.show()

        time.sleep(delay)

        with self.lock:

            for i in range(LED_COUNT):

                self.strip.setPixelColor(
                    i,
                    Color(0, 255, 0)
                )

            self.strip.show()

        time.sleep(delay)

        with self.lock:

            for i in range(LED_COUNT):

                self.strip.setPixelColor(
                    i,
                    Color(0, 0, 255)
                )

            self.strip.show()

        time.sleep(delay)

        self.clear()

    # =====================================================
    # LED-TEST EINZELNE LED
    # =====================================================

    def test_switch(
        self,
        switch_name,
    ):

        if switch_name not in SWITCH_LEDS:
            print(
                f"Keine LED-Konfiguration für "
                f"{switch_name}"
            )
            return

        positions = SWITCH_LEDS[
            switch_name
        ]

        for position, led in positions.items():

            print(
                f"{switch_name}: "
                f"{position} -> LED {led}"
            )

            self.set_pixel(
                led,
                Color(0, 255, 0)
            )

            time.sleep(1)

            self.off(led)

    # =====================================================
    # ENDE
    # =====================================================

    def __del__(self):

        try:
            self.clear()
        except Exception:
            pass