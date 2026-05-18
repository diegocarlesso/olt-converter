# Deployment Target Architecture
> Architectural blueprint — OLT Config Converter Engine v2
> Status: **Proposed (architecture only, no implementation)**
> Author: Diego + Claude · Date: 2026-05-18
> Predecessor: Semantic Runtime (frozen at L9)
> Successor target: **Deployment-Aware Telecom Orchestration Platform**

---

## 0. Why this document exists

The engine today produces CLI that is *semantically* equivalent to the source
configuration. That was the right milestone — we proved we can take a Huawei
config, build a vendor-agnostic semantic model, and emit ZTE/Fiberhome/Datacom
CLI that means the same thing.

It is **not enough** for production deployment. A CLI block that means the same
thing is not the same as a CLI block that *runs on real hardware*. Real
deployments fail on:

- slot/board mismatch (`gpon 0/3/0` does not exist if board in slot 3 is GUMA, not GPFD)
- numbering collisions (two `ont-lineprofile-id` with the same id pointing at different DBAs)
- service-port id ranges that the target firmware rejects
- profile references to ids the target never imported
- uplink interface that does not physically exist on the chassis
- ONU placement on a PON port that is administratively shutdown or unprovisioned

The next milestone is **deployability**: every line we emit must be valid on
a *specific, known* target OLT — frame, slots, boards, ports, firmware,
profiles in flash — not just on a Platonic ideal of "a Huawei MA5800".

This document defines that platform. It is architecture only — no code is
written here. Implementation is gated on Diego's review.

---

## 1. Vision and Principles

### 1.1 Vision

Move from a **semantic converter** to a **Deployment-Aware Telecom
Orchestration Platform**. The system shall, for any supported target OLT:

1. Accept a poly-vendor source semantic model (already done).
2. Accept a **Deployment Target Descriptor** — the real or planned target
   OLT, with hardware inventory, firmware, profile catalogue, numbering
   rules and constraints.
3. Bind every semantic entity to a physical location on that target,
   resolving collisions and surfacing every unresolved decision to the
   operator with structured evidence.
4. Emit CLI that is *operationally deployable* on that exact target —
   not "approximately Huawei-ish CLI".
5. Validate the result against the same hardware/topology model — the
   validator becomes a digital twin of the OLT's own admit-checks.

### 1.2 Principles (load-bearing — every design decision rolls up here)

| # | Principle | Forces it constrains |
|---|-----------|----------------------|
| P1 | **Layer separation is sacred.** Semantic, Deployment, Provisioning, Physical, Render, Validation are six bounded contexts, never collapsed. | Forbids "shortcut" code paths that read the parser and emit CLI without going through every layer. |
| P2 | **The renderer is dumb.** A renderer never decides what slot to use, what id to allocate, what profile to bind. It receives a fully-resolved Physical Binding Plan and emits text. | Forbids `if vendor == "huawei": pick_slot(...)` inside a Jinja template or a renderer module. |
| P3 | **Provenance is total.** Every field of every entity, at every layer, carries a `Provenance` record. Inferred, defaulted, synthesised, promoted, manually-edited values are all traceable. | Forbids silent defaults. Forbids "magic" id allocation. |
| P4 | **Vendor differences live in policy, not in code branches.** A vendor's numbering rule, slot constraint, profile-id range, naming convention is *data* — loadable, editable, versionable — not an `if` branch buried in a service. | Forbids vendor-exception spaghetti. |
| P5 | **Automation level is explicit.** Every action the platform takes is classified `AUTO`, `ASSISTED`, or `MANUAL`. The operator always sees who made each decision and can demote/promote any decision. | Forbids invisible automation. Operator distrust is the failure mode. |
| P6 | **Idempotent, immutable pipeline stages.** Each stage returns a new state; no in-place mutation. State at every stage is inspectable, diffable, snapshottable. | Forbids hidden side-effects between conversion and rendering. |
| P7 | **Deployability is a checkable property.** It is computed by a validator with explicit invariants — not approximated by "looks right to a Jinja template". | Forbids "render and hope". |
| P8 | **The model survives vendor changes.** When Huawei releases V100R022 with a new profile namespace, we patch policy data, not the parser/renderer source tree. | Forbids hard-coded firmware-specific logic in shared services. |

### 1.3 Anti-Patterns we are explicitly banning

These are written down because they have been the failure modes of every
similar tool the team has seen.

| Anti-pattern | What it looks like | Why we ban it | Replaced by |
|---|---|---|---|
| Vendor exception spaghetti | `if cfg.vendor == "huawei" and cfg.firmware.startswith("V100R020"): ...` scattered across renderer modules | Untestable, untraceable, prevents new vendor onboarding | Vendor capabilities loaded from `vendor_capabilities/<vendor>/<model>.yaml`; renderer reads policy, never branches on vendor identity. |
| Profile spaghetti | One `ServiceProfile` class mutated by both semantic and deployment layers, with optional fields for everything | Reference integrity breaks the moment two flows touch it | Separate `SemanticServiceProfile` (parser/promotion) and `DeploymentSrvProfile` (deployment layer); binding is explicit. |
| Interface spaghetti | `map_interface()` with 30 special cases for ZTE C300 vs C600, Huawei MA5800 vs MA5608T, hand-edited regexes | Brittle, untestable, conflates vendor and model | `InterfaceMappingPolicy` per `(vendor, model, firmware_family)`; static YAML + composable rules. |
| Renderer coupled to hardware | Renderer asks `cfg.boards[3].board_type` and decides numbering | Couples vendor template to a deployment decision; cannot regenerate without re-deciding | Renderer consumes `PhysicalBindingPlan`; deployment layer produced it. |
| Implicit profile lifecycle | "If profile id 1 already exists, just reuse it" without auditing | Operator does not know whether their edit was discarded | Explicit `lifecycle_state` on every Deployment-layer entity; transitions are logged events. |
| Magic id allocation | `next_id = max(existing) + 1` in a renderer helper | Allocator is opaque; collisions only surface at deploy time | Centralised `IdAllocator` service with provenance, range awareness, and operator override. |
| Pipeline mutation | A stage edits the model in place to "fix" something | Earlier stages can no longer be re-run cleanly | Every stage returns a new deep-copy; ledger of transformations is the only mutable thing. |

---

## 2. Bounded Contexts — the six-layer model

The platform decomposes into **six bounded contexts**, each with its own
language, its own invariants, its own model classes, and its own services.
A message crossing a boundary goes through an explicit adapter; no internal
type of layer N is allowed to leak into layer N+1 except through that adapter.

```
                  +-----------------------------+
   source CLI --->|  L1  Semantic Runtime       |  (FROZEN — exists today)
                  +-----------------------------+
                                |
                                | semantic_to_deployment_adapter
                                v
                  +-----------------------------+
   topology   --->|  L2  Deployment Topology    |  (NEW)
   ingest         +-----------------------------+
                                |
                                | topology_to_provisioning_adapter
                                v
                  +-----------------------------+
   profile    --->|  L3  Provisioning Semantics |  (NEW)
   catalogue      +-----------------------------+
                                |
                                | provisioning_to_binding_adapter
                                v
                  +-----------------------------+
                  |  L4  Physical Binding Plan  |  (NEW)
                  +-----------------------------+
                                |
                                | binding_to_render_adapter
                                v
                  +-----------------------------+
                  |  L5  Deployment Rendering   |  (EVOLVED)
                  +-----------------------------+
                                |
                                v
                          deployable CLI
                                |
                                v
                  +-----------------------------+
                  |  L6  Operational Validation |  (NEW; cross-cuts)
                  +-----------------------------+
```

L6 is drawn last because it consumes from every previous layer, but it is
*not* a sequential stage — it is an invariant-checker that the orchestrator
can run after L4 (pre-render validation) and after L5 (post-render text
checks). It never mutates.

### 2.1 L1 — Semantic Runtime (frozen)

| Aspect | Value |
|---|---|
| Status | Frozen; do not modify shape for this initiative |
| Anchor type | `OLTConfig` (Pydantic, `models/unified_model.py`) |
| Source of truth for | Vendor-neutral *meaning*: "ONU SN HWTC1234ABCD is bound to PON pon-1/3/5, runs PPPoE on VLAN 100, has SSID Home-XYZ, …" |
| Out of scope | Hardware identity of *which* OLT will host this, *which* slot, *which* profile-id |
| Boundary | A semantic ONU has `pon_interface = "pon-1/3/5"` because that's what the source CLI said. It does **not** know whether the *target* OLT has a board in slot 3 at all. |

L2 is what converts "what the source said" into "what is real on the target".

### 2.2 L2 — Deployment Topology

| Aspect | Value |
|---|---|
| Status | New |
| Anchor type | `DeploymentTarget` |
| Inputs | `TargetDescriptor` (declared or ingested), `VendorCapabilityPack`, `FirmwareCapabilityPack` |
| Source of truth for | The physical reality of the target OLT: what frame, what slots, what board sits in each slot, what physical ports each board offers, what uplinks and PONs are wired, what firmware features are available, what numbering rules apply |
| Critical invariant | `PhysicalPort` exists iff a `Board` is in the slot and the board's port count covers the port index. No `PhysicalPort` is invented. |
| Out of scope | Profiles, ONUs, service-ports — those are L3/L4 concerns |

