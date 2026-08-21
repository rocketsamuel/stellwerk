# stellwerk.py

import time

from config import (
    BLINK_INTERVAL,
    TEST_DURATION,
)

from leds import LedController
from rocrail import Rocrail


class Stellwerk:

    def __init__(self):

        self.leds = LedController()
        self.rocrail = Rocrail()

        self.requested_route = None
        self.active_route = None

    def start(self):

        self.leds.start()

    def request_route(self, route):

        print()
        print(f"Fahrstraße ausgewählt: {route}")

        self.requested_route = route

        # Fahrstraße an Rocrail übergeben
        success = self.rocrail.request_route(route)

        if not success:

            print("Rocrail hat die Anfrage abgelehnt.")

            self.requested_route = None

            return False

        return True

    def wait_for_activation(self):

        print()
        print("Warte auf Rocrail-Bestätigung...")

        while True:

            if self.rocrail.route_active():

                print("Fahrstraße ist aktiv.")

                self.active_route = (
                    self.requested_route
                )

                self.requested_route = None

                return True

            time.sleep(0.1)

    def cancel_route(self):

        self.rocrail.cancel_route()

        self.requested_route = None
        self.active_route = None

    def shutdown(self):

        print()
        print("Stellwerk wird beendet.")

        # Eventuell bestehende Fahrstraße zurücknehmen
        self.cancel_route()

        # LEDs ausschalten
        self.leds.clear()
