# Stellwerk: Konfiguration

Die Datei `config.py` beschreibt die Anlage: Verbindung zur Z21, GPIO-Taster, Rückmelder, Weichen, Signale, Fahrstraßen und LEDs des Stellpults. Diese Anleitung erklärt die Einstellungen anhand der derzeitigen Konfiguration.

## Änderungen übernehmen

`config.py` ist eine Python-Datei. Texte stehen in Anführungszeichen, Wahrheitswerte heißen `True` und `False`, Dezimalzahlen verwenden einen Punkt. Einträge in Listen und Wörterbüchern werden durch Kommas getrennt. Kommentare beginnen mit `#`.

Nach dem Speichern muss das Stellwerk-Programm neu gestartet werden. Falls es über die mitgelieferte systemd-Service-Datei installiert ist:

```bash
sudo systemctl restart stellwerk.service
```

Die Syntax lässt sich auf dem Raspberry Pi vorab prüfen:

```bash
python3 -m py_compile config.py
```

Dieser Befehl prüft nur die Python-Syntax, nicht die Verdrahtung oder die inhaltliche Zuordnung.

## Nummerierung und Namen

| Angabe | Bedeutung |
| --- | --- |
| GPIO-Pins | BCM-Nummern, keine physischen Steckleisten-Pinnummern. |
| LED-Nummern | Beginnen bei **1** und reichen bis einschließlich `LED_COUNT`. |
| Normale Zubehöradressen | Beginnen bei **1**. Die Umrechnung für das Z21-Protokoll übernimmt `z21.py`. |
| R-Bus-Kontaktadressen | Fortlaufend ab **1**, mit acht Eingängen je Modul. |
| DCC-Extended-`raw_address` | Unveränderte Protokolladresse; siehe Abschnitt Signale. |
| Namen wie `sw42`, `ls5`, `ABS1_HBF4` | Interne Schlüssel, die in allen zugehörigen Tabellen exakt übereinstimmen müssen. Groß-/Kleinschreibung beachten. |

## Z21-Verbindung und Zeitverhalten

Alle Zeitangaben sind in Sekunden.

| Einstellung | Aktueller Wert | Wirkung |
| --- | --- | --- |
| `Z21_IP` | `"192.168.178.223"` | IP-Adresse der Z21 im lokalen Netzwerk. |
| `Z21_PORT` | `21105` | UDP-Zielport der Z21. |
| `TURNOUT_PULSE_TIME` | `0.2` | Zeit zwischen Ein- und Ausschaltbefehl eines Zubehör-Schaltimpulses; gilt auch für Signale mit normalen Zubehörbefehlen. |
| `BROADCAST_KEEPALIVE` | `5.0` | Intervall zum Erneuern des Broadcast-Abonnements. |
| `Z21_BROADCAST_FLAGS` | `0x00000003` | Abonniert Fahr-/Schaltmeldungen (`0x01`) und R-Bus-Meldungen (`0x02`). Nicht benötigte Fahrmeldungen werden bei der Ausgabe gefiltert. |
| `Z21_LOG_BROADCASTS` | `False` | Aktiviert mit `True` zusätzliche Hex-Ausgaben empfangener Datasets zur Fehlersuche; die Ausgabe filtert Fahrmeldungen weiterhin. |
| `ROUTE_TIMEOUT` | `10.0` | Wartezeit auf passende Weichenrückmeldungen nach dem Senden der Stellbefehle. Bei Ablauf schlägt die Fahrstraßenanforderung fehl. |
| `BLINK_INTERVAL` | `0.5` | Dauer einer Ein- bzw. Ausphase beim Blinken. Ein vollständiger Blinkzyklus dauert damit etwa eine Sekunde. |
| `ROUTE_MIN_BLINK_TIME` | `1` | Mindestdauer der blinkenden Fahrstraßenanzeige, auch wenn die Weichen bereits richtig stehen. |

## LEDs und Startsequenz

