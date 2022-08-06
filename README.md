![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)
[![Validate with hassfest](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hassfest.yml/badge.svg)](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hassfest.yml)
[![HACS Action](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hacs.yml/badge.svg)](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/hacs.yml)
[![CodeQL](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/vwt12eh8/hassio-ecoflow/actions/workflows/codeql-analysis.yml)

# EcoFlow Portable Power Station Integration for Home Assistant

This integration uses a local API.
Therefore, if the devices are not on the same network, they cannot synchronize their status.

This integration uses a private API.
Future device updates may prevent integration.

Requires Home Assistant Core 2022.7.0 or later for operation.

## Installation
This integration is not included by default and must be installed by yourself to use it.

Two methods are available, and you can choose one or the other.
- Install as a custom repository via HACS
- Manually download and extract to the custom_components directory

Once installed, after restarting Home Assistant, you can start integration as usual from Add Integration.

## Supported products
- ~~RIVER Mini~~ (Coming soon)
- RIVER Max
- RIVER Pro
  - Extra Battery
- DELTA Mini
- DELTA Max
  - with Extra Battery
- DELTA Pro (Wi-Fi only)
  - with Extra Battery

## How to register for the Energy Dashboard
With this integration, total input and total output energy can be obtained from the device in AC and DC respectively.

The process of excluding pass-through power is necessary to display the correct graph on the energy dashboard.

This process can easily be done using the [Pass-Through Meter](https://github.com/vwt12eh8/hassio-pass-through-meter) integration.

1. Install both the EcoFlow integration and the Pass-Through Meter integration.
2. Set up the EcoFlow integration first
3. Set up the Pass-Through Meter integration and specify the EcoFlow integration entities as follows
    - Input entities: AC input energy, Car input energy, MPPT input energy
    - Output entities: AC output energy, DC output energy
    - Device: Your EcoFlow device
    - Hide members: ON is recommended
4. Register the following entities created by the Pass-Through Meter integration in the energy dashboard as storage batteries
    - Energy charged
    - Energy discharged
5. Register the following entities created by EcoFlow integration in the energy dashboard as solar panels
    - MPPT input energy

Note that due to firmware specifications, the DELTA series devices will not correctly record the amount of power with an MPPT input of less than 20W (Pro: less than 40W).
To resolve this, create an integral helper from the DC input entity and specify it as an alternative to Car input energy and MPPT input energy in the Input Entities of the Pass-Through Meter integration.

However, this method will not record the power generated while the device is out of the LAN.

## About Remain Entities
The Remain entity is disabled by default because it is highly variable and generates a large number of writes to the database.

If enabled, it is recommended that these entities be included in the exclude in the recorder settings.
