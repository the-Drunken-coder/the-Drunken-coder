<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=22&pause=1200&color=C9D1D9&center=true&vCenter=true&width=520&height=40&lines=Atlas+%C2%B7+mesh+%C2%B7+maps" alt="Atlas · mesh · maps" />
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
| [**DCS**](https://github.com/the-Drunken-coder/DCS) | Personal Agent Skills library (Plugins 1.0) — pstack, anti-ui-slop, Thermos ports |

---

### About

I work on systems where the map, the radio, and the backend have to agree — Go/TypeScript services, map consoles, mesh transports, and the small libraries that keep those pieces interoperable. Prefer things you can run locally, measure, and replay.

---

### Atlas

Main effort. Two repos: the application rewrite, and the radio/mesh lab underneath it.

```mermaid
flowchart TB
  subgraph UI["Command surface"]
    CI["Command interface<br/>map console · Cloudflare / Vite"]
    SIM["Simulations<br/>local scenario workbench"]
  end

  subgraph APP["Application stack — Atlas-Modernization"]
    SDK["SDK + asset runtime<br/>typed client · sync · telemetry"]
    PROTO["Protocol<br/>schemas · contracts · validators"]
    CORE["Core<br/>Go API · storage · object store"]
  end

  subgraph MESH["Transport lab — Atlas-Mesh"]
    WEB["Replay viewer"]
    MSIM["Deterministic simulation"]
    MP["MeshProtocol"]
    RAD["Radio"]
  end

  CI --> SDK
  SIM --> SDK
  SDK --> PROTO
  PROTO --> CORE
  CORE -. uses .-> MESH
  WEB --> MSIM
  MSIM --> MP
  MP --> RAD
```

#### Modernization

[`Atlas-Modernization`](https://github.com/the-Drunken-coder/Atlas-Modernization) — one workspace for the rewrite:

| Layer | Role |
|:--|:--|
| **Core** | Go HTTP API, durable storage, object store |
| **Protocol** | Schemas, generated contracts, validators |
| **SDK & asset runtime** | Typed client, sync, telemetry / command path |
| **Command interface** | Map console on Cloudflare Pages / Vite |
| **Simulations** | Local scenario workbench + browser UI |

Recent focus: consolidating wire contracts under Atlas Protocol, then closing a safety and type-boundary audit (credential fallbacks, storage isolation, SDK/command-interface types).

#### Mesh

[`Atlas-Mesh`](https://github.com/the-Drunken-coder/Atlas-Mesh) — narrower question: *how should bytes move between radios on an unreliable network?*

Architecture is intentionally thin: `Radio` → `MeshProtocol` → `Simulation` → web replay viewer. Direct strategies (ack, stop-and-wait, …) sit beside routing experiments (gateway-tree, controlled flooding, on-demand, quality-tree). Simulator is seeded and deterministic, including a measured Heltec V3 LoRa airtime model.

Latest: consolidated radio verification lab.

---

<sub>Updated 14 Aug 2026</sub>