The Deployment Topology is the platform's **digital twin** of the target
chassis. It is independent of any specific configuration. You can load a
topology from a real OLT (via ingestion of `display board` etc.) or
declare one (greenfield deployment planning).

### 2.3 L3 — Provisioning Semantics

| Aspect | Value |
|---|---|
| Status | New |
| Anchor type | `ProvisioningCatalogue` |
| Inputs | L2 (capability constraints), L1 (semantic profile hints), Operator (catalogue management) |
| Source of truth for | The *deployable* profile catalogue of the target OLT: `DeploymentDBAProfile`, `DeploymentTrafficProfile`, `DeploymentLineProfile`, `DeploymentSrvProfile`, `DeploymentWANProfile`, with concrete ids, concrete names, concrete bindings |
| Critical invariant | Every deployment profile has an id within the target's allowed range; every internal binding (T-CONT → DBA, GEM → T-CONT, mapper VLAN → GEM) resolves within the catalogue |
| Out of scope | Which ONU consumes which profile — that is L4 |

L3 holds the profile **library** of the target. A profile lives here from
the moment it is imported, synthesised or created until the moment the
target OLT is updated. The relationship to L1 profiles is one-way:
**L1 profiles are evidence**; **L3 profiles are deployable artefacts**.

### 2.4 L4 — Physical Binding Plan

| Aspect | Value |
|---|---|
| Status | New |
| Anchor type | `PhysicalBindingPlan` |
| Inputs | L1 (semantic intent), L2 (topology), L3 (profile catalogue) |
| Source of truth for | The "who goes where with what" — every semantic ONU bound to a concrete `PhysicalPort` and concrete profile ids; every service-port allocated an id within range; every uplink mapped to a real interface |
| Critical invariant | Every binding is fully resolved (no dangling references). Collisions on (slot, port, onu_id), (service_port_id), (profile_id) are mandatory errors. |
| Out of scope | Text. The plan is a structured document, never a string. |

L4 is the **last layer before text exists**. After L4, rendering is
mechanical.

### 2.5 L5 — Deployment Rendering

| Aspect | Value |
|---|---|
| Status | Evolved from current renderers |
| Anchor function | `render(plan: PhysicalBindingPlan, target: DeploymentTarget) -> str` |
| Source of truth for | The exact byte sequence the target OLT expects |
| Critical invariant | A renderer never makes a deployment decision. If the plan says `ont-lineprofile-id 50`, the renderer emits `50`; it does not "re-allocate" |
| Out of scope | Anything not present in the plan |

A renderer becomes a thin Jinja2 driver over a resolved plan. The bulk of
the intelligence moves out of `renderers/` into `services/deployment/`.

### 2.6 L6 — Operational Validation

| Aspect | Value |
|---|---|
| Status | New; cross-cutting |
| Anchor type | `DeploymentValidator` |
| Inputs | Any of L1..L5 |
| Source of truth for | Whether the artefact at each layer satisfies the invariants of that layer and of all earlier layers it depends on |
| Critical invariant | The validator never mutates. Issues carry severity, scope, evidence, suggested fix. |
| Out of scope | Fixing. Fixers are separate services that consume validator output. |

L6 is the closest thing to a "digital admit-check" the platform offers. It
should be runnable both on the plan (pre-render) and on the rendered text
(post-render structural sanity).

---

## 3. Domain Models (Section A of the brief)

This section is a class-level outline. Every model is `pydantic.BaseModel`
with `extra="allow"` and `validate_assignment=True`, carrying a `Provenance`
where applicable. Field types and full method signatures are TBD at
implementation time; the names below are the canonical names.

### 3.1 L2 — Deployment Topology models

```
DeploymentTarget
├── target_id: str                       # stable handle
├── vendor: Vendor
├── model: str                           # "MA5800-X7", "C600", "AN5516-04", ...
├── firmware: FirmwareDescriptor
│   ├── version_family: str              # "V100R020"
│   ├── patch_level: Optional[str]
│   └── capability_pack_ref: str         # FK -> VendorCapabilityPack
├── chassis: Chassis
│   ├── chassis_id: int                  # 0 for Huawei, 1 for ZTE/Fiberhome by convention
│   ├── frame_kind: FrameKind            # MAIN | EXPANSION | STANDALONE
│   └── total_slots: int
├── slots: list[Slot]
│   └── Slot
│       ├── slot_id: int
│       ├── slot_kind: SlotKind          # CONTROL | UPLINK | SERVICE | PON | POWER | FAN | RESERVED
│       ├── allowed_board_types: list[str]   # from capability pack
│       └── board: Optional[Board]
├── boards: list[Board]
│   └── Board
│       ├── slot_id: int                 # FK -> Slot
│       ├── board_type: str              # "H805GPFD", "GTGO", "GC8B", "GUMA", ...
│       ├── board_kind: BoardKind        # GPON_LINE | XGSPON_LINE | UPLINK | CONTROL | SERVICE_SWITCH | POWER | FAN
│       ├── port_count: int              # derived from board_type
│       ├── admin_state: AdminState
│       ├── operational_state: OperationalState
│       ├── ports: list[PhysicalPort]
│       └── provenance: Provenance
├── physical_ports: list[PhysicalPort]
│   └── PhysicalPort
│       ├── port_id: PortAddr            # (chassis, slot, port_index)
│       ├── port_kind: PortKind          # GPON | XGSPON | ETHERNET | SFP | XFP | QSFP
│       ├── speed_capability: list[Speed]
│       ├── admin_state: AdminState
│       ├── description: Optional[str]
│       └── provenance: Provenance
├── logical_ports: list[LogicalPort]     # LAG / link-aggregation groups
│   └── LogicalPort
│       ├── name: str                    # "eth-trunk 1", "smartgroup 1"
│       ├── kind: LogicalPortKind        # LAG | SVI | TUNNEL
│       ├── members: list[PortAddr]
│       └── lacp: Optional[LACPConfig]
├── uplink_groups: list[UplinkGroup]
├── pon_groups: list[PONGroup]
├── numbering_rules: NumberingRules      # cached projection from capability pack
└── provenance: Provenance               # parsed | declared | ingested | manual
```

```
NumberingRules                       (data, not branching)
├── interface_format: dict[PortKind, str]
│   # e.g. for Huawei MA5800:
│   #   GPON     -> "gpon {chassis}/{slot}/{port}"
│   #   ETHERNET -> "{chassis}/{slot}/{port}"
│   # for ZTE C600:
│   #   GPON     -> "gpon-olt_{chassis}/{slot}/{port}"
│   #   ETHERNET -> "gei_{chassis}/{slot}/{port}"
├── id_ranges: dict[IdNamespace, IdRange]
│   # e.g. SERVICE_PORT -> (0, 65535)
│   #      DBA_PROFILE  -> (10, 512)
│   #      ONT_LINEPROFILE -> (1, 512)
│   #      ONT_SRVPROFILE  -> (1, 512)
│   #      TRAFFIC_TABLE  -> (1, 256)
├── reserved_ids: dict[IdNamespace, set[int]]
└── naming_conventions: dict[ProfileKind, NameConvention]
    # uppercase / no-spaces / max-len etc.
```

```
DeploymentConstraint                  (declared by capability pack OR by operator override)
├── kind: ConstraintKind               # SLOT_RESERVED | BOARD_FORBIDDEN | UPLINK_REQUIRED | NUMBERING_RULE | PROFILE_RULE
├── scope: ConstraintScope             # TARGET | SLOT | BOARD | PORT | PROFILE_NAMESPACE
├── predicate: ConstraintPredicate     # serialisable; evaluated by validator
├── severity: Severity                 # MANDATORY | RECOMMENDED | INFORMATIONAL
├── reason: str
└── provenance: Provenance
```

#### Why `Board` is split from current `models/system.Board`

The existing `models.system.Board` (slot, board_type, kind, admin_state)
stays at L1 — it is the parser's snapshot of what the source CLI declared.
The L2 `Board` lives in `models.deployment.Board` and carries port-count,
operational state, ingestion origin, and a back-reference to its slot. They
are different *roles* and must not collapse into one class. The
`semantic_to_deployment_adapter` is responsible for promoting L1 `Board`
records when the target was ingested from the source's own `show card`
output.

### 3.2 L3 — Provisioning Semantics models

```
ProvisioningCatalogue
├── target_ref: str                     # FK -> DeploymentTarget.target_id
├── dba_profiles: list[DeploymentDBAProfile]
├── traffic_profiles: list[DeploymentTrafficProfile]
├── line_profiles: list[DeploymentLineProfile]
├── srv_profiles: list[DeploymentSrvProfile]
├── wan_profiles: list[DeploymentWANProfile]
└── policy_route_profiles: list[DeploymentPolicyRouteProfile]
```

