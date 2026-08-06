# Notify Person

A Home Assistant custom integration for person-based notifications.

## Features

- Create centralized notification groups in the UI
- Read persons from Home Assistant and define notification channels per person
- Assign mobile devices to persons
- Send notifications to person names instead of device entities
- Default notification setups per person (channel, criticality, importance)

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
2. Install "Notify Person"
3. Restart Home Assistant

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

### `notify_person.notify_group`

Send a notification to a defined group.

### `notify_person.notify_person`

Send a notification to a specific person by name.

## Development

This integration is under active development.
