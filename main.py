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

        # -------------------------------------------------
        # Fahrstraßenstatus
        # -------------------------------------------------

        self.selected_start = None

        self.requested_route = None

        self.active_route = None

        # -------------------------------------------------
        # Fehleranzeige
        # -------------------------------------------------

        self.route_error_active = False

    # =====================================================
    # START
    # =====================================================

    def start(self):

        print()
        print("==============================")
        print("        STELLWERK")
        print("==============================")
        print()

        # -------------------------------------------------
        # LEDs
        # -------------------------------------------------

        self.leds.start()

        # -------------------------------------------------
        # Z21
        # -------------------------------------------------

        self.z21.start(
            self.on_z21_change
        )

        # -------------------------------------------------
        # Taster
        # -------------------------------------------------

        self.buttons = Buttons(
            BUTTON_PINS,
            self.on_button
        )

        print()
        print(
            "Stellwerk gestartet."
        )
        print()

    # =====================================================
    # Z21 RÜCKMELDUNG
    # =====================================================

    def on_z21_change(
        self,
        address,
        position
    ):

        print(
            f"Z21: Adresse {address} -> {position}"
        )

        # -------------------------------------------------
        # Z21-Adresse einer logischen Weiche zuordnen
        # -------------------------------------------------

        result = self.switches.update(
            address,
            position
        )

        # -------------------------------------------------
        # Noch keine vollständige logische Stellung
        #
        # Das kann bei sw42 nach der ersten der beiden
        # Rückmeldungen passieren.
        # -------------------------------------------------

        if result is None:
            return

        switch_name, logical_position = result

        # -------------------------------------------------
        # Weichen-LED aktualisieren
        #
        # Wichtig:
        # Bei sw42 verwenden wir hier die LOGISCHE
        # Stellung left / straight / right.
        # -------------------------------------------------

        self.leds.switch_position(
            switch_name,
            logical_position
        )

        # -------------------------------------------------
        # Aktive Fahrstraße überwachen
        # -------------------------------------------------

        if (
            switch_name
            and self.active_route
            and not self.route_error_active
        ):

            self.check_active_route_after_change(
                switch_name
            )

        # -------------------------------------------------
        # Status ausgeben
        # -------------------------------------------------

        for (
            name,
            state
        ) in self.switches.states.items():

            print(
                f"     {name} = {state}"
            )

    # =====================================================
    # AKTIVE FAHRSTRASSE NACH WEICHENÄNDERUNG PRÜFEN
    # =====================================================

    def check_active_route_after_change(
        self,
        switch_name
    ):

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

        # -------------------------------------------------
        # Gehört die Weiche zur aktiven Fahrstraße?
        # -------------------------------------------------

        required_switches = route.get(
            "switches",
            {}
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

        # -------------------------------------------------
        # Stellung korrekt
        # -------------------------------------------------

        if current_position == expected_position:

            print(
                "  -> Stellung weiterhin korrekt."
            )

            return

        # -------------------------------------------------
        # FALSCHE STELLUNG
        # -------------------------------------------------

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

    # =====================================================
    # FAHRSTRASSENFEHLER
    # =====================================================

    def handle_route_error(self):

        if not self.active_route:
            return

        if self.route_error_active:
            return

        # -------------------------------------------------
        # Sofort sperren
        # -------------------------------------------------

        self.route_error_active = True

        route_name = self.active_route

        print(
            f"Fahrstraße {route_name} "
            f"wird wegen falscher "
            f"Weichenstellung aufgelöst."
        )

        # -------------------------------------------------
        # 5× rot blinken
        #
        # Deine aktuelle Einstellung:
        # leds.py -> range(5)
        # -------------------------------------------------

        self.leds.route_error(
            route_name
        )

        # -------------------------------------------------
        # Fahrstraße auflösen
        # -------------------------------------------------

        self.active_route = None

        self.requested_route = None

        self.selected_start = None

        # -------------------------------------------------
        # route_error() hat die
        # Fahrstraßen-LEDs bereits ausgeschaltet.
        #
        # Weichen-LEDs bleiben erhalten.
        # -------------------------------------------------

        self.route_error_active = False

        print()
        print(
            "Fahrstraße wurde aufgelöst."
        )
        print()

    # =====================================================
    # TASTER
    # =====================================================

    def on_button(
        self,
        name
    ):

        print()
        print(
            f"Taster gedrückt: {name}"
        )

        # -------------------------------------------------
        # AUFLÖSE-TASTER
        # -------------------------------------------------

        if name == "RELEASE":

            self.handle_release_button()

            return

        # -------------------------------------------------
        # Während Fehleranzeige keine Bedienung
        # -------------------------------------------------

        if self.route_error_active:

            print(
                "Momentan keine neue "
                "Fahrstraße möglich."
            )

            return

        # -------------------------------------------------
        # Fahrstraße bereits aktiv
        # -------------------------------------------------

        if self.active_route:

            print(
                f"Fahrstraße "
                f"{self.active_route} ist bereits aktiv."
            )

            print(
                "Neue Fahrstraße nicht möglich."
            )

            self.leds.route_flash_red(
                self.active_route
            )

            return

        # -------------------------------------------------
        # Fahrstraße wird gerade gestellt
        # -------------------------------------------------

        if self.requested_route:

            print(
                f"Fahrstraße "
                f"{self.requested_route} "
                f"wird gerade gestellt."
            )

            return

        # -------------------------------------------------
        # Erster Taster = Start
        # -------------------------------------------------

        if self.selected_start is None:

            self.selected_start = name

            print(
                f"Start gewählt: {name}"
            )

            return

        # -------------------------------------------------
        # Zweiter Taster = Ziel
        # -------------------------------------------------

        start = self.selected_start

        target = name

        self.selected_start = None

        self.request_route(
            start,
            target
        )

    # =====================================================
    # AUFLÖSE-TASTER
    # =====================================================

    def handle_release_button(self):

        # -------------------------------------------------
        # Fehleranzeige aktiv
        # -------------------------------------------------

        if self.route_error_active:

            print(
                "Fehleranzeige läuft."
            )

            print(
                "Auflösetaster momentan ohne Funktion."
            )

            return

        # -------------------------------------------------
        # Fahrstraße wird gerade gestellt
        # -------------------------------------------------

        if self.requested_route:

            print(
                "Fahrstraße wird gerade gestellt."
            )

            print(
                "Bitte auf Rückmeldung warten."
            )

            return

        # -------------------------------------------------
        # Keine aktive Fahrstraße
        # -------------------------------------------------

        if not self.active_route:

            print(
                "Keine Fahrstraße aktiv."
            )

            return

        # -------------------------------------------------
        # Fahrstraße auflösen
        # -------------------------------------------------

        print(
            f"Auflösetaster: "
            f"Fahrstraße "
            f"{self.active_route}"
        )

        self.release_route()

    # =====================================================
    # FAHRSTRASSE ANFORDERN
    # =====================================================

    def request_route(
        self,
        start,
        target
    ):

        # -------------------------------------------------
        # Sicherheitsprüfungen
        # -------------------------------------------------

        if self.route_error_active:

            print(
                "Fahrstraße momentan gesperrt."
            )

            return False

        if self.active_route:

            print(
                f"Fahrstraße "
                f"{self.active_route} "
                f"ist bereits aktiv."
            )

            return False

        if self.requested_route:

            print(
                f"Fahrstraße "
                f"{self.requested_route} "
                f"wird bereits gestellt."
            )

            return False

        # -------------------------------------------------
        # Fahrstraße suchen
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Fahrstraßen-LEDs blinken
        # -------------------------------------------------

        print(
            "Fahrstraßen-LEDs blinken..."
        )

        self.leds.route_blink(
            name
        )

        blink_started = time.monotonic()

        # -------------------------------------------------
        # WEICHEN STELLEN
        # -------------------------------------------------

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

        # -------------------------------------------------
        # AUF RÜCKMELDUNG WARTEN
        # -------------------------------------------------

        print()
        print(
            "Warte auf "
            "Weichen-Rückmeldungen..."
        )

        deadline = (
            time.monotonic()
            + ROUTE_TIMEOUT
        )

        # -------------------------------------------------
        # PRÜFSCHLEIFE
        # -------------------------------------------------

        while time.monotonic() < deadline:

            if self.route_is_correct(
                route
            ):

                # -----------------------------------------
                # Mindest-Blinkzeit
                # -----------------------------------------

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

                # -----------------------------------------
                # Fahrstraße aktivieren
                # -----------------------------------------

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

        # =================================================
        # TIMEOUT
        # =================================================

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

    # =====================================================
    # FAHRSTRASSE PRÜFEN
    # =====================================================

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

    # =====================================================
    # FAHRSTRASSE AUFLÖSEN
    # =====================================================

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

        # -------------------------------------------------
        # Status löschen
        # -------------------------------------------------

        self.active_route = None

        self.requested_route = None

        self.selected_start = None

        # -------------------------------------------------
        # Blinkmodus sicher beenden
        # -------------------------------------------------

        self.leds.stop_blink()

        # -------------------------------------------------
        # Fahrstraßen-LEDs ausschalten
        #
        # Weichen-LEDs bleiben erhalten.
        # -------------------------------------------------

        self.leds.route_off(
            route_name
        )

        print(
            "Fahrstraßen-LEDs ausgeschaltet."
        )

    # =====================================================
    # WEICHENSTATUS
    # =====================================================

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

    # =====================================================
    # STATUS
    # =====================================================

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

    # =====================================================
    # BEENDEN
    # =====================================================

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


# =========================================================
# KONSOLENSTEUERUNG
# =========================================================

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

        # =================================================
        # LEDTEST
        # =================================================

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

        # =================================================
        # STATUS
        # =================================================

        if command == "status":

            stellwerk.status()

            continue

        # =================================================
        # RELEASE
        # =================================================

        if command == "release":

            stellwerk.release_route()

            continue

        # =================================================
        # QUIT
        # =================================================

        if command == "quit":

            return False

        # =================================================
        # START
        # =================================================

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

        # =================================================
        # ROUTE
        # =================================================

        if (
            len(parts) == 3
            and parts[0] == "route"
        ):

            stellwerk.request_route(
                parts[1],
                parts[2]
            )

            continue

        # =================================================
        # UNBEKANNTER BEFEHL
        # =================================================

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


# =========================================================
# FAHRSTRASSE ANHAND DES NAMENS SUCHEN
# =========================================================

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


# =========================================================
# MAIN
# =========================================================

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


# =========================================================
# PROGRAMMSTART
# =========================================================

if __name__ == "__main__":

    main()