```
DeploymentLineProfile                 # Huawei: ont-lineprofile
├── profile_id: int                   # allocated in target's ONT_LINEPROFILE range
├── name: str                         # target's naming convention applied
├── tcont_bindings: list[TCONTBinding]
│   └── TCONTBinding
│       ├── tcont_id: int             # 0..7 typical Huawei
│       ├── dba_profile_ref: ProfileRef   # FK -> DeploymentDBAProfile
│       └── provenance: Provenance
├── gemport_bindings: list[GEMBinding]
│   └── GEMBinding
│       ├── gem_id: int
│       ├── tcont_id: int             # local within profile
│       ├── encryption: bool
│       ├── upstream_traffic_ref: Optional[ProfileRef]
│       ├── downstream_traffic_ref: Optional[ProfileRef]
│       ├── mapping_index: int        # mapping table position
│       └── provenance: Provenance
├── mappers: list[ProfileMapper]
│   └── ProfileMapper
│       ├── mapper_index: int         # 0..N in Huawei mapping-mode vlan
│       ├── match: MapperMatch        # vlan | priority | gem
│       └── gem_id: int
├── lifecycle_state: ProfileLifecycle  # see §9
├── source_origin: ProfileOrigin       # IMPORTED | SYNTHESISED | CLONED | MANUAL
├── source_evidence: list[str]         # references to L1 LineProfile, ingested config, etc.
└── provenance: Provenance
```

```
DeploymentSrvProfile                  # Huawei: ont-srvprofile
├── profile_id: int
├── name: str
├── port_config: PortLayout           # POTS / ETH / CATV / WiFi quantities and adaptive flags
├── ethernet_uni_overrides: list[EthernetUNIOverride]
│   # per-port VLAN mode, native vlan, translation rules
├── multicast_config: Optional[OMCIMulticast]
├── wifi_capability: Optional[WiFiCapability]
├── tr069_capability: Optional[TR069Capability]
├── catv_capability: Optional[CATVCapability]
├── voip_capability: Optional[VoIPCapability]
├── omci_extensions: list[OMCIExtension]   # vendor-specific OMCI tweaks
├── lifecycle_state: ProfileLifecycle
├── source_origin: ProfileOrigin
└── provenance: Provenance
```

```
DeploymentDBAProfile
├── profile_id: int
├── name: str
├── type: DBAType                      # type1..type5
├── fix_bandwidth_kbps: Optional[int]
├── assured_bandwidth_kbps: Optional[int]
├── max_bandwidth_kbps: Optional[int]
├── bandwidth_compensation: bool
├── lifecycle_state: ProfileLifecycle
├── source_origin: ProfileOrigin
└── provenance: Provenance
```

```
DeploymentTrafficProfile               # Huawei: traffic table ip index N
├── profile_id: int
├── cir_kbps: Optional[int]
├── cbs_bytes: Optional[int]
├── pir_kbps: Optional[int]
├── pbs_bytes: Optional[int]
├── color_mode: ColorMode
├── priority_policy: PriorityPolicy
├── priority: int
├── inner_priority: int
├── lifecycle_state: ProfileLifecycle
├── source_origin: ProfileOrigin
└── provenance: Provenance
```

```
DeploymentWANProfile
├── name: str
├── service_kind: WANServiceKind       # PPPoE | IPoE | Static | Bridged
├── default_vlan: Optional[int]
├── default_priority: Optional[int]
├── auth: Optional[WANAuth]            # PPPoE creds template, IPoE option-60 etc.
├── multicast: Optional[WANMulticast]
├── ipv6: Optional[WANIPv6]
├── nat: Optional[WANNAT]
├── lifecycle_state: ProfileLifecycle
└── provenance: Provenance
```

```
ProfileRef                            (typed reference, never bare int)
├── kind: ProfileKind                  # DBA | TRAFFIC | LINE | SRV | WAN | POLICY_ROUTE
├── target_ref: str                    # the catalogue this lives in
├── profile_id: int                    # int id within that namespace
├── name: str                          # mirror, for diagnostics
└── resolved: bool                     # false during binding, true after L4
```

### 3.3 L4 — Physical Binding Plan models

```
PhysicalBindingPlan
├── plan_id: str
├── target_ref: str                    # FK -> DeploymentTarget
├── catalogue_ref: str                 # FK -> ProvisioningCatalogue
├── semantic_ref: str                  # FK -> SessionRuntime.session_id
├── uplink_bindings: list[UplinkBinding]
├── pon_bindings: list[PONBinding]
├── onu_bindings: list[ONUBinding]
├── service_port_bindings: list[ServicePortBinding]
├── system_bindings: list[SystemBinding]    # AAA / SNMP / NTP etc., bound to mgmt interface
├── unresolved: list[UnresolvedBinding]     # explicit list of things needing operator
└── provenance: Provenance
```

```
UplinkBinding
├── semantic_uplink_ref: str           # L1 Uplink.interface
├── physical_port_ref: PortAddr        # L2 PhysicalPort (chassis, slot, port)
├── logical_port_ref: Optional[str]    # if member of a LAG
├── speed: Speed
├── vlans: VlanMembership              # native, tagged
└── provenance: Provenance
```

```
PONBinding
├── semantic_pon_ref: str              # L1 PON.interface
├── physical_port_ref: PortAddr
├── optical_overrides: Optional[PONOptical]
└── provenance: Provenance
```

```
ONUBinding
├── semantic_onu_ref: str              # L1 ONU id ("<pon-iface>:<onu_id>")
├── physical_pon_ref: PortAddr
├── onu_index: int                     # position on the PON (0..127 typical)
├── serial_number: Optional[str]
├── line_profile_ref: ProfileRef       # FK -> DeploymentLineProfile
├── srv_profile_ref: ProfileRef        # FK -> DeploymentSrvProfile
├── wan_profile_refs: list[ProfileRef] # 0..N WAN profiles bound
├── eth_overrides: list[EthernetUNIOverride]
├── ssid_overrides: list[SSIDOverride]
├── multicast_overrides: list[MulticastOverride]
└── provenance: Provenance
```

```
ServicePortBinding
├── service_port_id: int               # allocated within target's range
├── physical_pon_ref: PortAddr
├── onu_index: int
├── gem_id: int                        # within the bound line profile
├── match_vlan: Optional[int]
├── action: ServicePortAction          # replace | translate | transparent | qinq-add
├── target_vlan: Optional[int]
├── user_vlan: Optional[int]
├── inbound_traffic_ref: Optional[ProfileRef]
├── outbound_traffic_ref: Optional[ProfileRef]
└── provenance: Provenance
```

```
UnresolvedBinding                     (explicit failure mode; never silent)
├── kind: UnresolvedKind               # NO_PHYSICAL_PORT | PROFILE_NOT_IN_CATALOGUE | ID_RANGE_EXHAUSTED | ...
├── semantic_ref: str
├── evidence: list[str]
├── suggested_resolutions: list[ResolutionSuggestion]
└── severity: Severity
```

### 3.4 L5 — Rendering models (almost unchanged)

```
RenderRequest
├── plan_ref: str                      # FK -> PhysicalBindingPlan
├── target_ref: str                    # FK -> DeploymentTarget
├── render_options: RenderOptions      # include comments, sectioning, dry-run markers
└── audience: RenderAudience           # OPERATOR_REVIEW | DEPLOYMENT | DIFF

RenderResult
├── cli_text: str
├── line_provenance: list[LineProvenance]  # line N came from binding X via template Y
├── warnings: list[RenderWarning]
└── provenance: Provenance
```

### 3.5 L6 — Validation models

```
ValidationIssue
├── issue_id: str
├── severity: Severity                 # BLOCKER | ERROR | WARNING | INFO
├── layer: Layer                       # L1..L5
├── code: str                          # e.g. "DEPLOY-PON-NO-BOARD", "PROFILE-ID-RANGE-EXCEEDED"
├── scope_refs: list[EntityRef]        # which entities are involved
├── message: str
├── evidence: list[str]
├── suggested_fixes: list[Fix]
└── provenance: Provenance             # which validator raised it, when
```

```
DeploymentReadiness
├── target_ref: str
├── plan_ref: str
├── verdict: Verdict                   # READY | READY_WITH_WARNINGS | BLOCKED
├── issues: list[ValidationIssue]
├── statistics: dict[str, int]         # entity counts, coverage, etc.
└── timestamp: float
```

### 3.6 Capability and intent models (cross-cutting)

```
VendorCapabilityPack                  (data, loaded from YAML)
├── vendor: Vendor
├── model_family: str                  # "MA5800-Xn", "C600-series"
├── supported_models: list[str]
├── allowed_board_types: dict[str, BoardSpec]
│   # BoardSpec: kind, port_count, port_kind, speed_capabilities, slot_kinds_allowed
├── numbering_rules: NumberingRules
├── id_namespaces: dict[IdNamespace, IdRange]
├── default_constraints: list[DeploymentConstraint]
├── feature_flags: dict[str, bool]    # has_xgs_pon, supports_ont_srvprofile, ...
└── version: str                       # this pack's own semver
```

