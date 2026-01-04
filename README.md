# SwipeList Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/jackylandhyde-boop/swipelist-homeassistant.svg)](https://github.com/jackylandhyde-boop/swipelist-homeassistant/releases)

Integriere deine [SwipeList](https://swipelist.corsch.net) Einkaufslisten in Home Assistant.

## Features

- Einkaufslisten als Todo-Entitäten
- Artikel hinzufügen, abhaken & löschen
- Automatische Synchronisation
- Mehrere Listen unterstützt
- Echtzeit-Updates

## Installation

### HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Klicke auf "Integrationen"
3. Klicke auf die drei Punkte oben rechts → "Benutzerdefinierte Repositories"
4. Füge hinzu: `https://github.com/jackylandhyde-boop/swipelist-homeassistant`
5. Kategorie: "Integration"
6. Klicke "Hinzufügen"
7. Suche nach "SwipeList" und installiere es
8. Starte Home Assistant neu

### Manuelle Installation

1. Lade dieses Repository herunter
2. Kopiere `custom_components/swipelist/` nach `config/custom_components/`
3. Starte Home Assistant neu

## Konfiguration

1. Gehe zu Einstellungen → Geräte & Dienste
2. Klicke "Integration hinzufügen"
3. Suche nach "SwipeList"
4. Gib deine SwipeList-Anmeldedaten ein
5. Fertig!

## Verwendung

Nach der Einrichtung erscheinen deine Einkaufslisten als Todo-Entitäten:

- `todo.swipelist_<listenname>`

### Automationen

```yaml
# Beispiel: Benachrichtigung wenn Liste leer ist
automation:
  - alias: "Einkaufsliste leer"
    trigger:
      - platform: state
        entity_id: todo.swipelist_wocheneinkauf
        attribute: item_count
        to: "0"
    action:
      - service: notify.mobile_app
        data:
          message: "Deine Einkaufsliste ist leer!"
```

### Services

| Service | Beschreibung |
|---------|--------------|
| `todo.add_item` | Artikel hinzufügen |
| `todo.update_item` | Artikel aktualisieren |
| `todo.remove_item` | Artikel löschen |

## Sprachsteuerung

Mit Home Assistant Voice oder Assist:

- "Füge Milch zur Einkaufsliste hinzu"
- "Was steht auf meiner Einkaufsliste?"
- "Hake Brot ab"

## Troubleshooting

### Integration wird nicht gefunden

- Stelle sicher, dass du Home Assistant neu gestartet hast
- Prüfe die Logs unter Einstellungen → System → Logs

### Login schlägt fehl

- Prüfe deine SwipeList-Anmeldedaten
- Stelle sicher, dass du Internetverbindung hast

### Listen werden nicht synchronisiert

- Prüfe die Logs auf Fehler
- Versuche die Integration zu entfernen und neu hinzuzufügen

## Links

- [SwipeList App](https://swipelist.corsch.net)
- [SwipeList im Play Store](https://play.google.com/store/apps/details?id=com.corsch.swipelist)
- [Bug melden](https://github.com/jackylandhyde-boop/swipelist-homeassistant/issues)

## Lizenz

MIT License
