# Frontend Phase 1 — Semantic Telecom Engineering Workspace

**Estado:** Phase 1 entregue, buildando limpo (`vite build` → 165 modules, 0 errors, 298 kB gz 96 kB).

## Arquitetura

Backend e cliente trocam **patches** e **projections** — o OLTConfig nunca sai
do servidor. Frontend mantém apenas view-state (selection, expanded tree,
filtros, target preview).

```
[ Backend SessionRuntime ]                 [ Frontend (Zustand) ]
  ├─ canonical OLTConfig                     ├─ sessionId
  ├─ semantic indexes                        ├─ selection
  ├─ provenance graph                        ├─ expanded groups/pons
  ├─ validation cache  ←─ POST /sessions  ←──┤ filter, filterSource
  ├─ render cache      ←─ PATCH /entity   ←──┤ targetVendor
  ├─ audit log         ←─ GET /projection ───→ tree (lightweight)
  ├─ undo/redo stack   ←─ GET /entity     ───→ data + bindings + issues
  └─ snapshots         ←─ GET /render/v   ───→ rendered CLI
```

## Endpoints novos no backend

```
POST    /api/v1/sessions                          create
GET     /api/v1/sessions                          list
GET     /api/v1/sessions/{id}/projection          tree projection (lightweight)
GET     /api/v1/sessions/{id}/entity/{t}/{id}     entity + bindings + issues
PATCH   /api/v1/sessions/{id}/entity              apply patch (op=update)
GET     /api/v1/sessions/{id}/render/{vendor}     rendered CLI (cached)
GET     /api/v1/sessions/{id}/validation          validation report
GET     /api/v1/sessions/{id}/audit               audit log
POST    /api/v1/sessions/{id}/undo|redo
POST    /api/v1/sessions/{id}/snapshot
GET     /api/v1/sessions/{id}/snapshots
POST    /api/v1/sessions/{id}/restore/{snap}
DELETE  /api/v1/sessions/{id}
```

Cada PATCH:
- valida via Pydantic `validate_assignment`
- tagueia `provenance.source = MANUAL`
- snapshot para undo
- invalida caches (render + validation)
- registra audit entry
- retorna validation_summary + impacted_entity_ids

## Componentes Phase 1

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| StatusBar | `components/StatusBar.jsx` | engine status, session id, vendor, hostname, ONUs, e/w counts, dirty count |
| OnboardingSurface | `components/OnboardingSurface.jsx` | dropzone + paste + recent sessions + vendors + engine |
| Workspace | `components/Workspace.jsx` | grid 12-col: Explorer (3) | Inspector+Validation (5) | CliPreview (4) |
| RuntimeExplorer | `components/RuntimeExplorer.jsx` | árvore virtualizada (@tanstack/react-virtual). Provenance badges (P/I/S/L9/M/D). Filtros: search, source, needs_review |
| EntityInspector | `components/EntityInspector.jsx` | campos editáveis por tipo, cross-bindings, provenance panel, validation issues, undo/redo |
| ValidationPanel | `components/ValidationPanel.jsx` | warnings/errors agrupados, colapsável, severity filter, click-to-navigate |
| CliPreview | `components/CliPreview.jsx` | Monaco editor + DiffEditor toggle, vendor selector, cache indicator |

## Stack utilizada

```
React 18 · Vite 5 · Tailwind 3 · Monaco 0.52 · Zustand 4.5 ·
@tanstack/react-query 5 · @tanstack/react-virtual 3 · clsx 2 · immer 10
```

## Como rodar

```
# backend
cd olt-converter/backend
uvicorn app.main:app --reload --port 8000

# frontend
cd olt-converter/frontend
npm run dev   # http://localhost:5173
```

Variável de ambiente opcional no frontend:
```
VITE_API_BASE=http://localhost:8000/api/v1
```

## Smoke test (end-to-end já validado)

```
POST /sessions com MARIANA-X7.txt
  → 200, session_id=bd1e70abe2d1, vendor=huawei, 1811 ONUs
GET projection
  → tree: [(vlans,20), (pons,5), (service_ports,2580), (uplinks,4), (profiles,46)]
GET entity/ONU/gpon 0/1:0
  → fields + bindings={service_ports, wan_bindings, ssids, bridge_groups, port_routes}
PATCH entity description = "EDIT_API_OK"
  → ok, audit_size=1
GET render/fiberhome
  → 167.794 chars
POST undo
  → ok, restored
```

## Próximas fases (NÃO incluídas neste sprint)

5. Diff View entre snapshots/sessões
6. Batch Operations (multi-select + apply same patch)
7. Command palette (⌘K)
8. Audit log viewer integrado
9. Snapshot manager UI
10. Provenance graph visual (read-only, focado em densidade)
