<p align="center">
  <sub>Atlas · mesh · maps</sub>
</p>

---

### Lately

| Project | Notes |
|:--|:--|
| [**Atlas-Modernization**](https://github.com/the-Drunken-coder/Atlas-Modernization) | Atlas app stack rewrite — core, protocol, SDK, command UI, simulations |
| [**Atlas-Mesh**](https://github.com/the-Drunken-coder/Atlas-Mesh) | Radio transport & mesh-routing lab under Atlas |
| [**easymanet**](https://github.com/the-Drunken-coder/easymanet) | MANET / OpenMANET provisioning and operator tooling |
| [**sidc-kit**](https://github.com/the-Drunken-coder/sidc-kit) | Compact TypeScript toolkit for Symbol Identification Codes |
| [**Meshtastic-WIFI-bridge**](https://github.com/the-Drunken-coder/Meshtastic-WIFI-bridge) | Bridge between Meshtastic radios and IP networks |

---

### About

I work on systems where the map, the radio, and the backend have to agree.

That usually means Go and TypeScript services, map consoles, mesh transports, and the smaller libraries that keep those pieces interoperable. I care about things you can run locally, measure, and replay.

---

### Atlas

Atlas is the main effort — a command-and-control style stack split across two repos right now.

#### Modernization
[`Atlas-Modernization`](https://github.com/the-Drunken-coder/Atlas-Modernization) holds the application rewrite as one workspace:

- **Core** — Go HTTP API, durable storage, object store
- **Protocol** — schemas, generated contracts, validators
- **SDK & asset runtime** — typed client, sync, telemetry/command path
- **Command interface** — Cloudflare Pages / Vite map console
- **Simulations** — local scenario workbench with a browser UI

Recent focus: feed recovery barriers, catalog/ETag behavior, SDK cursor rehydration, and tightening the simulation event stream.

#### Mesh
[`Atlas-Mesh`](https://github.com/the-Drunken-coder/Atlas-Mesh) asks a narrower question: *how should bytes move between radios on an unreliable network?*

Architecture is intentionally thin — `Radio` → `MeshProtocol` → `Simulation` → a small web replay viewer — so hardware radios and experiments stay interchangeable. The lab ships direct acknowledgement strategies (ack, stop-and-wait, …) alongside routing experiments (gateway-tree, controlled flooding, on-demand, quality-tree). The simulator is seeded and deterministic, including a measured Heltec V3 LoRa airtime model.

Latest: consolidated radio verification lab.

---

<sub>Updated 12 Aug 2026</sub>
