#!/bin/bash

SERVER="192.168.178.138"
PORT="8051"
WEICHEN_ID="sw46"

XML_REQ="<sw id=\"$WEICHEN_ID\" cmd=\"query\"/>"

echo "Frage Rocrail nach Weiche '$WEICHEN_ID' ..."

# Rocrail-Antwort empfangen
RESPONSE=$(
    printf '%s\0' "$XML_REQ" |
    timeout 3 nc "$SERVER" "$PORT" 2>/dev/null |
    tr -d '\0'
)

echo
echo "---- Rocrail-Antwort ----"
printf '%s\n' "$RESPONSE"
echo "-------------------------"
echo

# Alle <sw ...>-Elemente suchen, unabhängig von der Reihenfolge der Attribute
SWITCH_LINE=$(
    printf '%s\n' "$RESPONSE" |
    grep -oE '<sw[^>]*id="'"$WEICHEN_ID"'"[^>]*'
)

if [ -z "$SWITCH_LINE" ]; then
    echo "Weiche '$WEICHEN_ID' wurde in der Rocrail-Antwort nicht gefunden."
    exit 1
fi

echo "Gefunden:"
echo "$SWITCH_LINE"

# dir-Attribut auslesen
STATUS=$(
    printf '%s\n' "$SWITCH_LINE" |
    grep -oE 'dir="[^"]+"' |
    head -n 1 |
    cut -d'"' -f2
)

if [ -z "$STATUS" ]; then
    echo "Weiche '$WEICHEN_ID' wurde gefunden, aber kein 'dir'-Attribut."
    exit 1
fi

case "$STATUS" in
    straight)
        echo "Weiche $WEICHEN_ID steht auf: GERADE"
        ;;
    turnout)
        echo "Weiche $WEICHEN_ID steht auf: ABZWEIGEND"
        ;;
    *)
        echo "Weiche $WEICHEN_ID hat einen unbekannten Status: $STATUS"
        ;;
esac
