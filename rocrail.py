# rocrail.py

class Rocrail:

    def __init__(self):

        self.requested_route = None
        self.active_route = None

    def request_route(self, route):

        print()
        print("================================")
        print("ROCrail: Fahrstraße anfordern")
        print("================================")
        print(f"Fahrstraße: {route}")
        print()

        self.requested_route = route

        # -------------------------------------------------
        # TESTBETRIEB
        #
        # Später wird hier der echte HTTP-Aufruf
        # an Rocrail stehen.
        # -------------------------------------------------

        return True

    def route_active(self):

        # -------------------------------------------------
        # TESTBETRIEB
        #
        # Später kommt hier die Rocrail-Rückmeldung hin.
        # -------------------------------------------------

        return True

    def cancel_route(self):

        print()
        print("================================")
        print("ROCrail: Fahrstraße auflösen")
        print("================================")
        print()

        self.requested_route = None
        self.active_route = None