| Einstellung | Aktueller Wert | Wirkung |
| --- | --- | --- |
| `LED_COUNT` | `34` | Anzahl der WS2812B-LEDs. |
| `LED_PIN` | `18` | BCM-GPIO für die LED-Datenleitung. Die weiteren Treiberparameter, einschließlich Kanal 0, stehen fest in `leds.py`; ein anderer Pin muss dazu passen. |
| `LED_BRIGHTNESS` | `32` | Helligkeit im Betrieb: `0` = aus, `255` = Maximum. |
| `STARTUP_LED_BRIGHTNESS` | `13` | Helligkeit während der Startsequenz, ebenfalls von 0 bis 255. |
| `STARTUP_LED_ORDER` | `list(range(1, LED_COUNT + 1))` | Reihenfolge des blauen Lauflichts; standardmäßig alle LEDs aufsteigend. Bereits eingeschaltete LEDs bleiben zunächst an. |
| `STARTUP_LED_DELAY` | `0.1` | Pause nach jeder LED des Lauflichts. |
| `STARTUP_LED_FLASH_COUNT` | `2` | Anzahl gemeinsamer blauer Blinkimpulse nach dem Lauflicht. Diese betreffen alle LEDs, unabhängig von `STARTUP_LED_ORDER`. |
| `STARTUP_LED_FLASH_TIME` | `0.2` | Einschaltdauer pro blauem Blinkimpuls. |
| `STARTUP_LED_FLASH_OFF_TIME` | `0.2` | Dunkelpause vor jedem blauen Blinkimpuls. |

Eine eigene Lauflicht-Reihenfolge kann beispielsweise so aussehen:

```python
STARTUP_LED_ORDER = [1, 2, 5, 6, 7, 8]
```

Nach der Startsequenz werden die LEDs ausgeschaltet und die Betriebshelligkeit wiederhergestellt. Farben und spezielle Anzeigelogik sind im Programm festgelegt, nicht in `config.py`.

## Taster und Herunterfahren

`BUTTON_PINS` ordnet jedem Tasternamen einen BCM-GPIO zu:

```python
BUTTON_PINS = {
    "HBF4": 22,
    "ABS1": 27,
    "RELEASE": 17,
    "SHUTDOWN": 25,
}
```

Dies ist ein gekürztes Beispiel. Die vollständige Config enthält weitere Start-/Zieltaster. Ein Wert von `None` deaktiviert den jeweiligen Taster. Die Eingänge verwenden interne Pull-ups; der Taster verbindet den Eingang beim Drücken mit GND. Die Entprellzeit beträgt fest 0,05 Sekunden.

Zum Anfordern einer Fahrstraße zuerst den Starttaster gedrückt halten und dann den Zieltaster drücken. Die Namen müssen zu `start` und `target` in `ROUTES` passen. `RELEASE` löst die aktive Fahrstraße auf.

| Einstellung | Aktueller Wert | Wirkung |
| --- | --- | --- |
| `SHUTDOWN_HOLD_TIME` | `5.0` | Haltezeit des `SHUTDOWN`-Tasters bis zum Beginn der roten Warnsequenz. |
| `SHUTDOWN_FLASH_COUNT` | `3` | Anzahl roter Blinkimpulse vor dem Herunterfahren des Raspberry Pi. Die Blinkdauer richtet sich nach `BLINK_INTERVAL`. |

Den Abschalttaster auch während der Warnsequenz gedrückt halten. Loslassen während dieser Sequenz bricht den Abschaltvorgang ab. Die Konsolentexte nennen derzeit fest „5 Sekunden“, auch wenn `SHUTDOWN_HOLD_TIME` geändert wird.

## Rückmelder und Belegtanzeige

`FEEDBACKS` verbindet einen R-Bus-Kontakt mit den zugehörigen Gleis-LEDs:

```python
FEEDBACKS = {
    "ABS1": {
        "address": 12,
        "leds": [1, 2],
    },
}

SHOW_OCCUPANCY = False
```

Die Kontaktadresse berechnet sich als `(Modul - 1) * 8 + Eingang`. Adresse 12 entspricht also Modul 2, Eingang 4. Der Name `ABS1` dient hier der Zuordnung und Ausgabe; er erzeugt keine automatische Verbindung zu einer Fahrstraße.

Mit `SHOW_OCCUPANCY = True` leuchten die zugeordneten LEDs bei Belegung rot. Die rote Anzeige überlagert die sonstige LED-Farbe; beim Freiwerden erscheint diese wieder. Bei `False` werden R-Bus-Meldungen weiterhin empfangen und protokolliert, aber nicht auf den LEDs dargestellt. Rückmelder sperren im aktuellen Programm keine Fahrstraßen und lösen sie auch nicht automatisch auf.

## Weichen

`SWITCHES` beschreibt die Decoderadressen und logischen Stellungen.

### Normale Weiche (`turnout`)

```python
"eow1": {
    "type": "turnout",
    "address": 127,
    "inverted": True,
},
```

