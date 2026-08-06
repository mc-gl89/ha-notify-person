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
2. Add repository URL: `https://github.com/YOUR_USERNAME/ha-notify-person`
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

### `notify_person.notify_person`

Send a notification to a specific person by name.

```yaml
service: notify_person.notify_person
data:
  person: "John Doe"
  message: "Your package arrived!"
  title: "Delivery"
  criticality: high
```

### `notify_person.notify_group`

Send a notification to a defined group.

```yaml
service: notify_person.notify_group
data:
  group: "family"
  message: "Dinner is ready!"
  title: "Kitchen"
```

## Development

This integration is under active development.
