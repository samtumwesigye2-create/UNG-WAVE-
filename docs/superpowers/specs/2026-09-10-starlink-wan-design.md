# LINK256 Starlink WAN + Flat Antenna Stack Design

## Goal
Add Starlink as a first-class UNG-WAVE WAN source while keeping the Starlink terminal external, and define the LINK256 flat laminated antenna packaging requirement.

## Software architecture

UNG-WAVE continues to own the local UGANET Wi-Fi network. Starlink is treated as an external satellite WAN delivered to LINK256 over Ethernet. The WAN manager classifies a configured Ethernet connection/profile as `satellite` rather than generic `ethernet`, then applies the default priority order:

1. 5G
2. Starlink / satellite
3. Ethernet
4. Wi-Fi WAN

The local UGANET AP must remain available when every WAN is down.

### Starlink identification

Because an Ethernet frame does not intrinsically identify Starlink, classification is explicit and deterministic. `WAVE_STARLINK_CONNECTIONS` is a comma-separated list of NetworkManager connection-profile names that should be treated as Starlink/satellite WANs. Matching is case-insensitive and whitespace-trimmed. A profile not listed remains ordinary Ethernet.

### Cellular truthfulness

A cellular modem must not be marked online merely because ModemManager can see it. `edge.cellular.modem_status()` must expose parsed connection state from `mmcli --output-json`, including at minimum `state` and `connected`. The WAN manager may advertise a 5G/LTE candidate as online only when `connected` is true.

### WAN status contract

`GET /api/v1/wan/status` keeps the existing response shape and candidate list. Satellite candidates use:

```json
{
  "kind": "satellite",
  "provider": "starlink",
  "interface": "eth0",
  "online": true,
  "connection": "Starlink"
}
```

Default `priority` becomes `['5g', 'satellite', 'lte', 'ethernet', 'wifi']`. 5G remains first, Starlink second, then LTE, Ethernet, Wi-Fi WAN.

## Hardware architecture

The Starlink user terminal remains external. LINK256 connects to it through Ethernet and redistributes connectivity over UGANET Wi-Fi. LINK256 does not reproduce Starlink's satellite phased-array radio.

The enclosure uses a flat RF packaging stack:

1. RF-transparent polymer top shell
2. Two flat dual-band Wi-Fi MIMO antennas at opposite ends
3. Antenna keep-out / isolation regions
4. Main compute + Wi-Fi PCB
5. RM520N-GL 5G modem and thermal spreader
6. Four perimeter 5G/LTE antenna elements
7. Bottom shell

USB 3.x and switching-regulator routing stays away from the Wi-Fi antenna regions. Metal thermal spreaders must not enter antenna keep-out zones.

## Failure behavior

- Starlink drops: UNG-WAVE automatically selects the next online WAN.
- 5G returns: default policy selects 5G again.
- Cellular modem exists but is not connected: it is not eligible as a WAN.
- No WAN is available: status is `local_only`; UGANET Wi-Fi remains available.
- Unknown Ethernet profile: classify as normal Ethernet, never guess Starlink.

## Testing

Unit tests cover:

- Starlink profile classification.
- Case-insensitive configured profile matching.
- Ordinary Ethernet classification.
- WAN priority selection with 5G, Starlink, LTE, Ethernet and Wi-Fi.
- Disconnected cellular modem excluded from online candidates.
- Connected cellular modem included.

## Non-goals

- No direct Starlink dish control.
- No Starlink phased-array implementation inside LINK256.
- No HTTPS interception.
- No satellite-provider-specific credentials stored in UNG-WAVE.