`address` ist die Zubehöradresse. Als logische Stellungen sind `straight` (gerade) und `turnout` (abzweigend) erlaubt. Das optionale `inverted` vertauscht die beiden Stellungen sowohl beim Senden als auch beim Auswerten der Rückmeldung. Ohne diese Angabe gilt `False`. Fahrstraßen und LED-Zuordnungen verwenden weiterhin die logischen Stellungen.

### Dreiwegweiche (`three_way`)

```python
"sw42": {
    "type": "three_way",
    "addresses": [25, 26],
    "positions": {
        "straight": {25: "straight", 26: "straight"},
        "right": {25: "turnout", 26: "straight"},
        "left": {25: "straight", 26: "turnout"},
    },
},
```

`addresses` enthält die beiden Zubehöradressen. `positions` beschreibt für jede logische Stellung die benötigte Kombination der Decoder-Ausgänge. Die Adressen innerhalb dieser Kombinationen sind Zahlen, keine Zeichenketten. Eine Stellung wird erst erkannt, wenn die Zustände beider Adressen bekannt sind und zur Kombination passen.

Der Code unterstützt auch `type: "double_slip"` für Doppelkreuzungsweichen mit demselben Aufbau aus `addresses` und `positions`. Für Mehrfachweichen wird eine vertauschte Ansteuerung direkt in den Kombinationen abgebildet; `inverted` wird nur bei normalen Weichen ausgewertet.

## Signale

`SIGNALS` enthält drei derzeit verwendete Signaltypen. Fahrstraßen verweisen auf den internen Schlüssel, beispielsweise `signal_abs`. Das optionale `display_name` ändert nur die entsprechende Anzeige in der Ausgabe.

### LED-Signal (`led`)

```python
"ls5": {
    "type": "led",
    "default_aspect": "Hp0",
    "aspect_leds": {"Sh1": 32, "Hp0": 33},
    "aspects": {"Hp0": [], "Sh1": []},
},
```

`aspect_leds` ordnet den Begriffen die Stellpult-LEDs zu. `aspects` muss die erlaubten Begriffe ebenfalls enthalten; leere Listen bedeuten, dass keine Zubehörbefehle an die Z21 gesendet werden. Das Signal wird beim Start auf `default_aspect` gesetzt. Die LED-Ansteuerung ist derzeit für `Hp0` und `Sh1` ausgelegt.

### Signal über normale Zubehöradressen (`four_aspect`)

Beim Signal `signal_abs` (Anzeigename `p4`) stehen in `addresses` die Decoderadressen 49 und 50. `aspects` ordnet jedem Signalbegriff eine Liste von Schaltbefehlen zu, beispielsweise:

```python
"Hp0_Sh1": [
    {"address": 49, "position": "turnout"},
    {"address": 50, "position": "turnout"},
],
```

Jeder Befehl verwendet `address` und `position` (`straight` oder `turnout`). Die Liste wird der Reihe nach gesendet. Dieselben Kombinationen dienen der Erkennung eingehender Signalzustände; längere Kombinationen werden zuerst geprüft. Eine ausgelassene Adresse wird weder geschaltet noch für diesen Begriff geprüft. Das betrifft aktuell beispielsweise `Hp1`, das nur Adresse 49 enthält.

`default_aspect` setzt hier zunächst den internen Anfangszustand; es sendet beim Start keinen Haltbefehl an den Decoder. `indicator_led` bezeichnet die LED für die Signalanzeige.

**Besonderheit von p4:** Die Anzeige ist in `main.py` ausdrücklich an `signal_abs` und die Weiche `sw42` gebunden. Teilweise wird dort LED 34 direkt verwendet. `Hp0` erscheint rot, `Hp2` blinkt gelb, und `Hp0_Sh1` blinkt nur bei `sw42 = "right"` weiß; sonst erscheint es rot. `Hp1` schaltet diese Anzeige aus. Beim Umbenennen dieser Elemente oder Ändern der Anzeige-LED muss daher auch `main.py` angepasst werden.

### DCC-Extended-Signal (`dcc_ext`)

```python
"n4": {
    "type": "dcc_ext",
    "address": 116,
    "raw_address": 119,
    "dcc_ext_aspects": {
        0: "Hp0",
        4: "Hp2",
        16: "Hp1",
        65: "Hp0_Sh1",
    },
    "indicator_led": 21,
},
```

`raw_address` wird unverändert für Statusabfragen und die Zuordnung empfangener Meldungen verwendet. Das Feld `address` wird bei diesem Signaltyp derzeit nicht ausgewertet. Aus den Beispielwerten 116 und 119 sollte daher keine allgemeine Umrechnungsregel abgeleitet werden.

