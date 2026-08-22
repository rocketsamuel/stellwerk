import time
import threading

from config import (
    BUTTON_PINS,
    ROUTES,
    ROUTE_TIMEOUT,
)

from z21 import Z21
from switches import SwitchController
from leds import LEDs


class Stellwerk:

    def __init__(self):

        self.z21 = Z21()

        self.switches = SwitchController(
            self.z21
        )

        self.leds = LEDs()

        self.running = False

        # -------------------------------------------------
        # Aktive Fahrstraßen
        # -------------------------------------------------

        self.active_routes = {}

        # -------------------------------------------------
        # Starttaster merken
        # -------------------------------------------------

        self.pending_start = None

        # -------------------------------------------------
        # GPIO-Taster
        # -------------------------------------------------

        self.buttons = {}

    # =====================================================
    # START
    # =====================================================

    def start(self):

        print()
        print("==============================")
        print("        STELLWERK")
        print("==============================")
        print()

        self.leds.start()

        # -------------------------------------------------
        # Z21 starten
        # -------------------------------------------------

        self.z21.start(
            self.on_z21_update
        )

        # -------------------------------------------------
        # Taster starten
        # -------------------------------------------------

        self.setup_buttons()

        self.running = True

        print()
        print("Stellwerk läuft.")
        print()

    # =====================================================
    # TASTER
    # =====================================================

    def setup_buttons(self):

        try:

            from gpiozero import Button

        except ImportError:

            print(
                "WARNUNG: gpiozero ist nicht "
                "installiert."
            )

            return

        for name, pin in BUTTON_PINS.items():

            if pin is None:
                continue

            try:

                button = Button(
                    pin,
                    pull_up=True,
                    bounce_time=0.05,
                )

                button.when_pressed = (
                    lambda n=name:
                    self.on_button(n)
                )

                self.buttons[name] = button

                print(
                    f"Taster {name} "
                    f"auf GPIO {pin} aktiviert."
                )

            except Exception as exc:

                print(
                    f"Fehler bei Taster "
                    f"{name}: {exc}"
                )

    # =====================================================
    # TASTER GEDRÜCKT
    # =====================================================

    def on_button(
        self,
        button_name,
    ):

        print()
        print(
            f"Taster gedrückt: "
            f"{button_name}"
        )

        # -------------------------------------------------
        # ABS0 = Fahrstraßen auflösen
        # -------------------------------------------------

        if button_name == "ABS0":

            self.resolve_all_routes()

            return

        # -------------------------------------------------
        # Aktiven Startpunkt merken
        # -------------------------------------------------

        if self.pending_start is None:

            self.pending_start = button_name

            print(
                f"Startpunkt gewählt: "
                f"{button_name}"
            )

            return

        # -------------------------------------------------
        # Zweiten Taster = Ziel
        # -------------------------------------------------

        start = self.pending_start

        target = button_name

        self.pending_start = None

        self.request_route(
            start,
            target
        )

    # =====================================================
    # FAHRSTRASSE SUCHEN
    # =====================================================

    def find_route(
        self,
        start,
        target,
    ):

        for route_name, route in ROUTES.items():

            if (
                route.get("start") == start
                and
                route.get("target") == target
            ):

                return route_name

        return None

    # =====================================================
    # FAHRSTRASSE ANFORDERN
    # =====================================================

    def request_route(
        self,
        start,
        target,
    ):

        print()
        print(
            f"Fahrstraße: "
            f"{start} -> {target}"
        )

        route_name = self.find_route(
            start,
            target
        )

        if route_name is None:

            print(
                "Keine passende Fahrstraße "
                "gefunden."
            )

            return

        # -------------------------------------------------
        # Bereits aktiv?
        # -------------------------------------------------

        if route_name in self.active_routes:

            print(
                f"Fahrstraße {route_name} "
                f"ist bereits aktiv."
            )

            return

        route = ROUTES[route_name]

        # -------------------------------------------------
        # Fahrstraße schalten
        # -------------------------------------------------

        print(
            f"Stelle Fahrstraße "
            f"{route_name}"
        )

        switches = route.get(
            "switches",
            {}
        )

        # -------------------------------------------------
        # Alle benötigten Weichen stellen
        # -------------------------------------------------

        for (
            switch_name,
            position
        ) in switches.items():

            try:

                self.switches.command(
                    switch_name,
                    position
                )

            except Exception as exc:

                print(
                    f"Fehler beim Stellen "
                    f"von {switch_name}: "
                    f"{exc}"
                )

                return

        # -------------------------------------------------
        # Aktive Fahrstraße merken
        # -------------------------------------------------

        self.active_routes[
            route_name
        ] = {
            "start": start,
            "target": target,
            "switches": dict(
                switches
            ),
            "created": time.monotonic(),
        }

        # -------------------------------------------------
        # LED-Anzeige erst nach Bestätigung
        # -------------------------------------------------

        print(
            "Warte auf Bestätigung "
            "der Weichen..."
        )

        threading.Thread(
            target=self.wait_for_route,
            args=(route_name,),
            daemon=True,
        ).start()

    # =====================================================
    # AUF WEICHENBESTÄTIGUNG WARTEN
    # =====================================================

    def wait_for_route(
        self,
        route_name,
    ):

        route_data = self.active_routes.get(
            route_name
        )

        if route_data is None:
            return

        required = route_data[
            "switches"
        ]

        start_time = time.monotonic()

        # -------------------------------------------------
        # Warten
        # -------------------------------------------------

        while self.running:

            all_correct = True

            for (
                switch_name,
                position
            ) in required.items():

                if not self.switches.is_position(
                    switch_name,
                    position
                ):

                    all_correct = False

                    break

            if all_correct:

                print(
                    f"Fahrstraße "
                    f"{route_name} "
                    f"bestätigt."
                )

                self.leds.set_route(
                    route_name
                )

                return

            # Timeout
            if (
                time.monotonic()
                - start_time
                > ROUTE_TIMEOUT
            ):

                print(
                    f"Timeout bei "
                    f"Fahrstraße "
                    f"{route_name}"
                )

                self.resolve_route(
                    route_name
                )

                return

            time.sleep(0.05)

    # =====================================================
    # Z21-RÜCKMELDUNG
    # =====================================================

    def on_z21_update(
        self,
        address,
        position,
    ):

        # -------------------------------------------------
        # Weichencontroller aktualisieren
        # -------------------------------------------------

        switch_name = self.switches.update(
            address,
            position
        )

        if switch_name is None:
            return

        logical_position = (
            self.switches.get_position(
                switch_name
            )
        )

        # -------------------------------------------------
        # Weichen-LED aktualisieren
        # -------------------------------------------------

        if logical_position is not None:

            self.leds.set_switch_state(
                switch_name,
                logical_position
            )

        # -------------------------------------------------
        # Aktive Fahrstraßen überwachen
        # -------------------------------------------------

        self.check_active_routes()

    # =====================================================
    # AKTIVE FAHRSTRASSEN PRÜFEN
    # =====================================================

    def check_active_routes(self):

        for route_name in list(
            self.active_routes.keys()
        ):

            route_data = (
                self.active_routes.get(
                    route_name
                )
            )

            if route_data is None:
                continue

            required = route_data[
                "switches"
            ]

            for (
                switch_name,
                required_position
            ) in required.items():

                actual_position = (
                    self.switches.get_position(
                        switch_name
                    )
                )

                # -------------------------------------------------
                # Noch keine bestätigte Stellung
                # -------------------------------------------------

                if actual_position is None:

                    continue

                # -------------------------------------------------
                # Falsche Stellung
                # -------------------------------------------------

                if (
                    actual_position
                    != required_position
                ):

                    print()
                    print(
                        "!!! FAHRSTRASSENFEHLER !!!"
                    )

                    print(
                        f"Fahrstraße: "
                        f"{route_name}"
                    )

                    print(
                        f"Weiche: "
                        f"{switch_name}"
                    )

                    print(
                        f"Erwartet: "
                        f"{required_position}"
                    )

                    print(
                        f"Tatsächlich: "
                        f"{actual_position}"
                    )

                    # -------------------------------------------------
                    # 5x rot blinken
                    # -------------------------------------------------

                    self.leds.flash_route_red(
                        route_name,
                        count=5
                    )

                    # -------------------------------------------------
                    # Fahrstraße auflösen
                    # -------------------------------------------------

                    self.resolve_route(
                        route_name
                    )

                    break

    # =====================================================
    # EINE FAHRSTRASSE AUFLÖSEN
    # =====================================================

    def resolve_route(
        self,
        route_name,
    ):

        if route_name not in self.active_routes:
            return

        print(
            f"Fahrstraße "
            f"{route_name} "
            f"wird aufgelöst."
        )

        self.leds.clear_route(
            route_name
        )

        del self.active_routes[
            route_name
        ]

    # =====================================================
    # ALLE FAHRSTRASSEN AUFLÖSEN
    # =====================================================

    def resolve_all_routes(self):

        print()
        print(
            "Alle Fahrstraßen werden "
            "aufgelöst."
        )

        for route_name in list(
            self.active_routes.keys()
        ):

            self.resolve_route(
                route_name
            )

    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        self.running = False

        print()
        print(
            "Stellwerk wird beendet..."
        )

        self.resolve_all_routes()

        for button in self.buttons.values():

            try:
                button.close()
            except Exception:
                pass

        self.z21.stop()

        self.leds.stop()

    # =====================================================
    # HAUPTSCHLEIFE
    # =====================================================

    def run(self):

        self.start()

        try:

            while self.running:

                time.sleep(0.5)

        except KeyboardInterrupt:

            print()
            print(
                "Strg+C erkannt."
            )

        finally:

            self.stop()


# =========================================================
# MAIN
# =========================================================

def main():

    stellwerk = Stellwerk()

    stellwerk.run()


if __name__ == "__main__":

    main()