# UGANET LINK256 Cost-Down Rev-B Hardware

Date: 2026-09-10
Status: LOCKED COST-DOWN DIRECTION

## Product split

### LINK256 Base
Goal: lowest-cost autonomous UGANET Wi-Fi gateway for Ethernet/Starlink/Wi-Fi uplink.

Prototype compute: FriendlyElec NanoPi Zero2, 1 GB RAM, $27 current list price.
Wi-Fi: FriendlyElec RTL8822CE M.2 E-key module, +$6.90 current list price.
Storage: microSD for prototype; avoid expensive eMMC option.
Power: external USB-C 5 V only; no internal battery.
Target bare electronics before enclosure/antennas: about $34 plus storage, power, antennas and connectors.

Constraint: NanoPi Zero2 has USB 2.0 only. It is NOT the production choice for full-speed 5G.

### LINK256 LTE
Use the same low-cost Base platform where LTE modem throughput is acceptable over USB 2.0. Keep modem modular and removable.

### LINK256 5G
Do not throttle 5G through USB 2.0. Use a host with USB 3.x or a native M.2 B-key cellular interface.
Current engineering fallback: NanoPi R3S-LTS at $38 provides USB 3.2 Gen 1 and dual Gigabit Ethernet, but it lacks integrated Wi-Fi/M.2 E-key, so a separate Wi-Fi solution is required.
A Banana Pi BPI-R3 Mini is architecturally ideal because it integrates Wi-Fi 6, 2x 2.5GbE and M.2 B-key cellular support, but current retail pricing around $178.50 makes it unsuitable for the cost-down target.

## Antenna system

### Base / Wi-Fi
Use 2 flat adhesive dual-band antennas inside the RF-transparent top shell.
Low-cost verified examples:
- Pulse W3334B0100: 2.4/5 GHz, U.FL, adhesive, $2.50 each at DigiKey.
- TE/Linx ANT-W63-FPC2-UFL-100: 2.4/5/6 GHz, U.FL, adhesive, $5.46 each at DigiKey.

Default cost-down choice: 2x Pulse W3334B0100 unless Wi-Fi 6E is required.

### 5G
Use 4 commercial cellular antennas connected to RM520N ANT0-ANT3. Keep antennas modular rather than printing conductive RF elements. Cellular antenna selection must cover required U.S. LTE/NR bands; do not lock a narrow 2.3-5 GHz antenna as the sole production antenna because low-band coverage such as 600/700 MHz is needed.

## 3D-printable parts

Print in PETG for indoor/mobile prototypes; ASA for higher-temperature/UV/outdoor versions.

Print:
- top RF-transparent shell
- bottom shell
- internal PCB tray
- NanoPi mounting cradle
- modem carrier cradle
- antenna positioning frame
- cable-management clips
- SIM access door
- USB-C/Ethernet port surrounds
- button extensions
- wall/vehicle mounting bracket
- feet
- ventilation duct/air channels
- optional external-antenna port covers

Do not print:
- heatsinks/thermal spreaders
- RF shielding cans
- antenna conductive elements
- RF ground planes
- SMA/U.FL/MHF4 connectors
- SIM contacts
- power contacts

## Enclosure stack

Top to bottom:
1. RF-transparent PETG/ASA top shell
2. two flat Wi-Fi antennas at opposite ends/orientations
3. printed non-conductive antenna spacer/keep-out frame
4. compute/router PCB
5. metal thermal/RF spreader kept outside antenna keep-outs
6. optional LTE/5G modem carrier
7. four perimeter cellular antennas on cellular models
8. printed bottom shell

No internal battery. External USB-C power only.

## Starlink

Starlink remains an external WAN terminal. LINK256 accepts Starlink over Ethernet and redistributes it through UGANET Wi-Fi. No Starlink phased-array antenna is integrated into LINK256.

## Cost targets

LINK256 Base prototype target: $50-$70 BOM.
LINK256 LTE target: approximately $90-$140 depending on modem.
LINK256 5G: modem-dominated; current RM520N pricing keeps initial prototype substantially above Base/LTE. Continue searching for lower-cost certified 5G modems before production freeze.

## Rev-B design rules

1. Commercial modules first; custom PCB only after the architecture is proven.
2. 3D-print all non-electrical/non-thermal structural parts.
3. Preserve USB 3.x or native high-speed modem path for 5G.
4. Preserve UGANET local Wi-Fi even when all WAN links fail.
5. Preserve WAN order and failover logic in UNG-WAVE software.
6. Preserve subscription/captive-portal control independently of upstream type.
7. Do not advertise RF range until finished-enclosure OTA/range testing is complete.
