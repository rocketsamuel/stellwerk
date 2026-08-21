import time

from config import (
    BUTTON_PINS,
    ROUTE_TIMEOUT,
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

    # --------------------------------------------------
    # START
    # --------------------------------------------------

    def start(self):

        print()
        print("==============================")
        print("        STELLWERK")
        print("==============================")
        print()

        # WS2812B initialisieren
        self.leds.start()

        # Z21 Listener starten
        self.z21.start(
            self.on_z21_change
        )

        # Taster initialisieren
        self.buttons = Buttons(
            BUTTON_PINS,
            self.on_button
        )

        print("Stellwerk gestartet.")
        print()

    # --------------------------------------------------
    # Z21 RÜCKMELDUNG
    # --------------------------------------------------

    def on_z21_change(
        self,
        address,
        position
    ):

        print(
            f"Z21: Adresse {address} -> {position}"
        )

        # Z21-Adresse einer logischen Weiche
        # zuordnen und Zustand speichern.
        switch_name = self.switches.update(
            address,
            position
        )

        # Wenn die Adresse zu einer bekannten
        # Weiche gehört, deren LED-Anzeige
        # aktualisieren.
        if switch_name:

            self.leds.switch_position(
                switch_name,
                position
            )

        # Aktuelle Zustände ausgeben
        for (
            name,
            state
        ) in self.switches.states.items():

            print(
                f"     {name} = {state}"
            )

    # --------------------------------------------------
    # TASTER
    # --------------------------------------------------

    def on_button(
        self,
        name
    ):

        print(
            f"Taster gedrückt: {name}"
        )

        # Wenn bereits eine Fahrstraße aktiv ist,
        # ignorieren wir zunächst weitere Taster.
        if self.active_route:

            print(
                f"Fahrstraße "
                f"{self.active_route} ist aktiv."
            )

            return

        # Erster Taster = Start
        if self.selected_start is None:

            self.selected_start = name

            print(
                f"Start gewählt: {name}"
            )

            return

        # Zweiter Taster = Ziel
        start = self.selected_start
        target = name

        self.selected_start = None

        self.request_route(
            start,
            target
        )

    # --------------------------------------------------
    # FAHRSTRASSE ANFORDERN
    # --------------------------------------------------

    def request_route(
        self,
        start,
        target
    ):

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

        # ------------------------------------------
        # Fahrstraßen-LEDs blinken
        # ------------------------------------------

        print(
            "Starte Fahrstraßen-LED..."
        )

        self.leds.route_blink(
            name
        )

        # ------------------------------------------
        # Weichen stellen
        # ------------------------------------------

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

        # ------------------------------------------
        # Auf Z21-Rückmeldungen warten
        # ------------------------------------------

        print()
        print(
            "Warte auf "
            "Weichen-Rückmeldungen..."
        )

        deadline = (
            time.monotonic()
            + ROUTE_TIMEOUT
        )

        while (
            time.monotonic()
            < deadline
        ):

            if self.route_is_correct(
                route
            ):

                # ----------------------------------
                # Fahrstraße erfolgreich gestellt
                # ----------------------------------

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
                1.5
            )

        # ------------------------------------------
        # Timeout
        # ------------------------------------------

        print()
        print(
            "FEHLER: Die Weichen wurden "
            "nicht innerhalb des Timeouts "
            "korrekt zurückgemeldet."
        )

        print(
            "Aktueller Weichenstatus:"
        )

        self.switches_status()

        self.leds.stop_blink()

        self.requested_route = None

        return False

    # --------------------------------------------------
    # FAHRSTRASSE PRÜFEN
    # --------------------------------------------------

    def route_is_correct(
        self,
        route
    ):

        for (
            switch_name,
            position
        ) in route["switches"].items():

            current = (
                self.switches.states.get(
                    switch_name
                )
            )

            print(
                f"Prüfe {switch_name}: "
                f"erwartet={position}, "
                f"aktuell={current}"
            )

            if current != position:

                return False

        return True

    # --------------------------------------------------
    # FAHRSTRASSE AUFLÖSEN
    # --------------------------------------------------

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

        self.active_route = None

        self.leds.stop_blink()

        # Aktuell werden beim Auflösen
        # alle LEDs ausgeschaltet.
        #
        # Später müssen hier die
        # Weichenstellungs-LEDs wieder
        # hergestellt werden.
        self.leds.all_off()

    # --------------------------------------------------
    # STATUS
    # --------------------------------------------------

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

    # --------------------------------------------------
    # BEENDEN
    # --------------------------------------------------

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

        # ------------------------------------------
        # LED TEST
        # ------------------------------------------

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

        # ------------------------------------------
        # STATUS
        # ------------------------------------------

        if command == "status":

            stellwerk.status()

            continue

        # ------------------------------------------
        # RELEASE
        # ------------------------------------------

        if command == "release":

            stellwerk.release_route()

            continue

        # ------------------------------------------
        # QUIT
        # ------------------------------------------

        if command == "quit":

            return False

        # ------------------------------------------
        # START
        # ------------------------------------------

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

        # ------------------------------------------
        # ROUTE
        # ------------------------------------------

        if (
            len(parts) == 3
            and parts[0] == "route"
        ):

            stellwerk.request_route(
                parts[1],
                parts[2]
            )

            continue

        # ------------------------------------------
        # UNBEKANNTER BEFEHL
        # ------------------------------------------

        print(
            "Unbekannter Befehl."
        )

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

    finally:

        stellwerk.stop()


if __name__ == "__main__":

    main()
