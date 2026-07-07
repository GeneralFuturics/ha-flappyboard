# Flappy Board for Home Assistant

A Home Assistant custom integration for [Flappy Board](https://flappyboard.app) — a split-flap display simulator for iOS, iPadOS, and tvOS.

## Installation

### HACS (recommended)

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/GeneralFuturics/ha-flappyboard` with type **Integration**.
3. Search for **Flappy Board** in HACS and install it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** and search for **Flappy Board**.

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=GeneralFuturics&repository=ha-flappyboard&category=integration)

### Manual

1. Copy the `custom_components/flappyboard/` directory into your Home Assistant config directory:
   ```
   <config>/custom_components/flappyboard/
   ```
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Flappy Board**.

## Setup

During setup you'll need two values from the Flappy Board app — long-press the board to open Settings:

| Field | Description |
|-------|-------------|
| **Display name** | Any name you choose (e.g. "Living Room Board") |
| **Host or IP address** | IP address of the device running Flappy Board |
| **Port** | Default `8443` |
| **Bearer token** | Shown in the Flappy Board Settings screen |
| **TLS certificate fingerprint** | SHA-256 fingerprint shown in Settings. Strongly recommended — enables certificate pinning. Leave blank to skip (not recommended). |

Each configured board appears as a single device with three entities.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.<name>_connectivity` | Binary sensor | `on` when the board is reachable. Polls every 30 seconds. |
| `button.<name>_clear` | Button | Clears all cells on the board immediately. |
| `notify.<name>` | Notify | Sends a message to the board. |

## Sending messages

### Simple — notify entity

Use `notify.send_message` in automations and scripts:

```yaml
action: notify.send_message
target:
  entity_id: notify.living_room_board
data:
  message: "DINNER IS READY"
```

Split the message across multiple rows with newlines:

```yaml
action: notify.send_message
target:
  entity_id: notify.living_room_board
data:
  title: "GATE 12"
  message: "NOW BOARDING"
```

`title` is placed in the first row. `message` lines (split on `\n`) fill subsequent rows.

### Advanced — flappyboard.send_message service

For full control over animation and layout:

```yaml
action: flappyboard.send_message
data:
  device_id: "your_device_id"
  message: "GATE 12\nNOW BOARDING"
  transition_animation: staggered_start
  flip_speed: 1.5
  center_h: true
  center_v: false
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `device_id` | string | **Required.** The Flappy Board device to target. Use the device picker in the UI. |
| `message` | string | **Required.** Text to display. `\n` creates additional rows. Supports inline color tags: `<color='red'>TEXT</color>` |
| `flip_speed` | float | Speed multiplier. `1.0` = default, `2.0` = twice as fast, `0.5` = half speed. Omit to use the board's configured default. |
| `transition_animation` | string | How cells animate when the message appears. See options below. Omit to use the board's configured default. |
| `center_h` | boolean | Center each row horizontally within its column. Default `false`. |
| `center_v` | boolean | Center the rows vertically on the board. Default `false`. |

#### Transition animations

| Value | Description |
|-------|-------------|
| `none` | All cells flip simultaneously |
| `staggered_start` | Rows cascade top to bottom |
| `top_to_bottom` | Like staggered_start with full charset spins |
| `bottom_to_top` | Rows sweep bottom to top with full spins |
| `left_to_right` | Columns sweep left to right |
| `right_to_left` | Columns sweep right to left |
| `row_by_row` | Reading order (left→right, top→bottom) |
| `dissolve` | Each cell starts at a random time (~12 s window) |
| `diagonal` | NW→SE diagonal bands |
| `middle_out` | Center columns first, expanding outward |
| `outside_in` | Edge columns first, converging inward |
| `spiral` | Clockwise spiral from the top-left corner |
| `hatch` | Alternating rows sweep from opposite sides |
| `snake_up` | Boustrophedon sweep from the bottom-right upward |
| `matrix` | Random column offsets sweeping top to bottom |
| `random` | Picks one of the above at random each time |

## Example automations

**Welcome home message:**
```yaml
automation:
  trigger:
    platform: state
    entity_id: person.jane
    to: home
  action:
    - action: flappyboard.send_message
      data:
        device_id: "your_device_id"
        message: "WELCOME HOME\nJANE"
        center_h: true
        center_v: true
        transition_animation: dissolve
```

**Clear the board at midnight:**
```yaml
automation:
  trigger:
    platform: time
    at: "00:00:00"
  action:
    - action: button.press
      target:
        entity_id: button.living_room_board_clear
```

**Show a sensor value:**
```yaml
automation:
  trigger:
    platform: state
    entity_id: sensor.outdoor_temperature
  action:
    - action: notify.send_message
      target:
        entity_id: notify.living_room_board
      data:
        message: "OUTSIDE\n{{ states('sensor.outdoor_temperature') }}°"
```

## Security

Flappy Board uses a self-signed TLS certificate. When a fingerprint is configured, the integration uses `aiohttp.Fingerprint` to pin to that exact certificate — the same pinning mechanism used by the official Flappy Board CLI client. Without a fingerprint, certificate authenticity is not verified and a warning is logged.

The fingerprint is shown in the Flappy Board Settings screen (long-press the board on iOS/iPadOS, or use the Play/Pause command on tvOS).
