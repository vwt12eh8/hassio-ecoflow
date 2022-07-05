# EcoFlow Portable Power Station Integration for Home Assistant

This integration uses a local API.
Therefore, if the devices are not on the same network, they cannot synchronize their status.

This integration uses a private API.
Future device updates may prevent integration.

## Tested products
- [ ] RIVER Mini (Not impl)
- [x] RIVER Max
- [x] RIVER Pro
  - [x] Extra Battery
- [ ] DELTA Mini
- [ ] DELTA Max
  - [ ] Extra Battery
- [x] DELTA Pro
  - [ ] Extra Battery

## How to register for the Energy Dashboard
- MPPT input energy : Solar Panels -> Solar production energy
- total input energy : Home Battery Storage -> Energy going in to the battery
- total output energy : Home Battery Storage -> Energy coming out of the battery

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ecoflow)
