[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](.)
[![Validate with hassfest](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hassfest.yml/badge.svg)](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hassfest.yml)
[![HACS Action](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hacs.yml/badge.svg)](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hacs.yml)

# EcoFlow Portable Power Station Integration for Home Assistant

This integration uses a local API.
Therefore, if the devices are not on the same network, they cannot synchronize their status.

This integration uses a private API.
Future device updates may prevent integration.

Requires Home Assistant Core 2022.7.0 or later for operation.

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

## About Remain Entities
The Remain entity is disabled by default because it is highly variable and generates a large number of writes to the database.

If enabled, it is recommended that these entities be included in the exclude in the recorder settings.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ecoflow)
