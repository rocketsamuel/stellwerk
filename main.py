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

    # ==================================================
    # START
    # ==================================================

    def start(self):

        print()
        print("==============================")
        print("        STELLWERK")
        print("==============================")
        print()

        # LEDs starten
        self.leds.start()

        # Z21 Listener starten
        self.z21.start(
            self.on_z21_change
        )

        # Taster starten
        self.buttons = Buttons(
            BUTTON_PINS,
            self.on_button
        )

        print("Stellwerk gestartet.")
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

        # Z21-Adresse einer logischen Weiche
        # zuordnen.
        switch_name = self.switches.update(
            address,
            position
        )

        # Weichen-LED aktualisieren
        if switch_name:

            self.leds.switch_position(
                switch_name,
                position
            )

        # Status ausgeben
        for (
            name,
            state
        ) in self.switches.states.items():

            print(
                f"     {name} = {state}"
            )

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
        # Wenn Fahrstraße bereits aktiv
        # ----------------------------------------------

        if self.active_route:

            print(
                f"Fahrstraße "
                f"{self.active_route} ist aktiv."
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

        # ----------------------------------------------
        # Prüfen, ob bereits eine Fahrstraße
        # bearbeitet wird
        # ----------------------------------------------

        if (
            self.active_route
            or self.requested_route
        ):

            print(
                "Es ist bereits eine "
                "Fahrstraße in Bearbeitung."
            )

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
        # BLINKEN STARTEN
        # ----------------------------------------------

        print(
            "Fahrstraßen-LEDs blinken..."
        )

        self.leds.route_blink(
            name
        )

        # Zeitpunkt merken, an dem das Blinken
        # begonnen hat.
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

            self.requested_route = None

            return False

        # ----------------------------------------------
        # AUF Z21-RÜCKMELDUNG WARTEN
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
                # Mindest-Blinkzeit einhalten
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
                # FAHRSTRASSE AKTIV
                # --------------------------------------

                self.requested_route = None
                self.active_route = name

                # Blinken stoppen und LEDs
                # dauerhaft einschalten.
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

            # Alle 50 ms erneut prüfen.
            #
            # Hier wird nicht aktiv die Z21 gefragt.
            # Es wird nur der zuletzt empfangene
            # Broadcast-Zustand geprüft.

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

        # Blinken stoppen
        self.leds.stop_blink()

        # Fahrstraßen-LEDs ausschalten
        self.leds.route_off(
            name
        )

        # Zustand zurücksetzen
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

            # Noch keine Rückmeldung
            if current_position is None:

                return False

            # Falsche Stellung
            if (
                current_position
                != expected_position
            ):

                return False

        # Alle Weichen stimmen
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

        print()
        print(
            f"Fahrstraße aufgelöst: "
            f"{self.active_route}"
        )

        route_name = self.active_route

        self.active_route = None

        self.leds.stop_blink()

        # Fahrstraßen-LEDs ausschalten
        self.leds.route_off(
            route_name
        )

        # ----------------------------------------------
        # Die Weichen-LEDs bleiben dabei erhalten.
        # ----------------------------------------------

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