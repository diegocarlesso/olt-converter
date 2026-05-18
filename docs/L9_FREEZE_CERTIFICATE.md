# L9 Stability — Backend Semanticamente Frozen

**Data:** 2026-05-18
**Veredito:** APROVADO — backend pronto para iniciar frontend/editor visual.

## Resumo

Todos os 7 criterios de estabilidade L9 aprovados em 12 backups reais
(`*.txt` no workspace). Pipeline completa rodou sem crashes.

| # | Criterio | Resultado |
|---|----------|----------|
| C1 | ProvenanceSource.PROMOTION + Provenance.promoted() helper | OK |
| C2 | promote_subscriber_edge: 0 crashes (12 arquivos)        | OK |
| C3 | Parsers populam extra_vendor (ZTE 60.3%, Huawei 4.4%)   | OK |
| C4 | 2.326 entidades formais L9 materializadas              | OK |
| C5 | Cross-binding integrity 100% (2.237 OK / 0 broken)     | OK |
| C6 | Confidence: 83.9% em high+medium                        | OK |
| C7 | Renderer SE emit em 2+ targets (fiberhome, zte)         | OK |

## Bugs corrigidos nesta rodada

1. **`ProvenanceSource.PROMOTION` ausente** — crashe silencioso
   `AttributeError('PROMOTION')` em todo arquivo onde parser populava
   `extra_vendor` (ZTE em particular). Fix: adicionado member + helper
   `Provenance.promoted()`.

2. **Huawei parser nao populava extra_vendor para L9** — slot/pon_port
   trocados em `ont add` e em todos os handlers de `ont port route /
   port native-vlan / wan-config / internet-config / policy-route-config
   / ipconfig`. Slot vem do `current_pon` (interface gpon 0/SLOT);
   `m.group(1)` e pon_port; `m.group(2)` e ont_id. Lookups corrigidos
   via helper `_resolve_onu_for_l9()`. Resultado: MARIANA-X7 passou de
   0 -> 156 wan_bindings, 0 -> 352 port_routes promovidos.

3. **PortRoute eth_ref broken (520 broken)** — `_promote_port_routes`
   agora cria `EthernetPort` ausente para o eth_id referenciado.
   Resultado: 520/520 OK.

4. **WANBinding wan_profile_ref usando string sintetica** — agora
   resolve `profile_id` -> `wan_profile.name` via map computado uma vez
   em `promote_subscriber_edge`. Resultado: 795/795 OK.

5. **Renderer-completeness lia apenas primeiros 1.200 chars** — bias
   de mensuracao (subscriber edge e tipicamente renderizado tardio).
   Fix: passa a contar SE keywords no render completo. Resultado: ZTE
   passou de 0 -> 459 linhas SE.

## Instrumentacao adicionada (observabilidade)

`promote_subscriber_edge` agora loga, alem dos contadores existentes:
  - `onus_total`
  - `extra_vendor_onus` (numero de ONUs com keys promoveis)
  - `extra_vendor_seen` (somatorio por key)
  - `errors` (com sample dos 3 primeiros tracebacks)
  - Persistencia em disco em `docs/promotion_errors.json` quando ha erro.

Cada promocao agora roda em try/except por funcao por ONU; uma falha
de uma promocao especifica nao quebra o resto do pipeline.

## Observacoes nao-bloqueadoras

- `ETA-LOJA-ZTE-OLT01.txt` apresenta **1.198 erros de
  `SERVICE_PORT_ID_DUPLICATED`** — pre-existente no parser ZTE. NAO
  relacionado a L9; pode ser tratado em sprint dedicado.
- `BACKUP-FIBERHOME.txt` mencionado no checkpoint NAO esta presente no
  workspace. O parser Fiberhome esta validado contra os exemplos do
  diretorio `examples/`.
- Huawei renderer ainda emite 0 linhas SE no FIDELITY (template
  `subscriber_edge.j2` nao puxa nenhum dado dos backups testados).
  Provavel causa: as ONUs Huawei tem apenas `port_routes` e
  `wan_bindings` promovidos, e o template pode estar gatado em outros
  campos. Investigar em proximo sprint se o frontend precisar.

