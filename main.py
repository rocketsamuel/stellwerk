import time

from config import (
    BUTTON_PINS,
    ROUTE_TIMEOUT,
    ROUTE_MIN_BLINK_TIME,
    LED_COUNT,
)

from z21 import Z21
from switches import SwitchController
from routes import find_route
from leds import LEDs
from buttons import Buttons


class Stellwerk:

    def __init__(self):

        self.z21 = Z21()

        self.switches = SwitchController(
            self.z21
        )

        self.leds = LEDs()

        self.buttons = None

        self.selected_start = None
        self.requested_route = None
        self.active_route = None

        # Verhindert, dass während einer
        # Fehleranzeige eine neue Fahrstraße
        # gestartet wird.
        self.route_error_active = False

    # ==================================================
    # START
    # ==================================================

    def start(self):

        print()
        print("==============================")
        print("        STELLWERK")
        print("==============================")
        print()

        # ----------------------------------------------
        # LEDs
        # ----------------------------------------------

        self.leds.start()

        # ----------------------------------------------
        # Z21
        # ----------------------------------------------

        self.z21.start(
            self.on_z21_change
        )

        # ----------------------------------------------
        # Taster
        # ----------------------------------------------

        self.buttons = Buttons(
            BUTTON_PINS,
            self.on_button
        )

        print(
            "Stellwerk gestartet."
        )

        print()

    # ==================================================
    # Z21 RÜCKMELDUNG
    # ==================================================

    def on_z21_change(
        self,
        address,
        position
    ):

        print(
            f"Z21: Adresse {address} -> {position}"
        )

        # ----------------------------------------------
        # Z21-Adresse einer logischen Weiche
        # zuordnen
        # ----------------------------------------------

        switch_name = self.switches.update(
            address,
            position
        )

        # ----------------------------------------------
        # Weichen-LED aktualisieren
        # ----------------------------------------------

        if switch_name:

            self.leds.switch_position(
                switch_name,
                position
            )

        # ----------------------------------------------
        # Prüfen, ob eine aktive Fahrstraße
        # durch diese Änderung verletzt wurde.
        # ----------------------------------------------

        if (
            switch_name
            and self.active_route
            and not self.route_error_active
        ):

            self.check_active_route_after_change(
                switch_name
            )

        # ----------------------------------------------
        # Status
        # ----------------------------------------------

        for (
            name,
            state
        ) in self.switches.states.items():

            print(
                f"     {name} = {state}"
            )

    # ==================================================
    # AKTIVE FAHRSTRASSE NACH WEICHENÄNDERUNG PRÜFEN
    # ==================================================

    def check_active_route_after_change(
        self,
        switch_name
    ):

        # ----------------------------------------------
        # Aktive Fahrstraße aus config/routes holen
        # ----------------------------------------------

        name, route = find_route_by_name(
            self.active_route
        )

        if route is None:

            print(
                f"Fahrstraße "
                f"{self.active_route} "
                f"nicht gefunden."
            )

            return

        # ----------------------------------------------
        # Gehört die geänderte Weiche überhaupt
        # zur aktiven Fahrstraße?
        # ----------------------------------------------

        required_switches = (
            route.get(
                "switches",
                {}
            )
        )

        if switch_name not in required_switches:

            return

        expected_position = (
            required_switches[
                switch_name
            ]
        )

        current_position = (
            self.switches.states.get(
                switch_name
            )
        )

        print()
        print(
            "Überprüfung aktive Fahrstraße:"
        )

        print(
            f"  Fahrstraße: "
            f"{self.active_route}"
        )

        print(
            f"  Weiche: "
            f"{switch_name}"
        )

        print(
            f"  Erwartet: "
            f"{expected_position}"
        )

        print(
            f"  Aktuell: "
            f"{current_position}"
        )

        # ----------------------------------------------
        # Stellung weiterhin korrekt
        # ----------------------------------------------

        if (
            current_position
            == expected_position
        ):

            print(
                "  -> Stellung weiterhin korrekt."
            )

            return

        # ----------------------------------------------
        # FALSCHE STELLUNG
        # ----------------------------------------------

        print()
        print(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )
        print(
            "FAHRSTRASSENFEHLER"
        )
        print(
            f"Weiche {switch_name} "
            f"wurde während der aktiven "
            f"Fahrstraße falsch gestellt."
        )
        print(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )
        print()

        self.handle_route_error()

    # ==================================================
    # FAHRSTRASSENFEHLER
    # ==================================================

    def handle_route_error(self):

        if not self.active_route:

            return

        if self.route_error_active:

            return

        # ----------------------------------------------
        # Sofort blockieren
        # ----------------------------------------------

        self.route_error_active = True

        route_name = self.active_route

        print(
            f"Fahrstraße {route_name} "
            f"wird wegen falscher "
            f"Weichenstellung aufgelöst."
        )

        # ----------------------------------------------
        # ROTE FEHLERANZEIGE
        #
        # Wichtig:
        # Diese Funktion ist blockierend.
        # Während der 3 Blinkimpulse wird
        # keine neue Fahrstraße angenommen.
        # ----------------------------------------------

        self.leds.route_error(
            route_name
        )

        # ----------------------------------------------
        # Danach Fahrstraße auflösen
        # ----------------------------------------------

        self.active_route = None
        self.requested_route = None
        self.selected_start = None

        # ----------------------------------------------
        # Fahrstraßen-LEDs sind durch route_error()
        # bereits ausgeschaltet.
        #
        # Weichen-LEDs bleiben unverändert.
        # ----------------------------------------------

        self.route_error_active = False

        print()
        print(
            "Fahrstraße wurde aufgelöst."
        )
        print()

    # ==================================================
    # TASTER
    # ==================================================

    def on_button(
        self,
        name
    ):

        print(
            f"Taster gedrückt: {name}"
        )

        # ----------------------------------------------
        # Fehleranzeige aktiv
        # ----------------------------------------------

        if self.route_error_active:

            print(
                "Momentan keine neue "
                "Fahrstraße möglich."
            )

            return

        # ----------------------------------------------
        # Fahrstraße aktiv
        # ----------------------------------------------

        if self.active_route:

            print(
                f"Fahrstraße "
                f"{self.active_route} ist aktiv."
            )

            return

        # ----------------------------------------------
        # Fahrstraße wird gerade angefordert
        # ----------------------------------------------

        if self.requested_route:

            print(
                f"Fahrstraße "
                f"{self.requested_route} "
                f"wird gerade gestellt."
            )

            return

        # ----------------------------------------------
        # Erster Taster = Start
        # ----------------------------------------------

        if self.selected_start is None:

            self.selected_start = name

            print(
                f"Start gewählt: {name}"
            )

            return

        # ----------------------------------------------
        # Zweiter Taster = Ziel
        # ----------------------------------------------

        start = self.selected_start
        target = name

        self.selected_start = None

        self.request_route(
            start,
            target
        )

    # ==================================================
    # FAHRSTRASSE ANFORDERN
    # ==================================================

    def request_route(
        self,
        start,
        target
    ):

        # ----------------------------------------------
        # Sicherheitsprüfung
        # ----------------------------------------------

        if self.route_error_active:

            print(
                "Fahrstraße momentan gesperrt."
            )

            return False

        if self.active_route:

            print(
                f"Fahrstraße "
                f"{self.active_route} ist bereits aktiv."
            )

            return False

        if self.requested_route:

            print(
                f"Fahrstraße "
                f"{self.requested_route} "
                f"wird bereits gestellt."
            )

            return False

        # ----------------------------------------------
        # Fahrstraße suchen
        # ----------------------------------------------

        name, route = find_route(
            start,
            target
        )

        if route is None:

            print()
            print(
                f"Keine Fahrstraße "
                f"{start} -> {target}"
            )
            print()

            return False

        print()
        print("==============================")
        print(
            "Fahrstraße angefordert:"
        )
        print(
            f"{start} -> {target}"
        )
        print(
            f"Name: {name}"
        )
        print("==============================")
        print()

        self.requested_route = name

        # ----------------------------------------------
        # Fahrstraßen-LEDs blinken
        # ----------------------------------------------

        print(
            "Fahrstraßen-LEDs blinken..."
        )

        self.leds.route_blink(
            name
        )

        # Zeitpunkt des Blinkstarts
        blink_started = time.monotonic()

        # ----------------------------------------------
        # WEICHEN STELLEN
        # ----------------------------------------------

        try:

            for (
                switch_name,
                position
            ) in route["switches"].items():

                print(
                    f"Weiche stellen: "
                    f"{switch_name} -> "
                    f"{position}"
                )

                self.switches.command(
                    switch_name,
                    position
                )

        except Exception as error:

            print()
            print(
                "FEHLER beim Stellen "
                "der Weichen:"
            )
            print(error)

            self.leds.stop_blink()

            self.leds.route_off(
                name
            )

            self.requested_route = None

            return False

        # ----------------------------------------------
        # AUF RÜCKMELDUNG WARTEN
        # ----------------------------------------------

        print()
        print(
            "Warte auf "
            "Weichen-Rückmeldungen..."
        )

        deadline = (
            time.monotonic()
            + ROUTE_TIMEOUT
        )

        # ----------------------------------------------
        # PRÜFSCHLEIFE
        # ----------------------------------------------

        while (
            time.monotonic()
            < deadline
        ):

            if self.route_is_correct(
                route
            ):

                # --------------------------------------
                # Mindest-Blinkzeit
                # --------------------------------------

                elapsed = (
                    time.monotonic()
                    - blink_started
                )

                if (
                    elapsed
                    < ROUTE_MIN_BLINK_TIME
                ):

                    remaining = (
                        ROUTE_MIN_BLINK_TIME
                        - elapsed
                    )

                    time.sleep(
                        remaining
                    )

                # --------------------------------------
                # Fahrstraße aktivieren
                # --------------------------------------

                self.requested_route = None
                self.active_route = name

                self.leds.route_on(
                    name
                )

                print()
                print("==============================")
                print(
                    f"FAHRSTRASSE AKTIV: {name}"
                )
                print("==============================")
                print()

                return True

            time.sleep(
                0.05
            )

        # ==================================================
        # TIMEOUT
        # ==================================================

        print()
        print(
            "FEHLER: Die Weichen wurden "
            "nicht innerhalb des Timeouts "
            "korrekt zurückgemeldet."
        )

        print()
        print(
            "Aktueller Weichenstatus:"
        )

        self.switches_status()

        self.leds.stop_blink()

        self.leds.route_off(
            name
        )

        self.requested_route = None

        return False

    # ==================================================
    # FAHRSTRASSE PRÜFEN
    # ==================================================

    def route_is_correct(
        self,
        route
    ):

        for (
            switch_name,
            expected_position
        ) in route["switches"].items():

            current_position = (
                self.switches.states.get(
                    switch_name
                )
            )

            print(
                f"Prüfe {switch_name}: "
                f"erwartet={expected_position}, "
                f"aktuell={current_position}"
            )

            if current_position is None:

                return False

            if (
                current_position
                != expected_position
            ):

                return False

        return True

    # ==================================================
    # FAHRSTRASSE AUFLÖSEN
    # ==================================================

    def release_route(self):

        if not self.active_route:

            print(
                "Keine Fahrstraße aktiv."
            )

            return

        route_name = self.active_route

        print()
        print(
            f"Fahrstraße aufgelöst: "
            f"{route_name}"
        )

        self.active_route = None
        self.requested_route = None
        self.selected_start = None

        self.leds.stop_blink()

        self.leds.route_off(
            route_name
        )

    # ==================================================
    # WEICHENSTATUS
    # ==================================================

    def switches_status(self):

        if not self.switches.states:

            print(
                "  Keine Weichenstellungen bekannt."
            )

            return

        for (
            name,
            position
        ) in self.switches.states.items():

            print(
                f"  {name}: {position}"
            )

    # ==================================================
    # STATUS
    # ==================================================

    def status(self):

        print()
        print("==============================")
        print("STATUS")
        print("==============================")

        print()
        print("Weichen:")

        self.switches_status()

        print()
        print(
            f"Startauswahl: "
            f"{self.selected_start}"
        )

        print(
            f"Angefordert: "
            f"{self.requested_route}"
        )

        print(
            f"Aktiv: "
            f"{self.active_route}"
        )

        print(
            f"Fehleranzeige: "
            f"{self.route_error_active}"
        )

        print()

    # ==================================================
    # BEENDEN
    # ==================================================

    def stop(self):

        print()
        print(
            "Stellwerk wird beendet..."
        )

        if self.buttons:

            self.buttons.close()

        self.z21.stop()

        self.leds.shutdown()

        print(
            "Stellwerk beendet."
        )