```
FirmwareCapabilityPack
├── vendor: Vendor
├── version_family: str                # "V100R020"
├── deltas_from_family_base: dict      # overrides for ranges / feature_flags / commands
└── version: str
```

```
ServiceIntent                         (operator-level desired state)
├── intent_id: str
├── kind: IntentKind                   # ROLLOUT_ONU | MIGRATE_PROFILE | RETIRE_BOARD | UPLINK_FAILOVER
├── parameters: dict
├── target_refs: list[EntityRef]
├── automation_level: AutomationLevel  # AUTO | ASSISTED | MANUAL
└── provenance: Provenance
```

`ServiceIntent` is the long-term primitive that allows the platform to
move from "render this exact config" to "achieve this outcome on this
target". It is declared here for completeness; implementation is later.

---

## 4. Mapping Graph (Section B of the brief)

The most failure-prone area of any converter is the *cross-layer mapping*.
We make it a first-class concept: a typed directed graph, walked by an
explicit resolver, with auditable evidence on every edge.

### 4.1 Edge types

```
Semantic                  Deployment                Physical                  Render

ONU ─────────────── ONUBinding ──── PhysicalPort (PON) + onu_index ─── ONT line in CLI
                       │
                       ├── ProfileRef (Line)  ── DeploymentLineProfile ── ont-lineprofile block
                       └── ProfileRef (Srv)   ── DeploymentSrvProfile  ── ont-srvprofile block

ServicePort ──── ServicePortBinding ── id within target's range ─── service-port line

Uplink ──────── UplinkBinding ── PhysicalPort (uplink-kind) + LAG ─── uplink block

PON ─────────── PONBinding ── PhysicalPort (gpon-kind) ────────── interface block

VLAN ──────── (no binding required; pure data) ─────────────── vlan block

DBA/Traffic/Line/Srv profile ── DeploymentXProfile ── id within range ─── profile block
```

### 4.2 The resolver — `MappingGraphResolver`

A single service is responsible for walking the graph and producing the
plan. It is **the** place that knows how to bind semantic to deployment.
Renderer code never calls into it; renderer code consumes its output.

Resolver inputs:
- `semantic_config: OLTConfig` (L1)
- `deployment_target: DeploymentTarget` (L2)
- `provisioning_catalogue: ProvisioningCatalogue` (L3)
- `binding_policy: BindingPolicy` (operator overrides + defaults)

Resolver outputs:
- `PhysicalBindingPlan`
- `list[UnresolvedBinding]`
- structured trace (for the audit log and for the UI to surface evidence)

Resolver algorithm (deterministic; no `random`, no clock, no env-var-driven
branches):
1. Resolve uplinks first (they constrain the rest — a service-port that
   tags vlan 100 needs vlan 100 to leave the chassis somewhere).
2. Resolve PONs — bind each semantic PON.interface to a physical
   GPON-kind port. Refuse if no matching slot/board.
3. Resolve ONUs — bind to PON, assign `onu_index`, pick `LineProfile` and
   `SrvProfile` from the catalogue. If the catalogue lacks a suitable
   profile, raise an `UnresolvedBinding(PROFILE_NOT_IN_CATALOGUE)` with
   suggestions (synthesise / clone / manual / import from real OLT).
4. Resolve service-ports — allocate ids within the target's
   `SERVICE_PORT` range using `IdAllocator`. Detect collisions early.
5. Resolve system bindings (AAA, SNMP, NTP, mgmt interface).
6. Run cross-resolver validation (e.g. profile referenced by ONU exists
   in catalogue and is in `LINKED` state).

### 4.3 BindingPolicy

```
BindingPolicy
├── pon_strategy: PonStrategy           # PRESERVE_SOURCE_NUMBERING | REMAP_TO_TARGET | OPERATOR_CHOICE
├── id_allocation_strategy: IdStrategy  # PRESERVE_OR_REASSIGN | ALWAYS_REASSIGN | DENSE_PACK
├── profile_strategy: ProfileStrategy   # MATCH_BY_NAME | MATCH_BY_SHAPE | NEW_PROFILE_PER_INTENT
├── on_id_collision: CollisionAction    # ABORT | SHIFT | REUSE_IF_IDENTICAL
├── on_missing_profile: MissingAction   # ABORT | SYNTHESISE | CLONE_NEAREST | ASK_OPERATOR
├── on_missing_board: BoardAction       # ABORT | ASK_OPERATOR | ASSUME_PLANNED
└── automation_levels: dict[Step, AutomationLevel]
```

`BindingPolicy` is the explicit shape of the operator's preferences. It is
saved per-target (or per-deployment-session), versioned, and editable. It
is the *only* knob the resolver responds to — there are no implicit
defaults that the operator cannot override.

### 4.4 IdAllocator

A separate service. Stateful within a binding session. Responsibilities:

- Maintain per-`IdNamespace` allocators bounded by the target's
  `id_ranges` and `reserved_ids`.
- Honour `PRESERVE_OR_REASSIGN` (try to keep the source's id; reassign on
  conflict, recording the new id and the reason).
- Emit `Provenance` for every assigned id: which strategy, which input,
  what conflicts were resolved.
- Refuse to allocate outside the namespace's `IdRange`.

This service is the **single point of truth** for "what id does this
profile/service-port get". Renderer reads `binding.service_port_id` —
never invents one.

### 4.5 InterfaceMappingPolicy

Today: `services/mapping.py` + `mapping_data.yaml`, an explicit 1:1
table. That model is a special case of:

```
InterfaceMappingPolicy
├── source_vendor: Vendor
├── source_model_family: str
├── target_vendor: Vendor
├── target_model_family: str
├── pattern_rules: list[PatternRule]
│   # regex-based, but expressed as named-group rules, not free regex
└── explicit_overrides: list[InterfaceOverride]
```

Pattern rules are written *once per vendor pair*, not per interface.
Operator overrides live in `explicit_overrides`, taking precedence.

---

## 5. Automation Levels (Section C of the brief)

Every action the platform performs has an explicit automation level. This
is encoded both in the code path that performs the action and in the audit
log of the action itself, so the operator can always see (a) what happened
automatically, (b) what was assisted, (c) what was a pure operator choice.

### 5.1 Three levels

| Level | Semantics | Example |
|---|---|---|
| AUTO | Platform makes the decision unilaterally. Recorded in audit; operator can revert. | Allocating a service-port id from `PRESERVE_OR_REASSIGN` strategy when the source id falls within target's range. |
| ASSISTED | Platform proposes one or more options ranked by confidence; operator picks. UI surfaces the proposals; nothing is committed until the operator confirms. | "This source profile `LINE-1G-PPPOE` does not exist in the catalogue. Suggested actions: (1) import nearest match `lineprofile-id 50`, (2) clone+rename, (3) synthesise new at id `512`." |
| MANUAL | Platform refuses to decide. Operator must supply the value. UI gates progression until value is supplied. | "Slot 3 of the target chassis has no board declared. Cannot bind PON pon-1/3/5 without slot 3 board." |

### 5.2 Per-step defaults

| Pipeline step | Default level | Promotable to | Demotable to |
|---|---|---|---|
| Topology ingestion | AUTO | — | ASSISTED if conflicts |
| PON binding | AUTO | — | MANUAL on missing board |
| ONU placement | AUTO | — | ASSISTED on duplicate SN |
| Profile lookup in catalogue | ASSISTED | AUTO if `MATCH_BY_NAME` and unique hit | MANUAL on `on_missing_profile=ABORT` |
| Profile synthesis | ASSISTED | — | MANUAL |
| Profile clone | ASSISTED | — | MANUAL |
| Profile creation | MANUAL | ASSISTED if template provided | — |
| Service-port id allocation | AUTO | — | ASSISTED on collisions |
| Uplink binding | ASSISTED | AUTO if only one uplink board | MANUAL on missing uplink ports |
| Renderer execution | AUTO | — | — (renderer never asks the operator) |
| Validation reporting | AUTO | — | — |

### 5.3 Operator overrides

