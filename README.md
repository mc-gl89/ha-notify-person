# Notify Person

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant custom integration for **person-based notifications**.

## Features

- Create centralized notification groups in the UI
- Read persons from Home Assistant and define notification channels per person
- Assign mobile devices to persons
- Send notifications to person names instead of device entities
- Default notification setups per person (channel, criticality, importance)

## Installation

### HACS (recommended)

1. Open HACS → Integrations → Custom Repositories
2. Add repository URL: `https://github.com/mc-gl89/ha-notify-person`
3. Category: Integration
4. Install "Notify Person"
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/notify_person/` directory to your Home Assistant `custom_components/`
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration → Notify Person

## Configuration

Configure via the UI (Config Flow). The integration will:

1. Let you select which Home Assistant persons to manage
2. Assign mobile notification devices to each person
3. Set default notification preferences (channel, criticality, importance)

## Services

### `notify_person.simple_notify`

Send a simple notification to a person or group by name.

```yaml
service: notify_person.simple_notify
data:
  person: "John Doe"
  message: "Your package arrived!"
  title: "Delivery"
```

### `notify_person.advanced_notify`

Send an advanced notification with all options (channel, priority, critical, tag, actions, persistent).

```yaml
service: notify_person.advanced_notify
data:
  person: "John Doe"
  message: "Motion detected at the front door!"
  title: "Security Alert"
  channel: "security"
  priority: "high"
  critical: true
  tag: "front_door_motion"
  persistent: true
```

## Development

This integration is under active development.