# ======================================================
# KONSOLENSTEUERUNG
# ======================================================

def console_mode(
    stellwerk
):

    print(
        "Konsolenbefehle:"
    )

    print(
        "  route <start> <ziel>"
    )

    print(
        "  start <name>"
    )

    print(
        "  ledtest"
    )

    print(
        "  status"
    )

    print(
        "  release"
    )

    print(
        "  quit"
    )

    print()

    while True:

        try:

            command = input(
                "stellwerk> "
            ).strip()

        except EOFError:

            return False

        if not command:

            continue

        parts = command.split()

        # ==================================================
        # LEDTEST
        # ==================================================

        if command == "ledtest":

            print(
                "LED-Test: "
                "alle LEDs werden gelb eingeschaltet."
            )

            stellwerk.leds.stop_blink()

            stellwerk.leds.all_off()

            for led in range(
                1,
                LED_COUNT + 1
            ):

                stellwerk.leds.set(
                    led,
                    255,
                    180,
                    0
                )

            stellwerk.leds.show()

            print(
                f"Alle {LED_COUNT} LEDs "
                "sollten jetzt gelb leuchten."
            )

            continue

        # ==================================================
        # STATUS
        # ==================================================

        if command == "status":

            stellwerk.status()

            continue

        # ==================================================
        # RELEASE
        # ==================================================

        if command == "release":

            stellwerk.release_route()

            continue

        # ==================================================
        # QUIT
        # ==================================================

        if command == "quit":

            return False

        # ==================================================
        # START
        # ==================================================

        if (
            len(parts) == 2
            and parts[0] == "start"
        ):

            stellwerk.selected_start = (
                parts[1]
            )

            print(
                f"Start gewählt: "
                f"{parts[1]}"
            )

            continue

        # ==================================================
        # ROUTE
        # ==================================================

        if (
            len(parts) == 3
            and parts[0] == "route"
        ):

            stellwerk.request_route(
                parts[1],
                parts[2]
            )

            continue

        # ==================================================
        # UNBEKANNTER BEFEHL
        # ==================================================

        print(
            "Unbekannter Befehl."
        )

        print()
        print(
            "Mögliche Befehle:"
        )

        print(
            "  route <start> <ziel>"
        )

        print(
            "  start <name>"
        )

        print(
            "  ledtest"
        )

        print(
            "  status"
        )

        print(
            "  release"
        )

        print(
            "  quit"
        )

        print()


# ======================================================
# FAHRSTRASSE ANHAND DES NAMENS SUCHEN
# ======================================================

def find_route_by_name(
    route_name
):

    from config import ROUTES

    route = ROUTES.get(
        route_name
    )

    if route is None:

        return None, None

    return route_name, route


# ======================================================
# MAIN
# ======================================================

def main():

    stellwerk = Stellwerk()

    try:

        stellwerk.start()

        console_mode(
            stellwerk
        )

    except KeyboardInterrupt:

        print()
        print(
            "Abbruch durch Benutzer."
        )

    except Exception as error:

        print()
        print("==============================")
        print("FEHLER")
        print("==============================")
        print(error)
        print()

        raise

    finally:

        stellwerk.stop()


# ======================================================
# PROGRAMMSTART
# ======================================================

if __name__ == "__main__":

    main()