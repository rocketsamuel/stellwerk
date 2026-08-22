from config import SWITCHES


class SwitchController:

    def __init__(self, z21):

        self.z21 = z21

        # Aktuell bekannte logische Stellung
        #
        # Beispiel:
        #
        # {
        #     "sw46": "straight",
        #     "sw42": "left",
        # }
        #
        self.states = {}

        # Zuordnung:
        #
        # Z21-Adresse -> logischer Weichenname
        #
        # Wird vor allem für die Rückmeldungen
        # der Z21 benötigt.
        self.address_map = {}

        self._build_address_map()

    # =====================================================
    # ADRESSZUORDNUNG AUFBAUEN
    # =====================================================

    def _build_address_map(self):

        self.address_map.clear()

        for name, config in SWITCHES.items():

            switch_type = config.get("type")

            # -------------------------------------------------
            # NORMALE WEICHE
            # -------------------------------------------------

            if switch_type == "turnout":

                address = config["address"]

                self.address_map[address] = name

            # -------------------------------------------------
            # DREIWEGWEICHE
            # -------------------------------------------------

            elif switch_type == "three_way":

                addresses = config["addresses"]

                for address in addresses:

                    self.address_map[address] = name

            # -------------------------------------------------
            # DKW
            # -------------------------------------------------

            elif switch_type == "double_slip":

                addresses = config["addresses"]

                for address in addresses:

                    self.address_map[address] = name

    # =====================================================
    # RÜCKMELDUNG VON DER Z21 VERARBEITEN
    # =====================================================

    def update(
        self,
        address,
        position
    ):
        """
        Verarbeitet eine Z21-Rückmeldung.

        Rückgabe:
            Name der betroffenen logischen Weiche
            oder None, wenn die Adresse unbekannt ist.
        """

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

            return switch_name

        # -------------------------------------------------
        # DREIWEGWEICHE
        # -------------------------------------------------

        if switch_type == "three_way":

            print(
                f"Z21: Adresse {address} "
                f"-> {position}"
            )

            self._update_three_way(
                switch_name,
                address,
                position
            )

            return switch_name

        # -------------------------------------------------
        # DKW
        # -------------------------------------------------

        if switch_type == "double_slip":

            print(
                f"Z21: Adresse {address} "
                f"-> {position}"
            )

            self._update_double_slip(
                switch_name,
                address,
                position
            )

            return switch_name

        return switch_name

    # =====================================================
    # DREIWEGWEICHE AKTUALISIEREN
    # =====================================================

    def _update_three_way(
        self,
        switch_name,
        address,
        position
    ):

        config = SWITCHES[switch_name]

        addresses = config["addresses"]

        # -------------------------------------------------
        # Aktuelle Zustände der beiden Decoderadressen
        # -------------------------------------------------

        current = getattr(
            self,
            "_three_way_states",
            {}
        )

        if switch_name not in current:

            current[switch_name] = {}

        current[switch_name][address] = position

        self._three_way_states = current

        state = current[switch_name]

        address_25 = addresses[0]
        address_26 = addresses[1]

        pos25 = state.get(address_25)
        pos26 = state.get(address_26)

        # -------------------------------------------------
        # Noch nicht beide Rückmeldungen bekannt
        # -------------------------------------------------

        if pos25 is None or pos26 is None:

            print(
                f"Z21: {switch_name}: "
                f"warte auf beide Adressen "
                f"({address_25}, {address_26})"
            )

            return

        # -------------------------------------------------
        # Erwartete Kombinationen aus config.py
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

            if (
                state.get(address_25)
                == requirements.get(address_25)
                and
                state.get(address_26)
                == requirements.get(address_26)
            ):

                detected_position = logical_position

                break

        # -------------------------------------------------
        # Stellung erkannt
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

            return

        # -------------------------------------------------
        # Kombination unbekannt
        # -------------------------------------------------

        print(
            f"Z21: {switch_name}: "
            f"unbekannte Kombination:"
        )

        print(
            f"     Adresse {address_25}: "
            f"{pos25}"
        )

        print(
            f"     Adresse {address_26}: "
            f"{pos26}"
        )

    # =====================================================
    # DKW
    # =====================================================

    def _update_double_slip(
        self,
        switch_name,
        address,
        position
    ):

        config = SWITCHES[switch_name]

        addresses = config["addresses"]

        current = getattr(
            self,
            "_double_slip_states",
            {}
        )

        if switch_name not in current:

            current[switch_name] = {}

        current[switch_name][address] = position

        self._double_slip_states = current

        state = current[switch_name]

        # -------------------------------------------------
        # Noch nicht beide Adressen bekannt
        # -------------------------------------------------

        if (
            addresses[0] not in state
            or
            addresses[1] not in state
        ):

            return

        positions = config.get(
            "positions",
            {}
        )

        detected_position = None

        for (
            logical_position,
            requirements
        ) in positions.items():

            match = True

            for addr, required in requirements.items():

                if state.get(addr) != required:

                    match = False
                    break

            if match:

                detected_position = (
                    logical_position
                )

                break

        if detected_position is not None:

            self.states[switch_name] = (
                detected_position
            )

            print(
                f"Z21: {switch_name} "
                f"-> {detected_position}"
            )

        else:

            print(
                f"Z21: {switch_name}: "
                f"unbekannte DKW-Kombination"
            )

    # =====================================================
    # WEICHE STELLEN
    # =====================================================

    def command(
        self,
        switch_name,
        position
    ):
        """
        Stellt eine logische Weiche.

        Beispiele:

            command("sw46", "straight")

            command("sw46", "turnout")

            command("sw42", "left")

            command("sw42", "straight")

            command("sw42", "right")
        """

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
                "turnout"
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

        # -------------------------------------------------
        # Wir setzen die logische Stellung NICHT sofort.
        #
        # Sie wird erst durch die Z21-Rückmeldung
        # bestätigt.
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
    # PRÜFEN, OB EINE STELLUNG ERREICHT IST
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
    # ALLE WEICHENSTELLUNGEN
    # =====================================================

    def get_states(self):

        return dict(
            self.states
        )