`dcc_ext_aspects` übersetzt empfangene Zahlenwerte in Signalbegriffe; die Zuordnung muss zum Decoder passen. `indicator_led` legt die Anzeige-LED fest. Dieser Signaltyp wird aktuell nur abgefragt und angezeigt. Das Senden von DCC-Extended-Signalbefehlen ist nicht implementiert; `n4` kann mit dieser Konfiguration deshalb nicht über `ROUTES[...]["signals"]` gestellt werden.

## Fahrstraßen

`ROUTES` legt für jede Fahrtrichtung eine eigene Fahrstraße fest:

```python
"HBF4_ABS1": {
    "start": "HBF4",
    "target": "ABS1",
    "switches": {
        "sw46": "turnout",
        "sw42": "straight",
    },
    "signals": {"signal_abs": "Hp0_Sh1"},
},
```

| Feld | Bedeutung |
| --- | --- |
| Schlüssel `HBF4_ABS1` | Eindeutiger Fahrstraßenname, der auch in `ROUTE_LEDS` verwendet wird. |
| `start`, `target` | Namen der Start- und Zieltaster. Die Kombination bestimmt die Fahrstraße. |
| `switches` | Benötigte Weichen und deren logische Stellungen aus `SWITCHES`. |
| `signals` | Optional: Signalbegriffe, die nach Bestätigung aller Weichenstellungen gesendet werden. |

Die Gegenrichtung wird nicht automatisch angelegt. `ABS1_HBF4` benötigt einen eigenen Eintrag und kann andere Signalbefehle haben. Jede Kombination aus Start und Ziel sollte nur einmal vorkommen, da bei mehreren Treffern der erste verwendet wird.

Während des Stellens blinken die Fahrstraßen-LEDs gelb, nach erfolgreicher Bestätigung leuchten sie dauerhaft gelb. Es kann nur eine Fahrstraße aktiv sein. Beim Auflösen werden die in der Fahrstraße enthaltenen Signale auf `Hp0` gestellt; dieser Begriff muss daher für sie definiert sein. Die Weichen werden dabei nicht zurückgestellt.

## LED-Zuordnungen für Weichen und Fahrstraßen

`SWITCH_LEDS` verbindet logische Weichenstellungen mit einzelnen LEDs:

```python
SWITCH_LEDS = {
    "sw46": {"straight": 4, "turnout": 3},
    "sw42": {"left": 12, "straight": 11, "right": 10},
}
```

Weichenname und Stellungsnamen müssen zu `SWITCHES` passen. Die LED der aktuellen Stellung leuchtet gelb; die übrigen LEDs dieser Weiche werden ausgeschaltet.

`ROUTE_LEDS` ordnet einer Fahrstraße die Gleis-LEDs zu:

```python
ROUTE_LEDS = {
    "HBF4_ABS1": [1, 2, 9, 13],
    "ABS1_HBF4": [1, 2, 9, 13],
}
```

Beide Richtungen dürfen dieselben LEDs verwenden, brauchen aber jeweils einen eigenen Eintrag. Ohne Zuordnung kann eine Fahrstraße gestellt werden, hat jedoch keine Fahrstraßen-LED-Anzeige. Weichen-LEDs werden separat über `SWITCH_LEDS` gesteuert und müssen nicht zusätzlich in `ROUTE_LEDS` stehen.

## Typische Änderungen

Zum Ergänzen einer Fahrstraße:

1. Start- und Zieltaster in `BUTTON_PINS` prüfen bzw. ergänzen.
2. Benötigte Weichen in `SWITCHES` und deren LEDs in `SWITCH_LEDS` eintragen.
3. Einen Eintrag in `ROUTES` mit Start, Ziel und Weichenstellungen ergänzen.
4. Falls benötigt, schaltbare Signale in `SIGNALS` definieren und unter `signals` zuordnen.
5. Unter demselben Fahrstraßennamen die Gleis-LEDs in `ROUTE_LEDS` eintragen.
6. Bei Bedarf eine eigene Gegenrichtung anlegen.
7. Syntax prüfen, Programm neu starten und die Zuordnungen an der Anlage kontrollieren.

Bei einer Änderung von `LED_COUNT` alle LED-Nummern prüfen: `STARTUP_LED_ORDER`, `FEEDBACKS`, `SWITCH_LEDS`, `ROUTE_LEDS` und die LED-Felder in `SIGNALS`. Änderungen an GPIOs dürfen keine Doppelbelegung mit anderen Tastern oder der LED-Datenleitung erzeugen.