The operator can:
- *Demote* an AUTO step to ASSISTED ("always ask me before allocating
  profile ids in this catalogue") — useful for production-frozen
  catalogues.
- *Promote* an ASSISTED step to AUTO with a saved policy ("always pick
  the highest-confidence profile match") — useful for bulk migrations.
- Never *promote* a MANUAL step beyond ASSISTED; MANUAL is reserved for
  decisions the platform cannot safely make.

These overrides live in `BindingPolicy.automation_levels`.

---

## 6. Renderer Evolution (Section D of the brief)

### 6.1 Current state

Today, renderers in `renderers/{vendor}/{model}/renderer.py` build context
via a `_context(config)` helper, then drive Jinja2 templates with the
semantic `OLTConfig`. The renderer often inspects the semantic config and
applies vendor-specific transformations inline (e.g. `map_interface(...)`
at template-time).

### 6.2 Target state

A renderer becomes:

```
def render(plan: PhysicalBindingPlan, target: DeploymentTarget) -> RenderResult:
    ctx = _context(plan, target)   # pure projection, no decisions
    text = _drive_templates(ctx)
    return RenderResult(cli_text=text, line_provenance=_emit_provenance(),
                        warnings=_emit_warnings(), provenance=_self_prov())
```

Constraints:
- `_context` is a **pure projection** of the plan: it copies fields into
  a Jinja-friendly dict. It does not make decisions. It does not call
  `map_interface()`. By the time the plan reaches the renderer, all
  interfaces are already in the target's canonical form.
- `_drive_templates` walks templates in a fixed order, each template
  consuming a *slice* of the projected context (`ctx.uplinks`, `ctx.pon`,
  `ctx.ont_lineprofiles`, …). Templates use `dict.get` everywhere
  (StrictUndefined remains in force).
- `_emit_provenance` records, per output line, which binding/profile in
  the plan was responsible. This is consumed by the Diff UI and the
  audit log.

### 6.3 Template reorganisation

Today's templates per vendor:
```
templates/huawei/ma5800/{header,boards,system,uplinks,gpon,dba,traffic_tables,
                        lineprofiles,srvprofiles,service_port,onts,subscriber_edge,footer}.j2
```

Same files survive. What changes:
- Each `.j2` consumes a slice of `PhysicalBindingPlan` projected by
  `_context`, not the raw `OLTConfig`.
- New templates: `boards.j2` and `header.j2` consume `DeploymentTarget`,
  not the source's parsed boards — the rendered boards reflect what we
  intend to deploy, not what the source had.
- Removed responsibilities: no template calls `map_interface()`; all
  interfaces in the projection are pre-mapped.

### 6.4 Renderer registry

Today: `renderers/registry.py` maps `(vendor, model)` to a renderer
factory. We keep that registry, but extend the factory signature:

```
register(vendor, model_family, factory=lambda target, plan: HuaweiMA5800Renderer(...))
```

This makes a renderer addressable per *model family*, not per vendor — so
MA5800 and MA5608T can share parts and override differences via the
target descriptor.

### 6.5 Backwards compatibility

The legacy `render(config)` entry point survives during the transition by
delegating to a "thin" deployment pipeline that:
1. Builds a `DeploymentTarget` declared from the semantic config (with
   `provenance.source=DEFAULT`, `confidence=0.3`, `needs_review=True`).
2. Builds a catalogue by promoting L1 profiles into L3 with
   `lifecycle_state=PROPOSED`.
3. Runs the resolver with permissive `BindingPolicy`.
4. Renders.

The legacy call therefore keeps working, but emits CLI marked as
"unanchored" (because no real target was bound). The fidelity report
reflects this.

---

## 7. Frontend Evolution (Section E of the brief)

### 7.1 Today

The UI is a "Runtime Explorer + Inspector + CLI Preview" triptych. It
addresses **semantic** editing only. There is no concept of "target",
"slot", "board", "uplink mapping", or "profile lifecycle".

### 7.2 Tomorrow — Deployment Engineering Cockpit

The UI gains four new top-level surfaces, accessible from a new left-rail
mode switch:

1. **Targets** — manage `DeploymentTarget`s: declare new, import from
   show-command dump, edit chassis/slots/boards, version capability
   packs.
2. **Catalogues** — Profile Mapping Studio: per-target, browse and edit
   `DeploymentLineProfile`, `DeploymentSrvProfile`, `DeploymentDBAProfile`,
   `DeploymentTrafficProfile`, `DeploymentWANProfile`. Editors are
   schema-driven. Each profile shows its `lifecycle_state`, `source_origin`,
   referenced-by-count, and a "promote/demote" action.
3. **Binding** — Mapping Graph viewer: for a given semantic session and a
   chosen target+catalogue, walk the graph. Surface every `UnresolvedBinding`
   as a card with the resolver's evidence and the operator's options.
4. **Render & Validate** — the CLI Preview, but now anchored. Shows the
   plan-to-CLI provenance: click a CLI line, the Binding Graph highlights
   the source binding.

The existing Semantic Runtime Explorer remains, but is renamed
"Semantic Model" and sits as the leftmost surface — it is now one of
several views on the session.

### 7.3 New components (sketch)

| Component | Role |
|---|---|
| `TargetCatalogueSidebar` | List of `DeploymentTarget`s, mark active. |
| `ChassisDesigner` | Visual slot grid; drop boards; declare ports. (Densest visual; no animations.) |
| `BoardInspector` | Edit/audit a single board: type, kind, ports, admin state, provenance. |
| `UplinkMapperPanel` | Each L1 Uplink ↔ a `PhysicalPort` on the active target. Diff against current binding. |
| `PONMapperPanel` | Each L1 PON ↔ a `PhysicalPort`. Highlight unmapped, dual-use, or non-existent. |
| `ProfileCatalogueSurface` | Master/detail Profile editors per profile kind. Search, filter by lifecycle, clone, synthesise from L1. |
| `LineProfileEditor` | T-CONT bindings, GEM bindings, mappers, with DBA-ref autocomplete. |
| `SrvProfileEditor` | Port layout, ethernet-UNI overrides, multicast, wifi/voip/catv capabilities. |
| `DBAProfileEditor`, `TrafficProfileEditor`, `WANProfileEditor` | Inline schema-driven forms. |
| `BindingGraphViewer` | Side-by-side semantic↔deployment↔physical, click-to-pivot. |
| `UnresolvedBindingsQueue` | Worklist of issues, sorted by severity, with resolution affordances. |
| `IdAllocationLedger` | Audit view of every id allocated, by which strategy, with conflict log. |
| `ProvenanceInspector` | Inline panel — for any selected entity at any layer, show provenance chain. |
| `RenderAnchorView` | Monaco split: left CLI, right `BindingGraph`. Click line → highlight binding. |
| `DeploymentReadinessReport` | Top of Render surface — verdict, count of blockers/errors/warnings, drill-in. |

### 7.4 Operator workflow

The UI shall make the following workflow first-class:

1. Operator opens a semantic session (existing, today).
2. Operator picks or declares a `DeploymentTarget` (new).
3. Platform proposes a `ProvisioningCatalogue` by promoting L1 profiles
   (new); operator reviews each promotion (ASSISTED).
4. Platform proposes a `PhysicalBindingPlan`; UI surfaces unresolved
   bindings in a queue.
5. Operator works through the queue. Each resolution edits the plan and
   re-runs the resolver for the impacted slice.
6. When `DeploymentReadiness.verdict in {READY, READY_WITH_WARNINGS}`, the
   Render surface unlocks for export.

### 7.5 State management

Backend remains the single source of truth (per the existing
`SessionRuntime` contract). The new surfaces extend the session with:

- `target_ref` field on session (which target is active).
- `catalogue_ref` field on session (which catalogue is active).
- `plan_ref` field on session (most recent plan).
- new endpoints on `/api/v1/sessions/{sid}`:
  `GET/PUT /target`, `GET/POST /catalogue/profiles/{kind}`, `POST /binding/run`,
  `GET /binding/plan`, `POST /binding/resolve`, `GET /readiness`.

Frontend Zustand state remains *view-only*: which surface is active,
which entity is selected, which filter chips are toggled. All edits route
through the session API.

---

## 8. Operational Validation (Section F of the brief)

### 8.1 Validator architecture

`OperationalValidator` is a single service that holds a list of
`InvariantRule` instances. A rule has:

```
InvariantRule
├── code: str                          # stable id, e.g. "DEPLOY-PON-NO-BOARD"
├── layer: Layer
├── severity: Severity
├── scope_predicate: Callable          # selects entities to check
├── check: Callable                    # returns list[ValidationIssue]
└── description: str
```

Rules are registered, not branched. A new vendor adds rules without
touching the validator's core.

### 8.2 Invariant catalogue (initial)

| Code | Layer | Severity | What it checks |
|---|---|---|---|
| `TOPO-SLOT-BOARD-MISMATCH` | L2 | ERROR | `Board.board_type` is in `Slot.allowed_board_types` for that slot's `slot_kind`. |
| `TOPO-PORT-COUNT-MISMATCH` | L2 | ERROR | `Board.port_count` matches the capability pack's `BoardSpec.port_count`. |
| `TOPO-DUPLICATE-PORT` | L2 | BLOCKER | No two `PhysicalPort`s share `(chassis, slot, port_index)`. |
| `TOPO-FIRMWARE-FEATURE-MISSING` | L2 | ERROR | A configured feature requires a firmware capability the target lacks. |
| `CAT-PROFILE-ID-RANGE-EXCEEDED` | L3 | BLOCKER | `profile_id` is within `id_ranges[<namespace>]`. |
| `CAT-PROFILE-ID-COLLISION` | L3 | BLOCKER | No two profiles in the same namespace share `profile_id`. |
| `CAT-PROFILE-INTERNAL-DANGLING` | L3 | ERROR | A `TCONTBinding.dba_profile_ref` resolves inside the catalogue. |
| `CAT-PROFILE-NAME-CONVENTION` | L3 | WARNING | Profile name matches the target's `NameConvention`. |
| `BIND-PON-NO-BOARD` | L4 | BLOCKER | Every `PONBinding.physical_port_ref` points at a board of `GPON_LINE` kind. |
| `BIND-UPLINK-WRONG-KIND` | L4 | BLOCKER | `UplinkBinding.physical_port_ref` is on a board of `UPLINK` kind. |
| `BIND-ONU-NO-PROFILE` | L4 | BLOCKER | Every `ONUBinding` has resolved `line_profile_ref` and `srv_profile_ref`. |
| `BIND-SERVICEPORT-ID-COLLISION` | L4 | BLOCKER | `service_port_id` is unique. |
| `BIND-SERVICEPORT-OUT-OF-RANGE` | L4 | BLOCKER | `service_port_id` is within target's range. |
| `BIND-ONU-INDEX-OUT-OF-RANGE` | L4 | BLOCKER | `onu_index` is within the bound PON's max-ONUs (Huawei 128, ZTE depends). |
| `BIND-VLAN-NOT-CARRIED-BY-UPLINK` | L4 | ERROR | Every `match_vlan/target_vlan` referenced by a service-port is carried by at least one bound uplink. |
| `BIND-DUPLICATE-SERIAL` | L4 | ERROR | No two ONUs share a serial within the same target. |
| `BIND-LINEPROFILE-REFS-MISSING-DBA` | L4 | ERROR | The selected `DeploymentLineProfile`'s T-CONT bindings reference DBAs that are present in the catalogue. |
| `RENDER-LINE-NO-PROVENANCE` | L5 | WARNING | Every emitted CLI line has a binding-provenance entry. |
| `RENDER-SECTION-MISSING` | L5 | ERROR | Mandatory sections (header, system, uplinks, gpon, profiles, onts, service-port, footer) are present. |
| `RENDER-PROFILE-NOT-IN-CATALOGUE` | L5 | BLOCKER | Every profile id emitted by the renderer appears in the catalogue. |
| `VAL-AUTOMATION-LEVEL-VIOLATION` | cross | ERROR | A MANUAL step was completed by an AUTO writer (programming error). |

### 8.3 Reporting

Validation output is structured. The UI renders it as a triage list. The
CLI/API exposes `GET /api/v1/sessions/{sid}/readiness` returning a
`DeploymentReadiness`. The terminal `fidelity_report.py` is extended to
include a "deployability" section per (source, target) pair.

### 8.4 What validation never does

- Mutate any model. Only `Fix` services may mutate, and only when
  invoked explicitly.
- Heuristic guessing. If evidence is missing, the validator emits
  `INFO` and the issue is surfaced for the operator to investigate.
- Crash a render. A blocker stops *deployment*, not *rendering* — the
  rendered text is still produced (it just must not be pushed to the
  OLT).

---

## 9. Profile Lifecycle

A `DeploymentXProfile` lives in the catalogue, but it has a **state**.
The lifecycle is explicit so the operator always knows what they are
looking at and what the resolver will do with it.

### 9.1 States

| State | Meaning | Resolver may bind to it? | Renderer may emit it? |
|---|---|---|---|
| DRAFT | Created by the operator, not yet validated. | No | No |
| PROPOSED | System suggested (e.g. by promotion from L1). Operator has not reviewed. | No | No |
| LINKED | Reviewed, accepted, references resolved. Ready for use. | Yes | Yes |
| FROZEN | Linked + explicitly locked by operator. Cannot be edited without unfreezing. | Yes | Yes |
| DEPRECATED | Still in catalogue for audit, but resolver must not pick it for new bindings. | No (existing bindings preserved) | Yes (for existing only) |
| RETIRED | Soft-deleted. Not visible by default. | No | No |

### 9.2 Transitions

```
DRAFT     ──(validate)─→ LINKED        ──(freeze)─→ FROZEN
PROPOSED  ──(accept)──→ LINKED         ──(deprecate)─→ DEPRECATED ──(retire)─→ RETIRED
PROPOSED  ──(reject)──→ RETIRED
LINKED    ──(unfreeze on FROZEN)←──────  edit       (back to DRAFT only if no bindings reference)
```

Transitions are operator-driven (MANUAL) by default. Validation gates the
DRAFT → LINKED transition. Promotion from L1 to L3 creates PROPOSED.

### 9.3 Provenance interactions

Every state transition is appended to the audit log with:
- `actor` (operator id or "system")
- `from_state`, `to_state`
- `reason`
- `evidence` (validation result, source artefact, etc.)

### 9.4 Origin

`source_origin` is orthogonal to `lifecycle_state`:

| Origin | Meaning |
|---|---|
| IMPORTED | Loaded from a real OLT's `display`/`show` output. |
| SYNTHESISED | Built from L1 evidence (existing `synthesis` service). |
| CLONED | Duplicated from another DeploymentXProfile in the same catalogue. |
| MANUAL | Created from scratch by the operator. |
| PROMOTED | Promoted from a Semantic L1 profile (this initiative). |

Origin never changes; state can change many times. This pair is what the
Profile editor UI surfaces at the top of every detail panel.

---

## 10. Topology Ingestion Pipeline

A `DeploymentTarget` can be constructed three ways:

1. **Declared** — operator fills out the chassis/slots/boards form in
   the UI, picks a model+firmware from the catalogue.
2. **Imported from show-command dump** — operator uploads a text file
   containing the output of vendor-specific show commands.
3. **Inferred from semantic config** — fallback: build a *speculative*
   target from the parsed source. Always marked `provenance=DEFAULT`,
   `needs_review=True`. Used by the legacy compatibility shim.

This section covers (2), the production path.

### 10.1 Per-vendor command-set

| Vendor | Required | Optional | Notes |
|---|---|---|---|
| Huawei MA5800 | `display board 0`, `display interface`, `display service-port all`, `display ont-lineprofile`, `display ont-srvprofile` | `display dba-profile`, `display traffic table ip`, `display vlan all`, `display sysname`, `display version` | Profile dumps may be huge — paginated parsing. |
| ZTE C600 | `show card`, `show interface`, `show service-port`, `show running-config gpon`, `show vlan` | `show running-config interface`, `show version` | Dual syntax era (`gpon-olt_` vs `gpon_olt-`); ingestion accepts both. |
| Fiberhome AN5516 | `show card`, `show running-config interface`, `show service-port`, `show running-config dba-profile`, `show running-config service-profile` | `show version`, `show sysname` | WOS-style; line continuation rules apply. |
| Datacom DM4615 | `show running-config gpon`, `show interface description` | `show version` | Lower priority. |

### 10.2 Parsers — `parsers/ingest/<vendor>/<model>/`

Each vendor gets a sibling tree to `parsers/<vendor>/<model>/` named
`parsers/ingest/<vendor>/<model>/` that knows how to read show outputs
(not running-config). The two are *separate parsers*: a running-config
parser populates L1; an ingestion parser populates L2/L3.

Both share lexical helpers (`utils/cli/`) for line continuation, banner
stripping, prompt detection.

### 10.3 Ingestion output

```
IngestionResult
├── target: DeploymentTarget               # L2 fully populated
├── catalogue: ProvisioningCatalogue       # L3 partially populated (profiles only)
├── inventory_only: bool                    # True when only `display board` was provided
├── warnings: list[IngestionWarning]
└── unparsed_lines: list[str]
```

An ingestion is *partial* when commands are missing — e.g. only
`display board` was supplied, no profile dumps. The result is still
useful (you get a topology), but the catalogue is empty and the resolver
will surface "no profile in catalogue" issues until the operator imports
or synthesises.

### 10.4 Persistence

Targets and catalogues are persistable per session and globally. Globally
persisted targets become reusable "site descriptors" — the operator can
plan multiple sessions against the same MA5800 in slot config X.

Storage model: filesystem-backed (`./targets/<target_id>.json`) for the
prototype; promotable to a DB later. The session refers to a target by
`target_id` regardless of backing store.

### 10.5 Diff against real OLT

A useful side-product: once we can ingest a real target, we can also
*diff* the rendered CLI against the target's current state. This is a
later milestone (`RenderAudience.DIFF`) but the ingestion pipeline is
the prerequisite.

---

## 11. Deployment Session Model

The existing `SessionRuntime` is the *semantic* session: a parsed source +
indexes + validation + render cache for the semantic model.

We introduce a **DeploymentSession** that wraps a semantic session and
adds the new layers.

```
DeploymentSession
├── deployment_session_id: str
├── semantic_session_ref: str             # FK -> SessionRuntime.session_id
├── target_ref: Optional[str]              # FK -> DeploymentTarget
├── catalogue_ref: Optional[str]           # FK -> ProvisioningCatalogue
├── plan_ref: Optional[str]                # FK -> PhysicalBindingPlan (latest)
├── binding_policy: BindingPolicy
├── readiness_cache: Optional[DeploymentReadiness]
├── render_cache: dict[RenderAudience, str]
├── audit_log: list[DeploymentAuditEntry]
├── snapshots: list[DeploymentSnapshot]
└── locks: SessionLocks                   # which other operators are editing what
```

Notable design choices:
- A `DeploymentSession` *wraps* a `SessionRuntime`. The semantic
  session keeps its existing API and lifecycle. Patches at L1 propagate
  down: the resolver listens for invalidation events from
  `SessionRuntime.apply_patch` and marks the plan as `stale`. The next
  call to `/binding/plan` re-runs the resolver.
- Snapshots cover the *whole* deployment session (target+catalogue+plan
  +policy), not just the plan. This is what supports "what-if" analysis
  ("snapshot, change service-port strategy, compare diff, restore").
- The audit log is append-only. The undo/redo stack mirrors snapshots,
  with a separate retention bound (50 by default, configurable).
- `SessionLocks` is a placeholder for multi-operator coordination. The
  prototype runs single-operator; the data shape supports per-entity
  locking from day one to avoid migration later.

### 11.1 Session lifecycle

```
created
  → semantic_session_attached
    → target_attached
      → catalogue_initialised
        → policy_set
          → binding_resolved (first time)
            ↺ binding_resolved (each L1 patch or operator edit invalidates and re-resolves)
              → readiness_ready
                → render_committed
                  → exported (CLI handed off; session remains for audit)
```

### 11.2 Endpoint surface (extends current `routes.py`)

```
POST   /api/v1/sessions/{sid}/deployment              attach a deployment session
GET    /api/v1/sessions/{sid}/deployment              fetch state
DELETE /api/v1/sessions/{sid}/deployment              detach

GET    /api/v1/targets                                 list global targets
POST   /api/v1/targets                                 create / declare target
POST   /api/v1/targets/import                          ingest from show-dump
GET    /api/v1/targets/{tid}                           detail
PATCH  /api/v1/targets/{tid}                           edit (board/slot)
DELETE /api/v1/targets/{tid}

GET    /api/v1/sessions/{sid}/deployment/target       active target ref
PUT    /api/v1/sessions/{sid}/deployment/target       attach a target

GET    /api/v1/sessions/{sid}/deployment/catalogue    catalogue summary
GET    /api/v1/sessions/{sid}/deployment/catalogue/profiles/{kind}
POST   /api/v1/sessions/{sid}/deployment/catalogue/profiles/{kind}
PATCH  /api/v1/sessions/{sid}/deployment/catalogue/profiles/{kind}/{pid}
DELETE /api/v1/sessions/{sid}/deployment/catalogue/profiles/{kind}/{pid}
POST   /api/v1/sessions/{sid}/deployment/catalogue/promote   promote from L1
POST   /api/v1/sessions/{sid}/deployment/catalogue/synthesise

POST   /api/v1/sessions/{sid}/deployment/binding/run          run resolver
GET    /api/v1/sessions/{sid}/deployment/binding/plan         latest plan
GET    /api/v1/sessions/{sid}/deployment/binding/unresolved   list issues
POST   /api/v1/sessions/{sid}/deployment/binding/resolve      apply an operator resolution

GET    /api/v1/sessions/{sid}/deployment/readiness            readiness report
POST   /api/v1/sessions/{sid}/deployment/render               render with audience

GET    /api/v1/sessions/{sid}/deployment/audit
GET    /api/v1/sessions/{sid}/deployment/snapshots
POST   /api/v1/sessions/{sid}/deployment/snapshot
POST   /api/v1/sessions/{sid}/deployment/restore/{snap_id}
```

The semantic endpoints remain untouched; deployment endpoints are
additive.

---

## 12. Invariants & Contracts (cross-cutting)

These are the platform-wide contracts that every layer commits to.

### 12.1 Provenance invariant

> Every entity at every layer carries a `Provenance`. A renderer must not
> emit any line backed by an entity with `provenance.source=DEFAULT` and
> `confidence < 0.5` unless `RenderOptions.allow_default_fallback=True`
> (off by default). Validator rule `RENDER-DEFAULT-FALLBACK` checks this.

### 12.2 Deep-copy invariant

> Each pipeline stage returns a new object. In-place mutation is reserved
> for `SessionRuntime.apply_patch` and equivalent explicit edit paths.
> Tests assert this via `id()` checks on stage outputs.

### 12.3 Adapter invariant

> A layer's types are imported from the next layer *only* via the named
> adapter module: `adapters/semantic_to_deployment.py`,
> `adapters/deployment_to_provisioning.py`, etc. Static import-graph tests
> enforce this.

### 12.4 Renderer purity invariant

> Renderers do not import from `services/deployment/`,
> `services/inference.py`, `services/synthesis.py`, `services/mapping.py`,
> or anywhere a *decision* is made. They import only from
> `models/`, `models/deployment/`, and `templates/`. Static import-graph
> tests enforce this.

### 12.5 Idempotency invariant

> Running the resolver twice on the same `(semantic, target, catalogue,
> policy)` produces byte-identical plans. Differences ⇒ a bug. Tests
> assert this via golden-file comparison.

### 12.6 ID allocation invariant

> No id appears in a render that was not allocated by `IdAllocator`. Every
> allocated id has a recorded strategy, input id (if any), and conflict
> set. Validator rule `BIND-ID-NOT-ALLOCATED` enforces this.

### 12.7 Lifecycle invariant

> A renderer must not emit a profile whose `lifecycle_state` is
> `DRAFT`, `PROPOSED`, `DEPRECATED`-for-new-bindings, or `RETIRED`.
> Validator rule `RENDER-PROFILE-LIFECYCLE` enforces this.

### 12.8 Automation invariant

> A MANUAL step's output is never produced by an automatic code path. The
> binding policy's automation map is checked by every solver; outputs are
> tagged with the actual level used; mismatch raises
> `VAL-AUTOMATION-LEVEL-VIOLATION`.

### 12.9 Backwards-compatibility invariant

> The legacy `/api/v1/convert`, `/api/v1/parse`, `/api/v1/render`
> endpoints keep working with the same response shape. They route through
> the legacy compatibility shim described in §6.5. Removal is a separate,
> later milestone.

---

## 13. Roadmap (phased, no code yet)

Phasing is illustrative — Diego will sequence. Each phase produces
working software, with green tests, before the next phase begins.

### Phase 0 — Architecture (this document)

Deliverables:
- `docs/DEPLOYMENT_TARGET_ARCHITECTURE.md` (this doc)
- `docs/HUAWEI_MA5800_DEPLOYMENT_SPEC.md`
- Review & sign-off from Diego

### Phase 1 — Topology foundation

- `models/deployment/topology.py`: `DeploymentTarget`, `Chassis`, `Slot`,
  `Board`, `PhysicalPort`, `LogicalPort`, `UplinkGroup`, `PONGroup`,
  `NumberingRules`, `DeploymentConstraint`, enums.
- `models/deployment/capability.py`: `VendorCapabilityPack`,
  `FirmwareCapabilityPack`, loader from `vendor_capabilities/<v>/<m>.yaml`.
- Seed YAML: `huawei/ma5800-x7.yaml` (boards, slot kinds, numbering,
  id_ranges).
- `services/deployment/target_store.py`: in-memory + filesystem backed.
- API: target endpoints (`GET/POST/PATCH/DELETE /targets`).
- Validator rules: TOPO-* family.
- Tests: golden-file YAML loading, capability pack diff tests.

### Phase 2 — Topology ingestion (Huawei MA5800 only)

- `parsers/ingest/huawei/ma5800/board_parser.py`,
  `interface_parser.py`, `service_port_parser.py`,
  `ont_lineprofile_parser.py`, `ont_srvprofile_parser.py`,
  `dba_traffic_parser.py`.
- `services/deployment/topology_ingestion.py`: orchestrates per-command
  parsers, builds `IngestionResult`.
- API: `POST /targets/import`.
- Tests: real-world show-dumps committed to `examples/ingest/huawei/`.

### Phase 3 — Catalogue foundation

- `models/deployment/catalogue.py`: profile classes + lifecycle.
- `services/deployment/catalogue_store.py`.
- `services/deployment/promotion.py`: L1 → L3 promoter (renamed from
  current `services/promotion.py` to keep its current responsibility
  separate from this new one — see §14.2).
- `services/deployment/synthesis_deployment.py`: per-target synthesis.
- API: catalogue endpoints.
- Validator rules: CAT-* family.
- Tests: round-trip promote → catalogue → render-back-to-source.

### Phase 4 — Binding resolver

- `models/deployment/plan.py`: plan classes.
- `services/deployment/resolver.py`: walk the graph, emit plan.
- `services/deployment/id_allocator.py`.
- `services/deployment/binding_policy.py`.
- API: binding endpoints.
- Validator rules: BIND-* family.
- Tests: matrix of (source-vendor, target=MA5800-X7) → plan, golden files.

### Phase 5 — Renderer evolution (MA5800-X7 only)

- Refactor `renderers/huawei/ma5800/renderer.py` to consume
  `PhysicalBindingPlan + DeploymentTarget`.
- Refactor each `templates/huawei/ma5800/*.j2` to consume slice
  projections.
- Provenance threading from binding → line.
- Validator rules: RENDER-* family.
- Tests: deployability checks against canned MA5800 acceptance configs.

### Phase 6 — Frontend cockpit

- Sequence: `Targets` surface → `Catalogues` surface → `Binding` surface
  → `Render & Validate` surface upgrade.
- New components per §7.3.
- Reuse existing `EntityInspector`/`ValidationPanel` for the new entity
  types — they are schema-driven; only the schema mappings change.

### Phase 7 — ZTE C600 hardware-aware

- New `vendor_capabilities/zte/c600.yaml`, ingestion parsers, renderer
  refactor.
- Validator rules: ZTE-specific.
- Resolves the legacy `SERVICE_PORT_ID_DUPLICATED` 1198 errors as a
  by-product (the id allocator never produces collisions).

### Phase 8 — Fiberhome AN5516 hardware-aware
### Phase 9 — Datacom DM4615 hardware-aware
### Phase 10 — Diff-against-real-OLT, multi-operator locking, persistent stores

---

## 14. Migration & Coexistence

### 14.1 Coexistence with the frozen Semantic Runtime

L1 stays frozen. We add L2..L6 alongside. The L1 API (existing
`SessionRuntime`, existing endpoints) keeps working. The new
`DeploymentSession` *wraps* a `SessionRuntime` (composition, not
inheritance).

### 14.2 Renaming existing services

The current `services/promotion.py` promotes L1 `extra_vendor` into L1
formal models (subscriber edge, eth ports, etc.). That is "L1 internal
promotion". The new "L1 → L3 promoter" is conceptually different. To
avoid name collision:

| Current name | New name | Note |
|---|---|---|
| `services/promotion.py` | unchanged | Stays at L1, unchanged. |
| (new) | `services/deployment/profile_adoption.py` | "Adopt" a semantic profile into the catalogue as a PROPOSED `DeploymentXProfile`. |

The term **adopt** instead of **promote** keeps both pipelines legible.

### 14.3 `mapping_data.yaml` evolution

The existing YAML is treated as the seed of `InterfaceMappingPolicy.
explicit_overrides`. Pattern rules supplement it. The file is moved to
`vendor_capabilities/_pairs/<src>__<dst>/interface_mapping.yaml` and
versioned per capability pack. Backwards-compatible loader for one
release cycle.

### 14.4 Capability packs as data

`vendor_capabilities/huawei/ma5800-x7.yaml` ships with the repo. The
operator can override any field at runtime per session by editing the
target descriptor. No Python file needs editing to support a new
patch level — only YAML.

---

## 15. Open questions (tracked for Diego's review)

| # | Question | Default proposal | Decide before |
|---|---|---|---|
| Q1 | Persistence backend for targets/catalogues — filesystem or SQLite from day one? | Filesystem, JSON files under `./targets/` and `./catalogues/`. Migration path to SQLite stays open. | Phase 1 |
| Q2 | Capability pack versioning — semver per pack, or git-only? | Semver per pack written into the YAML; loader rejects packs newer than the engine knows. | Phase 1 |
| Q3 | Per-operator scope of catalogues — global or per-session? | Global library + per-session overlays. Editing a global profile is gated; editing the overlay is not. | Phase 3 |
| Q4 | `IdAllocator` exhaustion behaviour — error or auto-recycle deprecated ids? | Error first; auto-recycle is a separate strategy that the operator opts into. | Phase 4 |
| Q5 | Live ingestion (SSH to OLT) — in scope? | Out of scope for v2. Operator pastes show dumps. SSH is a v3 candidate. | Phase 2 |
| Q6 | Profile diff between source-semantic and target-catalogue — visual diff or evidence list? | Evidence list first (cheaper). Visual diff once the editor schema settles. | Phase 3 |
| Q7 | What happens to L9 (subscriber edge) under the deployment layer? | L9 stays L1-resident; binding to physical EthernetPort uses existing `port_id`. No new layer for L9 needed. | Phase 4 |
| Q8 | Pre-existing `SERVICE_PORT_ID_DUPLICATED` 1198 errors — block phase 7? | No. They are an L1 artefact of source. The id allocator at L4 emits a clean numbering for the target; the L1 errors stay as L1 warnings. | Phase 7 |
| Q9 | Multi-source merging (one deployment session consuming N source configs) | Out of scope for Phase 1..6. Architecture supports it (semantic_session_ref → list) but UI does not. | Phase 10 |
| Q10 | Render-time secret materialisation (PPPoE creds, SNMP communities) — emit placeholders or vault-refs? | Placeholders with `{{SECRET:NAME}}` tokens. Vault integration is later. | Phase 5 |

---

## 16. Adherence checklist (self-review against Diego's brief)

This document was checked against the original brief item by item. The
table below records each requirement and where it is addressed.

| Brief item | Addressed in |
|---|---|
| A. Domain Models — TargetOLT | §3.1 `DeploymentTarget` |
| A. Slot | §3.1 `Slot` |
| A. Board | §3.1 `Board` |
| A. PhysicalPort | §3.1 `PhysicalPort` |
| A. LogicalPort | §3.1 `LogicalPort` |
| A. PONGroup | §3.1 `PONGroup` (declared; detail in MA5800 spec) |
| A. UplinkGroup | §3.1 `UplinkGroup` (idem) |
| A. DeploymentConstraint | §3.1 `DeploymentConstraint` |
| A. ProvisioningProfile | §3.2 `DeploymentXProfile` family |
| A. ServiceIntent | §3.6 `ServiceIntent` |
| B. Mapping Graph — semantic ↔ deployment ↔ physical | §4 entirely |
| C. Automation Levels — auto / assisted / manual | §5 entirely |
| D. Renderer Evolution — semantic → deployment-aware | §6 entirely |
| E. Frontend Evolution — converter UI → engineering cockpit | §7 entirely |
| F. Operational Validation — deployability / hardware / slot / profile / interface / uplink / ONU placement | §8 entirely |
| Lifecycle of profiles | §9 entirely |
| Reusable deployment templates | §3.6 + §10.4 (`target_store` persistence) |
| Hardware import pipeline | §10 entirely |
| Topology ingestion | §10 entirely |
| Physical interface mapping | §4.5 `InterfaceMappingPolicy` + §3.1 `NumberingRules` |
| Deployment session model | §11 entirely |
| Avoid vendor exception spaghetti | P4 + §1.3 + §3.6 capability packs |
| Avoid profile spaghetti | §3.2 separate `DeploymentXProfile` classes + §9 lifecycle |
| Avoid interface spaghetti | §4.5 `InterfaceMappingPolicy` |
| Renderer not coupled to hardware | P2 + §6 entirely + §12.4 import-graph invariant |
| First target: Huawei MA5800 | §13 Phase 1..6 + companion `HUAWEI_MA5800_DEPLOYMENT_SPEC.md` |

If any brief item is missing from the table above, this document is
incomplete and must be amended before implementation.

---

## 17. Glossary

| Term | Meaning |
|---|---|
| Semantic | Vendor-neutral *meaning* of the config; L1. |
| Deployment Topology | Physical inventory of a target OLT; L2. |
| Provisioning Catalogue | Library of deployable profiles for a target; L3. |
| Physical Binding Plan | The fully resolved who-goes-where document; L4. |
| Deployment-aware Render | A render driven by a plan, not by raw semantic data; L5. |
| Operational Validation | Invariant checking across L1..L5; L6. |
| Adopt | Action by which an L1 profile becomes an L3 `DeploymentXProfile`-PROPOSED. |
| Resolve | Action by which the resolver turns unresolved bindings into bindings. |
| Capability pack | YAML data describing a vendor/model/firmware's allowed hardware and numbering rules. |
| Numbering rules | The shape of every interface/id namespace on a target. |
| Lifecycle | The state machine each catalogue profile traverses. |
| Provenance | Auditable origin metadata on every entity. |
| Automation level | AUTO/ASSISTED/MANUAL classification of any decision. |
| Binding policy | Operator-settable preferences for the resolver. |

---

## 18. Out of scope for this document

- Specific CLI examples (lives in companion `HUAWEI_MA5800_DEPLOYMENT_SPEC.md`).
- API request/response JSON schemas (will be drafted in the corresponding
  phase doc, e.g. `docs/PHASE1_TOPOLOGY_API.md`).
- Frontend component prop tables (will be drafted in the corresponding
  phase doc).
- Database schema (Q1 keeps this open).
- Authentication / multi-operator (acknowledged in §11.0 placeholders).

---

*End of architectural blueprint. Companion document:
`docs/HUAWEI_MA5800_DEPLOYMENT_SPEC.md`.*
