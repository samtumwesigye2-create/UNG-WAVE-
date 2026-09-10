# UNG-WAVE

**Wireless Access & Virtualized Edge**

UNG-WAVE is the control and networking platform for the **UGANET LINK256** portable router/repeater.

## Phase 1

The first implementation targets Raspberry Pi/Linux hardware and provides:

- network-interface and Wi-Fi radio discovery
- persistent device state
- hardware health reporting
- REST management API
- foundation for uplink, AP, NAT, DHCP/DNS, firewall and automatic recovery

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn edge.main:app --host 0.0.0.0 --port 8256
```

Then open `/health`, `/api/v1/device`, or `/api/v1/interfaces`.

## Hardware target

Prototype: Raspberry Pi / Linux

Product family: UGANET

Hardware model: LINK256
