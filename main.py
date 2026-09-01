import argparse
import subprocess
import threading
import time

from config import (
    BUTTON_PINS,
    ROUTE_TIMEOUT,
    ROUTE_MIN_BLINK_TIME,
    LED_COUNT,
    SHUTDOWN_HOLD_TIME,
    SHUTDOWN_FLASH_COUNT,
    Z21_LOG_BROADCASTS,
)

from z21 import Z21
from switches import SwitchController
from routes import find_route
from leds import LEDs
from buttons import Buttons


class Stellwerk:

    def __init__(
        self,
        log_z21_broadcasts=Z21_LOG_BROADCASTS
    ):

        self.z21 = Z21()
        self.log_z21_broadcasts = log_z21_broadcasts

        self.switches = SwitchController(
            self.z21
        )

        self.leds = LEDs()

        self.buttons = None

        # -------------------------------------------------
        # Fahrstraßenstatus
        # -------------------------------------------------

        # Erster gedrückter Fahrstraßen-Taster
        self.selected_start = None

        # Aktuell angeforderte Fahrstraße
        self.requested_route = None

        # Aktive Fahrstraße
        self.active_route = None

        # -------------------------------------------------
        # Gedrückte Taster
        #
        # Beispiel:
        #
        # {
        #     "ABS1",
        #     "HBF4"
        # }
        #
        # Damit können wir erkennen, ob zwei Taster
        # gleichzeitig gedrückt sind.
        # -------------------------------------------------

        self.pressed_buttons = set()

        # -------------------------------------------------
        # Fehleranzeige
        # -------------------------------------------------

        self.route_error_active = False

        # Wird gesetzt, wenn der Abschalttaster während der
        # roten Warnsequenz losgelassen wird.
        self.shutdown_cancelled = threading.Event()
        self.shutdown_warning_active = False

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
            self.on_z21_change,
            self.on_z21_broadcast
            if self.log_z21_broadcasts
            else None,
            self.on_z21_feedback
        )

        # -------------------------------------------------
        # Taster
        # -------------------------------------------------

        self.buttons = Buttons(
            BUTTON_PINS,
            self.on_button,
            SHUTDOWN_HOLD_TIME
        )

        print()
        print(
            "Stellwerk gestartet."
        )
        print()

    # =====================================================
    # Z21 RÜCKMELDUNG
    # =====================================================

    def on_z21_broadcast(self, data):

        """Gibt jedes empfangene Z21-Dataset lesbar aus."""

        header = int.from_bytes(
            data[2:4],
            byteorder="little"
        ) if len(data) >= 4 else None

        if header is None:
            description = "unvollständig"
        elif header == 0x0040 and len(data) >= 5:
            description = (
                f"LAN_X, X-Header=0x{data[4]:02X}"
            )
        else:
            description = f"Header=0x{header:04X}"

        hex_data = data.hex(" ").upper()

        print(
            f"Z21 Broadcast: {description} | {hex_data}"
        )

    def on_z21_feedback(
        self,
        module,
        input_number,
        occupied
    ):

        state = "BELEGT" if occupied else "frei"

        print(
            f"R-Bus: Modul {module}, "
            f"Eingang {input_number} -> {state}"
        )

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
        # Wichtig bei Dreiwegweichen:
        # Erst wenn beide Decoderadressen bekannt sind,
        # bekommen wir z. B. "left", "straight" oder "right".
        # -------------------------------------------------

        if result is None:
            return

        switch_name, logical_position = result

        # -------------------------------------------------
        # Weichen-LED aktualisieren
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
        # Gedrückte Fahrstraßentaster zurücksetzen
        # -------------------------------------------------

        self.pressed_buttons.clear()

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
        name,
        event
    ):

        # =================================================
        # TASTER GEDRÜCKT
        # =================================================

        if event == "pressed":

            self._button_pressed(
                name
            )

            return

        # =================================================
        # TASTER LANGE GEDRÜCKT
        # =================================================

        if event == "held":

            self._button_held(
                name
            )

            return

        # =================================================
        # TASTER LOSGELASSEN
        # =================================================

        if event == "released":

            self._button_released(
                name
            )

            return

    # =====================================================
    # TASTER GEDRÜCKT
    # =====================================================

    def _button_pressed(
        self,
        name
    ):

        print()
        print(
            f"Taster gedrückt: {name}"
        )

        # -------------------------------------------------
        # RASPBERRY PI HERUNTERFAHREN
        # -------------------------------------------------

        if name == "SHUTDOWN":

            if not self.shutdown_warning_active:
                self.shutdown_cancelled.clear()

            print(
                "SHUTDOWN-Taster für 5 Sekunden halten."
            )

            return

        # -------------------------------------------------
        # Taster als gedrückt registrieren
        # -------------------------------------------------

        self.pressed_buttons.add(
            name
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
        # Fahrstraße bereits aktiv
        # -------------------------------------------------

        if self.active_route:

            print(
                f"Fahrstraße "
                f"{self.active_route} "
                f"ist bereits aktiv."
            )

            print(
                "Zum Auflösen bitte "
                "RELEASE drücken."
            )

            # -------------------------------------------------
            # Aktive Fahrstraße kurz rot anzeigen
            # -------------------------------------------------

            self.leds.route_flash_red(
                self.active_route
            )

            return

        # -------------------------------------------------
        # Nur Fahrstraßen-Taster werden für die
        # Start-/Zielauswahl verwendet.
        # -------------------------------------------------

        # -------------------------------------------------
        # Erster gedrückter Taster
        # -------------------------------------------------

        if self.selected_start is None:

            self.selected_start = name

            print()
            print(
                f"Start gewählt: {name}"
            )

            print(
                "Warte auf zweiten "
                "gleichzeitig gedrückten Taster..."
            )

            return

        # -------------------------------------------------
        # Derselbe Taster nochmals gedrückt
        # -------------------------------------------------

        if self.selected_start == name:

            print(
                f"{name} ist bereits "
                f"als Start ausgewählt."
            )

            return

        # -------------------------------------------------
        # Zweiter Taster
        #
        # Da der erste Taster weiterhin in
        # pressed_buttons enthalten sein muss,
        # erfüllen wir hier die gewünschte
        # Gleichzeitigkeit.
        # -------------------------------------------------

        if self.selected_start not in self.pressed_buttons:

            print(
                "Starttaster wurde "
                "zwischenzeitlich losgelassen."
            )

            self.selected_start = name

            print(
                f"Neuer Start: {name}"
            )

            return

        # -------------------------------------------------
        # Fahrstraße aus Start + Ziel bestimmen
        # -------------------------------------------------

        start = self.selected_start

        target = name

        print()
        print(
            "Zwei Taster gleichzeitig gedrückt:"
        )

        print(
            f"  Start:  {start}"
        )

        print(
            f"  Ziel:   {target}"
        )

        # -------------------------------------------------
        # Auswahl löschen
        # -------------------------------------------------

        self.selected_start = None

        # -------------------------------------------------
        # Fahrstraße anfordern
        # -------------------------------------------------

        self.request_route(
            start,
            target
        )

    # =====================================================
    # ABSCHALTTASTER LANGE GEDRÜCKT
    # =====================================================

    def _button_held(
        self,
        name
    ):

        if name != "SHUTDOWN":
            return

        print(
            "SHUTDOWN-Taster 5 Sekunden gehalten."
        )

        self.shutdown_warning_active = True

        try:

            completed = self.leds.all_flash_red(
                SHUTDOWN_FLASH_COUNT,
                self.shutdown_cancelled
            )

            if not completed:

                print(
                    "Herunterfahren abgebrochen."
                )

                self.restore_led_display()

                return

            self.shutdown_raspberry_pi()

        finally:

            self.shutdown_warning_active = False

    # =====================================================
    # LED-ANZEIGE WIEDERHERSTELLEN
    # =====================================================

    def restore_led_display(self):

        print(
            "LED-Anzeige wird wiederhergestellt."
        )

        self.leds.all_off()

        for (
            switch_name,
            position
        ) in self.switches.get_states().items():

            self.leds.switch_position(
                switch_name,
                position
            )

        if self.active_route:

            self.leds.route_on(
                self.active_route
            )

        elif self.requested_route:

            self.leds.route_blink(
                self.requested_route
            )

    # =====================================================
    # RASPBERRY PI HERUNTERFAHREN
    # =====================================================

    def shutdown_raspberry_pi(self):

        print()
        print(
            "Herunterfahren durch SHUTDOWN-Taster..."
        )

        try:

            subprocess.Popen(
                ["systemctl", "poweroff"]
            )

        except OSError as error:

            print(
                f"Herunterfahren fehlgeschlagen: {error}"
            )

    # =====================================================
    # TASTER LOSGELASSEN
    # =====================================================

    def _button_released(
        self,
        name
    ):

        print()
        print(
            f"Taster losgelassen: {name}"
        )

        if name == "SHUTDOWN":

            self.shutdown_cancelled.set()

            if self.shutdown_warning_active:

                print(
                    "Abschaltvorgang wird abgebrochen."
                )

            return

        # -------------------------------------------------
        # Aus gedrückten Tastern entfernen
        # -------------------------------------------------

        self.pressed_buttons.discard(
            name
        )

        # -------------------------------------------------
        # RELEASE
        #
        # Hier müssen wir nichts weiter machen.
        # Die Auflösung erfolgt beim Drücken.
        # -------------------------------------------------

        if name == "RELEASE":

            return

        # -------------------------------------------------
        # Wenn eine Fahrstraße gerade angefordert
        # oder aktiv ist, Auswahl nicht verändern.
        # -------------------------------------------------

        if (
            self.requested_route
            or self.active_route
        ):

            return

        # -------------------------------------------------
        # Starttaster losgelassen
        #
        # Wenn noch kein zweiter Taster gedrückt wurde,
        # wird die Auswahl aufgehoben.
        # -------------------------------------------------

        if self.selected_start == name:

            self.selected_start = None

            print(
                f"Startauswahl {name} "
                f"wurde verworfen."
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
                "Auflösetaster momentan "
                "ohne Funktion."
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
        # Gedrückte Fahrstraßen-Taster löschen
        # -------------------------------------------------

        self.pressed_buttons.clear()

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
            f"Gedrückte Taster: "
            f"{sorted(self.pressed_buttons)}"
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

            # -------------------------------------------------
            # Kein Terminal vorhanden.
            #
            # Das ist z.B. beim Start über systemd der Fall.
            # Das Stellwerk soll dann trotzdem weiterlaufen
            # und auf die GPIO-Taster reagieren.
            # -------------------------------------------------

            print(
                "Kein Konsoleneingang vorhanden."
            )

            print(
                "Stellwerk läuft im Hintergrund."
            )

            while True:

                try:
                    time.sleep(3600)

                except KeyboardInterrupt:
                    raise

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

    parser = argparse.ArgumentParser(
        description="Stellwerksteuerung"
    )
    parser.add_argument(
        "--z21-broadcasts",
        action="store_true",
        default=Z21_LOG_BROADCASTS,
        help=(
            "alle empfangenen Z21-Broadcasts "
            "als Hexdaten ausgeben"
        )
    )
    args = parser.parse_args()

    stellwerk = Stellwerk(
        log_z21_broadcasts=args.z21_broadcasts
    )

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
