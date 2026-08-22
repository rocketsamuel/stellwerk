from config import SWITCHES


class SwitchController:

    def __init__(self, z21):

        self.z21 = z21

        # Logischer Zustand der Weichen
        #
        # Beispiel:
        # {
        #     "sw46": "straight",
        #     "sw42": "left",
        # }
        self.states = {}

        # Z21-Adresse -> logischer Weichenname
        self.address_map = {}

        # Zwischenzustände der Mehrfachweichen
        self.combination_states = {}

        self._build_address_map()

    # =====================================================
    # ADRESSZUORDNUNG
    # =====================================================

    def _build_address_map(self):

        self.address_map.clear()

        for name, config in SWITCHES.items():

            switch_type = config.get("type")

            if switch_type == "turnout":

                address = config["address"]

                self.address_map[address] = name

            elif switch_type in (
                "three_way",
                "double_slip",
            ):

                for address in config["addresses"]:

                    self.address_map[address] = name

    # =====================================================
    # Z21-RÜCKMELDUNG
    # =====================================================

    def update(
        self,
        address,
        position
    ):

        if address not in self.address_map:

            print(
                f"Z21: unbekannte "
                f"Weichenadresse {address}"
            )

            return None

        switch_name = self.address_map[address]

        config = SWITCHES[switch_name]

        switch_type = config.get("type")

        # -------------------------------------------------
        # NORMALE WEICHE
        # -------------------------------------------------

        if switch_type == "turnout":

            self.states[switch_name] = position

            print(
                f"Z21: Adresse {address} "
                f"-> {position}"
            )

            return (
                switch_name,
                position
            )

        # -------------------------------------------------
        # DREIWEGWEICHE
        # -------------------------------------------------

        if switch_type == "three_way":

            print(
                f"Z21: Adresse {address} "
                f"-> {position}"
            )

            logical_position = (
                self._update_combination_switch(
                    switch_name,
                    address,
                    position
                )
            )

            # -------------------------------------------------
            # Noch keine vollständige Kombination
            # -------------------------------------------------

            if logical_position is None:

                return None

            return (
                switch_name,
                logical_position
            )

        # -------------------------------------------------
        # DKW
        # -------------------------------------------------

        if switch_type == "double_slip":

            print(
                f"Z21: Adresse {address} "
                f"-> {position}"
            )

            logical_position = (
                self._update_combination_switch(
                    switch_name,
                    address,
                    position
                )
            )

            if logical_position is None:

                return None

            return (
                switch_name,
                logical_position
            )

        return None

    # =====================================================
    # MEHRFACHWEICHE AKTUALISIEREN
    # =====================================================

    def _update_combination_switch(
        self,
        switch_name,
        address,
        position
    ):

        config = SWITCHES[switch_name]

        addresses = config["addresses"]

        # -------------------------------------------------
        # Zustand der beiden Z21-Adressen speichern
        # -------------------------------------------------

        if switch_name not in self.combination_states:

            self.combination_states[switch_name] = {}

        state = self.combination_states[
            switch_name
        ]

        state[address] = position

        # -------------------------------------------------
        # Falls Z21 bereits einen Zustand kennt,
        # übernehmen wir diesen ebenfalls.
        #
        # Das ist besonders beim Programmstart hilfreich.
        # -------------------------------------------------

        for addr in addresses:

            if addr not in state:

                z21_state = self.z21.get_state(
                    addr
                )

                if z21_state is not None:

                    state[addr] = z21_state

        # -------------------------------------------------
        # Sind beide Adressen bekannt?
        # -------------------------------------------------

        for addr in addresses:

            if addr not in state:

                print(
                    f"Z21: {switch_name}: "
                    f"warte auf Rückmeldung "
                    f"für Adresse {addr}"
                )

                return None

        # -------------------------------------------------
        # Kombination auswerten
        # -------------------------------------------------

        positions = config.get(
            "positions",
            {}
        )

        detected_position = None

        for (
            logical_position,
            requirements
        ) in positions.items():

            matches = True

            for (
                required_address,
                required_position
            ) in requirements.items():

                if (
                    state.get(required_address)
                    != required_position
                ):

                    matches = False

                    break

            if matches:

                detected_position = (
                    logical_position
                )

                break

        # -------------------------------------------------
        # Gültige Stellung erkannt
        # -------------------------------------------------

        if detected_position is not None:

            old_position = self.states.get(
                switch_name
            )

            self.states[switch_name] = (
                detected_position
            )

            if old_position != detected_position:

                print(
                    f"Z21: {switch_name} "
                    f"-> {detected_position}"
                )

            return detected_position

        # -------------------------------------------------
        # Ungültige Kombination
        # -------------------------------------------------

        print(
            f"Z21: {switch_name}: "
            f"unbekannte Kombination"
        )

        for addr in addresses:

            print(
                f"     Adresse {addr}: "
                f"{state.get(addr)}"
            )

        return None

    # =====================================================
    # WEICHE STELLEN
    # =====================================================

    def command(
        self,
        switch_name,
        position
    ):

        if switch_name not in SWITCHES:

            raise ValueError(
                f"Unbekannte Weiche: "
                f"{switch_name}"
            )

        config = SWITCHES[switch_name]

        switch_type = config.get("type")

        # -------------------------------------------------
        # NORMALE WEICHE
        # -------------------------------------------------

        if switch_type == "turnout":

            if position not in (
                "straight",
                "turnout",
            ):

                raise ValueError(
                    f"Ungültige Stellung "
                    f"für {switch_name}: "
                    f"{position}"
                )

            address = config["address"]

            print(
                f"Weiche {switch_name}: "
                f"Adresse {address} "
                f"-> {position}"
            )

            self.z21.set_turnout(
                address,
                position
            )

            return

        # -------------------------------------------------
        # DREIWEGWEICHE
        # -------------------------------------------------

        if switch_type == "three_way":

            self.command_three_way(
                switch_name,
                position
            )

            return

        # -------------------------------------------------
        # DKW
        # -------------------------------------------------

        if switch_type == "double_slip":

            self.command_double_slip(
                switch_name,
                position
            )

            return

        raise ValueError(
            f"Unbekannter Weichentyp "
            f"{switch_type} bei "
            f"{switch_name}"
        )

    # =====================================================
    # DREIWEGWEICHE STELLEN
    # =====================================================

    def command_three_way(
        self,
        switch_name,
        position
    ):

        config = SWITCHES[switch_name]

        positions = config.get(
            "positions",
            {}
        )

        if position not in positions:

            raise ValueError(
                f"Ungültige Stellung "
                f"{position} für "
                f"Dreiwegweiche "
                f"{switch_name}"
            )

        requirements = positions[position]

        print()
        print(
            f"Dreiwegweiche "
            f"{switch_name} -> "
            f"{position}"
        )

        # -------------------------------------------------
        # Beide Decoderadressen stellen
        # -------------------------------------------------

        for (
            address,
            target_position
        ) in requirements.items():

            print(
                f"  Adresse {address} "
                f"-> {target_position}"
            )

            self.z21.set_turnout(
                address,
                target_position
            )

        print()

        # -------------------------------------------------
        # Wichtig:
        #
        # self.states wird hier NICHT direkt gesetzt.
        #
        # Erst die Z21-Rückmeldung bestätigt die
        # tatsächliche Stellung.
        # -------------------------------------------------

    # =====================================================
    # DKW STELLEN
    # =====================================================

    def command_double_slip(
        self,
        switch_name,
        position
    ):

        config = SWITCHES[switch_name]

        positions = config.get(
            "positions",
            {}
        )

        if position not in positions:

            raise ValueError(
                f"Ungültige Stellung "
                f"{position} für "
                f"DKW {switch_name}"
            )

        requirements = positions[position]

        print(
            f"DKW {switch_name} -> "
            f"{position}"
        )

        for (
            address,
            target_position
        ) in requirements.items():

            print(
                f"  Adresse {address} "
                f"-> {target_position}"
            )

            self.z21.set_turnout(
                address,
                target_position
            )

    # =====================================================
    # STELLUNG ABFRAGEN
    # =====================================================

    def get_position(
        self,
        switch_name
    ):

        return self.states.get(
            switch_name
        )

    # =====================================================
    # STELLUNG PRÜFEN
    # =====================================================

    def is_position(
        self,
        switch_name,
        position
    ):

        return (
            self.states.get(
                switch_name
            )
            == position
        )

    # =====================================================
    # ALLE STELLUNGEN
    # =====================================================

    def get_states(self):

        return dict(
            self.states
        )