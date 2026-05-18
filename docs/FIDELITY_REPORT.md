# Fidelity Report — pipeline real

> Gerado por `fidelity_report.py`. Reflete o estado *real* da
> pipeline (parse → inferência → síntese → equivalência → remap → render)
> contra os backups disponíveis. Use para calibrar a matriz de
> compatibilidade declarativa.

## 0. Sprint coverage milestones

Targets do **Parser Coverage Recovery Sprint** vs realidade medida.

| Vendor | Target | Actual | Δ | Status |
|--------|-------:|-------:|--:|:------:|
| **datacom** | 70% | 80.0% | +10.0% | ✅ |
| **fiberhome** | 75% | 100.0% | +25.0% | ✅ |
| **huawei** | 90% | 94.1% | +4.1% | ✅ |
| **zte** | 75% | 84.7% | +9.7% | ✅ |

## 1. Sumário por arquivo

| Arquivo | Vendor | Linhas | Cobertura | ONUs | SPs | Inferência | Issues | Remaps |
|--------|--------|-------:|----------:|-----:|----:|----------:|-------:|-------:|
| datacom_dm4615_basic.cfg | datacom | 30 | 80.0% | 1 | 0 | 0.0% | 0e/0w | varia |
| fiberhome_an5516_basic.cfg | fiberhome | 38 | 100.0% | 3 | 0 | 0.0% | 0e/0w | varia |
| huawei_ma5800_basic.cfg | huawei | 44 | 97.7% | 2 | 4 | 100.0% | 0e/4w | varia |
| zte_c600_basic.cfg | zte | 45 | 100.0% | 2 | 2 | 0.0% | 0e/4w | varia |
| ETA-LOJA-ZTE-OLT01.txt | zte | 27647 | 85.8% | 1092 | 1202 | 0.0% | 1198e/5759w | varia |
| MG-GVS-OLT-BRAIPE.txt | huawei | 1780 | 94.2% | 565 | 984 | 74.0% | 0e/1132w | varia |
| MG-GVS-OLT-MARIANA-X7.txt | huawei | 8498 | 97.3% | 1811 | 2580 | 41.9% | 0e/3645w | varia |
| OLT HUAWEI PROFILES .txt | huawei | 2002 | 100.0% | 0 | 0 | 0.0% | 0e/1w | varia |
| OLT SERVICOS.txt | huawei | 1097 | 59.3% | 0 | 0 | 0.0% | 0e/1w | varia |
| OLT-NOVA-BRAIPE.txt | huawei | 2040 | 94.1% | 608 | 1044 | 70.9% | 0e/1226w | varia |
| OLT-ZTE-CRISTAL.txt | zte | 3296 | 83.3% | 167 | 167 | 0.0% | 166e/334w | varia |
| OLT-ZTE-ITABAIANA.txt | zte | 338 | 45.6% | 0 | 0 | 0.0% | 0e/0w | varia |
| OLT-ZTE-MUCURICI.txt | zte | 382 | 48.7% | 0 | 0 | 0.0% | 0e/0w | varia |
| PROVISIONAR_ONU.txt | zte | 14 | 85.7% | 1 | 0 | 0.0% | 0e/1w | varia |
| SCRIPT-GER-OLT.txt | huawei | 63 | 49.2% | 0 | 0 | 0.0% | 0e/0w | varia |
| Script_OLT_Huawei.txt | huawei | 578 | 96.4% | 0 | 0 | 0.0% | 0e/1w | varia |

## 1b. Parser coverage heatmap por vendor

Média ponderada pelo número de linhas (não pela contagem de arquivos).

| Vendor | Files | Total lines | Avg coverage |
|--------|------:|------------:|-------------:|
| 🟢 **datacom** | 1 | 30 | 80.0% |
| 🟢 **fiberhome** | 1 | 38 | 100.0% |
| 🟢 **huawei** | 8 | 16,102 | 94.1% |
| 🟢 **zte** | 6 | 31,722 | 84.7% |

## 1c. Runtime vs declarative unparsed

Classificação das linhas não-mapeadas. Comandos *runtime* (per-ONU: gemport, tcont, set wancfg, sn-bind, etc.) são geralmente per-cliente; *declarative* são globais.

| Categoria | Linhas | % |
|-----------|-------:|--:|
| Runtime    | 530 | 9.1% |
| Declarative | 5,284 | 90.9% |

## 1d. Unsupported clusters (top prefixos)

Agrupamento por prefixo de comando — mostra qual *família* de comandos tem maior impacto.

| # | Ocorrências | Cluster |
|--:|------------:|---------|
| 1 | 375 | `interface` |
| 2 | 241 | `r069` |
| 3 | 184 | `snmp-server` |
| 4 | 178 | `ssid` |
| 5 | 169 | `gem` |
| 6 | 144 | `vlan` |
| 7 | 141 | `<N>` |
| 8 | 136 | `onu-type-if` |
| 9 | 119 | `pppoe` |
| 10 | 99 | `no` |
| 11 | 82 | `ont` |
| 12 | 80 | `tcont` |
| 13 | 68 | `onu-type` |
| 14 | 55 | `ssh` |
| 15 | 48 | `ont-srvprofile` |
| 16 | 48 | `ont-port` |
| 17 | 48 | `ont-lineprofile` |
| 18 | 45 | `description` |
| 19 | 43 | `switchport` |
| 20 | 42 | `ip` |

## 1e. Semantic loss buckets (cross-conversion)

| Categoria | Total |
|-----------|------:|
| Render errors        | 4,092 |
| Render warnings      | 26,303 |
| Remap collisions     | 0 |
| Remaps applied (ok)  | 1,239 |

## 2. Top unsupported commands (normalizados, agregados)

Patterns que aparecem em `raw_unparsed` após normalização (números e paths viram `<N>`/`<PATH>`).
Bom indicador de features a priorizar nos parsers.

| # | Ocorrências | Pattern |
|--:|------------:|---------|
| 1 | 334 | `interface vport-<PATH>.<N>:<N>` |
| 2 | 241 | `r069` |
| 3 | 140 | `<N>` |
| 4 | 87 | `no shutdown` |
| 5 | 80 | `tcont <N> dba-profile-id <N>` |
| 6 | 80 | `gem add <N> eth tcont <N>` |
| 7 | 80 | `gem mapping <N> <N> vlan <N>` |
| 8 | 51 | `vlan port eth_0/<N> mode hybrid` |
| 9 | 32 | `linktrap disable` |
| 10 | 32 | `name gpon-olt_1/<PATH>` |
| 11 | 32 | `dba-profile add profile-name <STR> type3 assure <N> max <N>` |
| 12 | 32 | `ont-port pots adaptive <N> eth adaptive <N> catv adaptive <N>` |
| 13 | 32 | `discover-period new-onu <N> miss-onu <N>` |
| 14 | 31 | `14ab.02af.b03e <N> Dynamic xgei_1/<PATH>` |
| 15 | 31 | `description gpon-olt_1/<PATH>` |
| 16 | 24 | `vlan port eth_0/<N> vlan <N>,<N>` |
| 17 | 24 | `speed <N> <N>` |
| 18 | 21 | `ring check enable` |
| 19 | 18 | `ip address <N>.<N>.<N>.<N> <N>.<N>.<N>.<N>` |
| 20 | 18 | `switchport mode trunk` |
| 21 | 18 | `accept on` |
| 22 | 17 | `mgmt-ip <N>.<N>.<N>.<N> <N>.<N>.<N>.<N> vlan <N> priority <N> route <N>.<N>.<N>.<N> <N>.<N>.<N>.<N>` |
| 23 | 17 | `<N>.<N>.<N>.<N> host <N>` |
| 24 | 17 | `ont ipconfig <N> <N> pppoe vlan <N> priority <N> user-account username <STR> password <STR>` |
| 25 | 16 | `onu-type-if ZTE-F660 eth_0/<N>` |
| 26 | 16 | `auto-neg <N> disable` |
| 27 | 16 | `port <N> fec enable` |
| 28 | 16 | `ont port vlan <N> <N> eth <N> translation <N> user-vlan <N>` |
| 29 | 16 | `ont-port eth <N>` |
| 30 | 14 | `onu-type-if ZTE-F660 wifi_0/<N>` |

## 3. Entidades que precisam de revisão (needs_review=True)

Contagem por coleção. `needs_review` é setado quando algo foi
inferido com baixa confiança, sintetizado, default-fallback ou remapeado.

| Coleção | needs_review |
|---------|-------------:|
| `traffic_profiles` | 59 |
| `dba_profiles` | 17 |

## 4. Bindings inferidos (cobertura por confidence)

Cobertura média da inferência de service-ports: **17.9%** das ONUs receberam binding.

Distribuição global por bucket de confidence:

| Bucket | Bindings |
|--------|---------:|
| medium | 2 |
| high | 1607 |

### Exemplos representativos (origem do binding rastreável)

- **huawei_ma5800_basic.cfg** · ONU gpon 0/1:0 → VLAN 100 · conf=**0.85**
  - reason: _service-profile Generic_1_V100 traduz para VLAN 100_
  - signals: `service-profile Generic_1_V100 eth1 translation=100 user_vlan=100`
- **huawei_ma5800_basic.cfg** · ONU gpon 0/1:1 → VLAN 100 · conf=**0.85**
  - reason: _service-profile Generic_1_V100 traduz para VLAN 100_
  - signals: `service-profile Generic_1_V100 eth1 translation=100 user_vlan=100`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/1:0 → VLAN 201 · conf=**1.0**
  - reason: _VLAN 201 mapeada para GEM 1 no line-profile Generic_1_V201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `line-profile Generic_1_V201 mapper gem 1 → vlan 201, service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/1:1 → VLAN 201 · conf=**1.0**
  - reason: _VLAN 201 mapeada para GEM 1 no line-profile Generic_1_V201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `line-profile Generic_1_V201 mapper gem 1 → vlan 201, service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/1:2 → VLAN 201 · conf=**1.0**
  - reason: _VLAN 201 mapeada para GEM 1 no line-profile Generic_1_V201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `line-profile Generic_1_V201 mapper gem 1 → vlan 201, service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/1:3 → VLAN 201 · conf=**1.0**
  - reason: _VLAN 201 mapeada para GEM 1 no line-profile Generic_1_V201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `line-profile Generic_1_V201 mapper gem 1 → vlan 201, service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **MG-GVS-OLT-MARIANA-X7.txt** · ONU gpon 0/1:0 → VLAN 205 · conf=**1.0**
  - reason: _VLAN 205 mapeada para GEM 1 no line-profile Generic_1_V205 | service-profile Generic_1_V205 traduz para VLAN 205 | service-profile Generic_1_V205 traduz para VLAN 205 | service-profile Generic_1_V205 traduz para VLAN 205 | service-profile Generic_1_V205 traduz para VLAN 205_
  - signals: `line-profile Generic_1_V205 mapper gem 1 → vlan 205, service-profile Generic_1_V205 eth1 translation=205 user_vlan=205, service-profile Generic_1_V205 eth2 translation=205 user_vlan=205, service-profile Generic_1_V205 eth3 translation=205 user_vlan=205, service-profile Generic_1_V205 eth4 translation=205 user_vlan=205`
- **MG-GVS-OLT-MARIANA-X7.txt** · ONU gpon 0/1:1 → VLAN 205 · conf=**1.0**
  - reason: _VLAN 205 mapeada para GEM 1 no line-profile Generic_1_V205 | service-profile Generic_1_V205 traduz para VLAN 205 | service-profile Generic_1_V205 traduz para VLAN 205 | service-profile Generic_1_V205 traduz para VLAN 205 | service-profile Generic_1_V205 traduz para VLAN 205_
  - signals: `line-profile Generic_1_V205 mapper gem 1 → vlan 205, service-profile Generic_1_V205 eth1 translation=205 user_vlan=205, service-profile Generic_1_V205 eth2 translation=205 user_vlan=205, service-profile Generic_1_V205 eth3 translation=205 user_vlan=205, service-profile Generic_1_V205 eth4 translation=205 user_vlan=205`

## 5. Per-feature confidence histogram (matriz)

Para cada feature, distribuição de `semantic_fidelity` em pares vendor×vendor.

| Feature | ≥0.9 | 0.7-0.9 | 0.5-0.7 | 0.3-0.5 | <0.3 |
|---------|-----:|--------:|--------:|--------:|-----:|
| `hostname` | 12 | 0 | 0 | 0 | 0 |
| `vlan` | 12 | 0 | 0 | 0 | 0 |
| `service_vlan` | 0 | 0 | 0 | 6 | 6 |
| `vlan_translation` | 0 | 6 | 6 | 0 | 0 |
| `qinq` | 0 | 0 | 2 | 10 | 0 |
| `uplink` | 12 | 0 | 0 | 0 | 0 |
| `uplink_lacp` | 0 | 0 | 5 | 7 | 0 |
| `static_route` | 0 | 6 | 6 | 0 | 0 |
| `mgmt_vlan_ip` | 6 | 6 | 0 | 0 | 0 |
| `boards` | 0 | 2 | 8 | 0 | 2 |
| `pon` | 9 | 3 | 0 | 0 | 0 |
| `onu_auth` | 12 | 0 | 0 | 0 | 0 |
| `onu_admin_state` | 0 | 4 | 8 | 0 | 0 |
| `onu_eth_ports` | 0 | 5 | 6 | 1 | 0 |
| `onu_native_vlan` | 0 | 6 | 6 | 0 | 0 |
| `onu_user_vlan` | 0 | 5 | 5 | 2 | 0 |
| `gem_tcont` | 0 | 7 | 5 | 0 | 0 |
| `dba_profile` | 2 | 7 | 3 | 0 | 0 |
| `traffic_profile` | 0 | 5 | 5 | 2 | 0 |
| `line_profile` | 0 | 7 | 5 | 0 | 0 |
| `service_profile` | 0 | 12 | 0 | 0 | 0 |
| `service_port` | 2 | 6 | 3 | 1 | 0 |
| `multicast_igmp` | 0 | 0 | 0 | 0 | 12 |
| `multicast_gem` | 0 | 0 | 0 | 0 | 12 |
| `wan_profile` | 0 | 0 | 0 | 6 | 6 |
| `pppoe_session` | 0 | 0 | 0 | 0 | 12 |
| `ipoe_session` | 0 | 0 | 0 | 0 | 12 |
| `policy_route` | 0 | 0 | 0 | 6 | 6 |
| `snmp` | 0 | 0 | 6 | 6 | 0 |
| `ssh_cipher_detail` | 0 | 0 | 0 | 12 | 0 |
| `aaa_radius` | 0 | 4 | 4 | 4 | 0 |
| `users` | 0 | 1 | 4 | 7 | 0 |
| `qos_attachment` | 0 | 0 | 3 | 9 | 0 |
| `omci_provisioning` | 4 | 8 | 0 | 0 | 0 |
| `stb_ports` | 0 | 0 | 0 | 0 | 12 |
| `ssid_binding` | 0 | 0 | 0 | 0 | 12 |
| `subscriber_edge_uni` | 0 | 11 | 1 | 0 | 0 |
| `subscriber_edge_wifi` | 0 | 2 | 7 | 3 | 0 |
| `subscriber_edge_bridge_group` | 0 | 0 | 9 | 3 | 0 |
| `subscriber_edge_wan_binding` | 0 | 3 | 9 | 0 | 0 |
| `subscriber_edge_lan_service` | 0 | 1 | 11 | 0 | 0 |
| `subscriber_edge_stb` | 0 | 0 | 0 | 0 | 12 |
| `subscriber_edge_multicast` | 0 | 0 | 0 | 0 | 12 |
| `subscriber_edge_port_route` | 0 | 0 | 0 | 6 | 6 |

## 6. Heatmap origem → destino (conversões reais)

Soma das métricas dos arquivos analisados. Cores: 🟢 OK · 🟡 atenção · 🔴 problema.

| origem ↓ destino → | **fiberhome** | **huawei** | **zte** | **datacom** |
|---|---|---|---|---|
| **fiberhome** | — | 🟢 1f · 0e · 0w · 2r | 🟢 1f · 0e · 0w · 2r | 🟢 1f · 0e · 0w · 2r |
| **huawei** | 🟡 8f · 0e · 6010w · 441r | — | 🟡 8f · 0e · 6010w · 321r | 🟡 8f · 0e · 6010w · 441r |
| **zte** | 🔴 6f · 1364e · 2767w · 1r | 🔴 6f · 1364e · 2739w · 28r | — | 🔴 6f · 1364e · 2767w · 1r |
| **datacom** | 🟢 1f · 0e · 0w · 0r | 🟢 1f · 0e · 0w · 0r | 🟢 1f · 0e · 0w · 0r | — |

Legenda: `f`=arquivos, `e`=errors, `w`=warnings, `r`=remaps aplicados

## 7. Scores globais derivados da matriz

| Vendor | parser_coverage | renderer_completeness |
|--------|---------------:|---------------------:|
| **fiberhome** | 40% | 44% |
| **huawei** | 60% | 57% |
| **zte** | 50% | 47% |
| **datacom** | 35% | 35% |

### semantic_fidelity por par

| | → **fiberhome** | → **huawei** | → **zte** | → **datacom** |
|---|---|---|---|---|
| **fiberhome** | — | 58% (8/22/14/0) | 55% (6/24/14/0) | 51% (5/26/13/0) |
| **huawei** | 60% (8/24/12/0) | — | 61% (9/23/12/0) | 57% (7/22/15/0) |
| **zte** | 57% (6/25/13/0) | 61% (10/20/14/0) | — | 54% (6/22/16/0) |
| **datacom** | 52% (5/26/13/0) | 56% (7/21/16/0) | 53% (6/22/16/0) | — |

Contadores entre parênteses: (FULL / PARTIAL / NONE / UNSUPPORTED)

## 7b. L9 Subscriber Edge — validation final

Cobertura: **22.2%** (942 de 4252 ONUs com entidades L9 promovidas/parseadas).

### Promoted entities (totais agregados)

| Tipo | Total |
|------|------:|
| `eth_ports` | 2,378 |
| `wan_bindings` | 795 |
| `bridge_groups` | 744 |
| `port_routes` | 520 |
| `ssids` | 178 |
| `radios` | 89 |
| `lan_services` | 0 |
| `multicast_bindings` | 0 |
| `stb_configured` | 0 |

### Foco: EthernetPort.native_vlan

- Total de EthernetPort: **2378**
- Com `native_vlan` populado: **157** (`6.6%`)

### Provenance distribution (subscriber edge)

| Categoria | Count |
|-----------|------:|
| `wan_bindings:promotion` | 795 |
| `bridge_groups:promotion` | 744 |
| `port_routes:promotion` | 520 |
| `ssids:promotion` | 178 |
| `radios:synthesis` | 89 |

### Promoted vs Parsed/Inference ratio

- Promoted (extra_vendor → modelo): **2,237** (96.2%)
- Parsed/inferred direto: **89** (3.8%)

### Confidence histogram

| Bucket | Count |
|--------|------:|
| high       | 568 |
| medium     | 1,384 |
| low        | 374 |
| very-low   | 0 |
| fallback   | 0 |

### Cross-binding integrity

**Score global: 100.0%**

| Check | OK | Broken |
|-------|---:|-------:|
| SSID ↔ Radio | 178 | 0 |
| WANBinding ↔ WANProfile | 795 | 0 |
| BridgeGroup members ⊂ eth_ports | 744 | 0 |
| LANService.vlan ∈ vlans | 0 | 0 |
| PortRoute eth refs | 520 | 0 |

### Renderer subscriber-edge completeness

Quantos arquivos por destino emitiram conteúdo subscriber-edge não-vazio.

| Destino | Arquivos com edge | Total | Linhas subscriber edge |
|---------|-----------------:|------:|----------------------:|
| fiberhome | 1 | 9 | 178 |
| huawei | 0 | 6 | 0 |
| zte | 3 | 6 | 459 |
| datacom | 0 | 9 | 0 |

## 8. Detalhe por arquivo


---

### datacom_dm4615_basic.cfg

- vendor: **datacom** (DM4615, conf=0.429)
- linhas: 30 · cobertura **80.0%** · unparsed=6
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                2
  service_vlans        0
  uplinks              1
  lacp_groups          0
  static_routes        0
  pons                 1
  onus                 1
  service_ports        0
  dba_profiles         2
  traffic_profiles     2
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1
  unparsed             6
```

**Needs review** (total 2):
- `traffic_profiles` `TT-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-1G' (bw=1024000 kbps)_
- `traffic_profiles` `TT-500M` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-500M' (bw=512000 kbps)_

**Cross conversions**
```
  → fiberhome len=   866 e=0 w=0 i=1 onus=1 sp=0 remap=0 col=0
  → huawei    len=  1093 e=0 w=0 i=1 onus=1 sp=0 remap=0 col=0
  → zte       len=   709 e=0 w=0 i=1 onus=1 sp=0 remap=0 col=0
```

**Amostra de linhas não-mapeadas:**
```
  dot1q
   description UPLINK
   no shutdown
  gpon
    onu 2 serial-number DACM22222222
     profile BRIDGE-100
```

**Subscriber edge (L9):**
```
  coverage     : 0.0% (0/1 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 0
  port_routes  : 0
  stb          : 0
  multicast    : 0
  eth_native_vlan: 0/0 (0.0%)
  integrity    : 100.0% OK
```

---

### fiberhome_an5516_basic.cfg

- vendor: **fiberhome** (AN5516, conf=1.0)
- linhas: 38 · cobertura **100.0%** · unparsed=0
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               4
  vlans                3
  service_vlans        2
  uplinks              2
  lacp_groups          0
  static_routes        1
  pons                 4
  onus                 3
  service_ports        0
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     2
  wan_profiles         0
  onu_type_profiles    2
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             3
  unparsed             0
```

**Needs review** (total 2):
- `dba_profiles` `DBA-SYNTH-IPTV` · synthesis conf=0.75
  - _Sintetizado a partir de: service_vlan 'IPTV'_
- `traffic_profiles` `TT-SYNTH-IPTV` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-SYNTH-IPTV' (bw=102400 kbps)_

**DBA sintetizados:**
- `DBA-SYNTH-IPTV` (type3, max=102400) conf=0.75 · synthesis

**Cross conversions**
```
  → huawei    len=  1839 e=0 w=0 i=0 onus=3 sp=0 remap=2 col=0
  → zte       len=  1601 e=0 w=0 i=0 onus=3 sp=0 remap=2 col=0
  → datacom   len=   794 e=0 w=0 i=0 onus=3 sp=0 remap=2 col=0
```

**Subscriber edge (L9):**
```
  coverage     : 0.0% (0/3 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 0
  port_routes  : 0
  stb          : 0
  multicast    : 0
  eth_native_vlan: 0/0 (0.0%)
  integrity    : 100.0% OK
```

---

### huawei_ma5800_basic.cfg

- vendor: **huawei** (MA5800, conf=0.75)
- linhas: 44 · cobertura **97.7%** · unparsed=1
- inferência: **100.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                3
  service_vlans        0
  uplinks              1
  lacp_groups          0
  static_routes        0
  pons                 1
  onus                 2
  service_ports        4
  dba_profiles         3
  traffic_profiles     4
  line_profiles        1
  service_profiles     1
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             0
  unparsed             1
```

**Needs review** (total 4):
- `dba_profiles` `DBA-SYNTH-1G` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile 'SMARTOLT-1G-UP'_
- `traffic_profiles` `TT-DADOS` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DADOS' (bw=1024000 kbps)_
- `traffic_profiles` `TT-VOZ` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-VOZ' (bw=512000 kbps)_
- `traffic_profiles` `TT-SYNTH-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-SYNTH-1G' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-SYNTH-1G` (type3, max=1024000) conf=0.75 · synthesis

**Cross conversions**
```
  → fiberhome len= 13524 e=0 w=4 i=0 onus=2 sp=4 remap=1 col=0
  → zte       len=  2458 e=0 w=4 i=0 onus=2 sp=4 remap=0 col=0
  → datacom   len=   613 e=0 w=4 i=0 onus=2 sp=4 remap=1 col=0
```

**Amostra de linhas não-mapeadas:**
```
   system modify logon password disable
```

**Subscriber edge (L9):**
```
  coverage     : 0.0% (0/2 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 0
  port_routes  : 0
  stb          : 0
  multicast    : 0
  eth_native_vlan: 0/0 (0.0%)
  integrity    : 100.0% OK
```

---

### zte_c600_basic.cfg

- vendor: **zte** (C600, conf=0.875)
- linhas: 45 · cobertura **100.0%** · unparsed=0
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                0
  service_vlans        0
  uplinks              2
  lacp_groups          0
  static_routes        0
  pons                 2
  onus                 2
  service_ports        2
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1
  unparsed             0
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len=   747 e=0 w=0 i=4 onus=2 sp=2 remap=0 col=0
  → huawei    len=  1176 e=0 w=0 i=4 onus=2 sp=2 remap=0 col=0
  → datacom   len=   573 e=0 w=0 i=4 onus=2 sp=2 remap=0 col=0
```

**Subscriber edge (L9):**
```
  coverage     : 0.0% (0/2 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 0
  port_routes  : 0
  stb          : 0
  multicast    : 0
  eth_native_vlan: 0/2 (0.0%)
  integrity    : 100.0% OK
```

---

### ETA-LOJA-ZTE-OLT01.txt

- vendor: **zte** (C600, conf=0.375)
- linhas: 27647 · cobertura **85.8%** · unparsed=3917
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                9
  service_vlans        0
  uplinks              0
  lacp_groups          0
  static_routes        0
  pons                 32
  onus                 1092
  service_ports        1202
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1093
  unparsed             3917
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len=111626 e=1198 w=2432 i=1 onus=1092 sp=1202 remap=0 col=0
  → huawei    len=217778 e=1198 w=2404 i=1 onus=1092 sp=1202 remap=28 col=0
  → datacom   len= 43837 e=1198 w=2432 i=1 onus=1092 sp=1202 remap=0 col=0
```

**Amostra de linhas não-mapeadas:**
```
  ETA-LOJA-ZTE-OLT01#show mac
  Total mac address : 2583
  Mac address      Vlan  Type      Port                     Vc
  -------------------------------------------------------------------------------
  18fd.7490.4be6   3999  Dynamic   gpon-onu_1/1/1:1         vport 1
  18fd.7490.4be6   5     Dynamic   gpon-onu_1/1/1:1         vport 2
  d836.5f82.eafb   5     Dynamic   gpon-onu_1/1/1:1         vport 2
  18fd.7490.4be6   6     Dynamic   gpon-onu_1/1/1:1         vport 3
  30e1.f14a.52b3   6     Dynamic   gpon-onu_1/1/1:1         vport 3
  30e1.f14a.5b46   6     Dynamic   gpon-onu_1/1/1:1         vport 3
```

**Subscriber edge (L9):**
```
  coverage     : 69.6% (760/1092 ONUs)
  radios       : 89
  ssids        : 178
  bridge_grps  : 744
  lan_services : 0
  wan_bindings : 555
  port_routes  : 0
  stb          : 0
  multicast    : 0
  eth_native_vlan: 0/1531 (0.0%)
  integrity    : 100.0% OK
```

---

### MG-GVS-OLT-BRAIPE.txt

- vendor: **huawei** (MA5800, conf=0.667)
- linhas: 1780 · cobertura **94.2%** · unparsed=104
- inferência: **74.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                12
  service_vlans        0
  uplinks              4
  lacp_groups          0
  static_routes        0
  pons                 2
  onus                 565
  service_ports        984
  dba_profiles         8
  traffic_profiles     11
  line_profiles        15
  service_profiles     16
  wan_profiles         2
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             147
  unparsed             104
```

**Needs review** (total 10):
- `dba_profiles` `DBA-FROM-SMARTOLT-VOIPMNG-10M` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile 'SMARTOLT-VOIPMNG-10M' (cir=2048, pir=10432)_
- `dba_profiles` `DBA-SYNTH-1G` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile 'SMARTOLT-1G-UP', traffic_profile 'SMARTOLT-1G-DOWN'_
- `traffic_profiles` `TT-DADOS` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DADOS' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SMARTOLT_DEFAULT_TCONT_1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT_DEFAULT_TCONT_1G' (bw=1048000 kbps)_
- `traffic_profiles` `TT-SMARTOLT_DEFAULT_TCONT_1G_EPON` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT_DEFAULT_TCONT_1G_EPON' (bw=1000000 kbps)_
- `traffic_profiles` `TT-SMARTOLT-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT-1G' (bw=1024000 kbps)_
- `traffic_profiles` `TT-CLI-BRAIP` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'CLI-BRAIP' (bw=1024000 kbps)_
- `traffic_profiles` `TT-BIG-MAIS-L2L` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'BIG-MAIS-L2L' (bw=1048000 kbps)_
- `traffic_profiles` `TT-FROM-SMARTOLT-VOIPMNG-10M` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-FROM-SMARTOLT-VOIPMNG-10M' (bw=10432 kbps)_
- `traffic_profiles` `TT-SYNTH-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-SYNTH-1G' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-FROM-SMARTOLT-VOIPMNG-10M` (type3, max=10432) conf=0.75 · synthesis
- `DBA-SYNTH-1G` (type3, max=1024000) conf=0.75 · synthesis

**Cross conversions**
```
  → fiberhome len= 53082 e=0 w=1132 i=0 onus=565 sp=984 remap=30 col=0
  → zte       len=216410 e=0 w=1132 i=0 onus=565 sp=984 remap=1 col=0
  → datacom   len= 42512 e=0 w=1132 i=0 onus=565 sp=984 remap=30 col=0
```

**Amostra de linhas não-mapeadas:**
```
   switch vdsl mode to tr129
   xpon mode switch-to profile-mode
   sysmode end
    nat enable
    policy-route 0 port-based eth 1-4 wlan 1-8 wan 1
    llid dba-profile-id 12
   gpon ont home-gateway config-method omci
    ring check enable
    ring check enable
    ring check enable
```

**Subscriber edge (L9):**
```
  coverage     : 4.1% (23/565 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 36
  port_routes  : 72
  stb          : 0
  multicast    : 0
  eth_native_vlan: 20/92 (21.7%)
  integrity    : 100.0% OK
```

---

### MG-GVS-OLT-MARIANA-X7.txt

- vendor: **huawei** (MA5800, conf=0.75)
- linhas: 8498 · cobertura **97.3%** · unparsed=232
- inferência: **41.9%** das ONUs receberam binding

**Entidades**
```
  boards               7
  vlans                20
  service_vlans        0
  uplinks              4
  lacp_groups          0
  static_routes        0
  pons                 5
  onus                 1811
  service_ports        2580
  dba_profiles         10
  traffic_profiles     13
  line_profiles        23
  service_profiles     28
  wan_profiles         2
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1053
  unparsed             232
```

**Needs review** (total 12):
- `dba_profiles` `DBA-FROM-SMARTOLT-VOIPMNG-10M` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile 'SMARTOLT-VOIPMNG-10M' (cir=2048, pir=10432)_
- `dba_profiles` `DBA-SYNTH-1G` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile 'SMARTOLT-1G-UP', traffic_profile 'SMARTOLT-1G-DOWN'_
- `traffic_profiles` `TT-PPPOE` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'PPPOE' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SMARTOLT_DEFAULT_TCONT_1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT_DEFAULT_TCONT_1G' (bw=1048000 kbps)_
- `traffic_profiles` `TT-SMARTOLT_DEFAULT_TCONT_1G_EPON` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT_DEFAULT_TCONT_1G_EPON' (bw=1000000 kbps)_
- `traffic_profiles` `TT-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA '1G' (bw=1056000 kbps)_
- `traffic_profiles` `TT-VLAN-206` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'VLAN-206' (bw=1024000 kbps)_
- `traffic_profiles` `TT-CAMERAS` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'CAMERAS' (bw=1048000 kbps)_
- `traffic_profiles` `TT-COI` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'COI' (bw=1048000 kbps)_
- `traffic_profiles` `TT-BIG-MAIS-L2L` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'BIG-MAIS-L2L' (bw=1048000 kbps)_

**DBA sintetizados:**
- `DBA-FROM-SMARTOLT-VOIPMNG-10M` (type3, max=10432) conf=0.75 · synthesis
- `DBA-SYNTH-1G` (type3, max=1024000) conf=0.75 · synthesis

**Cross conversions**
```
  → fiberhome len=167794 e=0 w=3645 i=0 onus=1811 sp=2580 remap=62 col=0
  → zte       len=651962 e=0 w=3645 i=0 onus=1811 sp=2580 remap=2 col=0
  → datacom   len=142067 e=0 w=3645 i=0 onus=1811 sp=2580 remap=62 col=0
```

**Amostra de linhas não-mapeadas:**
```
  [Active: H903MPLB; Standby: H903MPLB]
  [Patch Info: SPC303]
  [MA5800V100R020: 7310]
   switch vdsl mode to tr129
   xpon mode switch-to profile-mode
   sysmode end
   terminal user name buildrun_new_password root *~ud$1b$GX8S2eU'5C$#_lW6gl9IY;G=oBt4Le1mkg{SjC%/Wv:SXW)<Z`A$* 7 0000:00:00:00:00:00 2000:01:01:09:56:24 root 1 first-login-info 0 self-changed-password 1 "-----"
   terminal user name buildrun_new_password metronw *~uc$1b$:vW\/(0yxM${LfoS@miN39U]r.{X_^@/+to%/_r_0/Y>b-SU+PU$* 0 2000:01:01:10:08:08 2000:01:07:08:38:41 root 2 first-login-info 0 self-changed-password 1 "-----"
   terminal user name buildrun_new_password bignet *~uc$1b$_7cEVo0k-.$&>o):u50)>N3Lb:9zSuXl$%UU!>X4Ci4uY9P<AoH$* 0 2000:01:01:10:43:02 2000:01:01:10:43:02 root 3 first-login-info 1 self-changed-password 0 "-----"
   terminal user name buildrun_new_password smartolt *~uc$1b$KA4i/IXBJR$rNnyFJ|WpSfCKZ-Es@ZWiw;#1xHtJ'Fo{X'"efF.$* 0 2000:01:08:00:23:21 2000:01:08:00:24:16 root 4 first-login-info 0 self-changed-password 0 "-----"
```

**Subscriber edge (L9):**
```
  coverage     : 7.1% (129/1811 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 156
  port_routes  : 352
  stb          : 0
  multicast    : 0
  eth_native_vlan: 116/468 (24.8%)
  integrity    : 100.0% OK
```

---

### OLT HUAWEI PROFILES .txt

- vendor: **huawei** (MA5800, conf=0.167)
- linhas: 2002 · cobertura **100.0%** · unparsed=1
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                0
  service_vlans        0
  uplinks              0
  lacp_groups          0
  static_routes        0
  pons                 0
  onus                 0
  service_ports        0
  dba_profiles         1
  traffic_profiles     1
  line_profiles        143
  service_profiles     143
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1
  unparsed             1
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len=   292 e=0 w=1 i=0 onus=0 sp=0 remap=285 col=0
  → zte       len= 59354 e=0 w=1 i=0 onus=0 sp=0 remap=285 col=0
  → datacom   len=   223 e=0 w=1 i=0 onus=0 sp=0 remap=285 col=0
```

**Amostra de linhas não-mapeadas:**
```
    commit q
```

---

### OLT SERVICOS.txt

- vendor: **huawei** (MA5800, conf=0.417)
- linhas: 1097 · cobertura **59.3%** · unparsed=446
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                33
  service_vlans        0
  uplinks              1
  lacp_groups          0
  static_routes        0
  pons                 1
  onus                 0
  service_ports        0
  dba_profiles         2
  traffic_profiles     3
  line_profiles        16
  service_profiles     16
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             0
  unparsed             446
```

**Needs review** (total 3):
- `dba_profiles` `DBA-SYNTH-1G` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile '1G'_
- `traffic_profiles` `TT-VOZ` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'VOZ' (bw=11344 kbps)_
- `traffic_profiles` `TT-SYNTH-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-SYNTH-1G' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-SYNTH-1G` (type3, max=1024000) conf=0.75 · synthesis

**Cross conversions**
```
  → fiberhome len=  4248 e=0 w=1 i=0 onus=0 sp=0 remap=32 col=0
  → zte       len=  4402 e=0 w=1 i=0 onus=0 sp=0 remap=32 col=0
  → datacom   len=   786 e=0 w=1 i=0 onus=0 sp=0 remap=32 col=0
```

**Amostra de linhas não-mapeadas:**
```
  switch vdsl mode to tr129
   xpon mode switch-to profile-mode
   sysmode end
  ont wan-profile profile-name NAT-ROUTER
    nat enable
  gpon dba bandwidth-assignment-mode max-bandwidth-usage
   gpon ont home-gateway config-method omci
   xpon anti-rogueont autodetect on y
   gpon dba bandwidth-assignment-mode max-bandwidth-usage
   xpon ont-interoperability-mode gpon tcont-pq-priority-reverse enable y
```

---

### OLT-NOVA-BRAIPE.txt

- vendor: **huawei** (MA5800, conf=0.75)
- linhas: 2040 · cobertura **94.1%** · unparsed=121
- inferência: **70.9%** das ONUs receberam binding

**Entidades**
```
  boards               4
  vlans                14
  service_vlans        0
  uplinks              4
  lacp_groups          0
  static_routes        0
  pons                 2
  onus                 608
  service_ports        1044
  dba_profiles         8
  traffic_profiles     11
  line_profiles        18
  service_profiles     17
  wan_profiles         2
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             177
  unparsed             121
```

**Needs review** (total 10):
- `dba_profiles` `DBA-FROM-SMARTOLT-VOIPMNG-10M` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile 'SMARTOLT-VOIPMNG-10M' (cir=2048, pir=10432)_
- `dba_profiles` `DBA-SYNTH-1G` · synthesis conf=0.75
  - _Sintetizado a partir de: traffic_profile 'SMARTOLT-1G-UP', traffic_profile 'SMARTOLT-1G-DOWN'_
- `traffic_profiles` `TT-DADOS` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DADOS' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SMARTOLT_DEFAULT_TCONT_1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT_DEFAULT_TCONT_1G' (bw=1048000 kbps)_
- `traffic_profiles` `TT-SMARTOLT_DEFAULT_TCONT_1G_EPON` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT_DEFAULT_TCONT_1G_EPON' (bw=1000000 kbps)_
- `traffic_profiles` `TT-SMARTOLT-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SMARTOLT-1G' (bw=1024000 kbps)_
- `traffic_profiles` `TT-CLI-BRAIP` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'CLI-BRAIP' (bw=1024000 kbps)_
- `traffic_profiles` `TT-BIG-MAIS-L2L` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'BIG-MAIS-L2L' (bw=1048000 kbps)_
- `traffic_profiles` `TT-FROM-SMARTOLT-VOIPMNG-10M` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-FROM-SMARTOLT-VOIPMNG-10M' (bw=10432 kbps)_
- `traffic_profiles` `TT-SYNTH-1G` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-SYNTH-1G' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-FROM-SMARTOLT-VOIPMNG-10M` (type3, max=10432) conf=0.75 · synthesis
- `DBA-SYNTH-1G` (type3, max=1024000) conf=0.75 · synthesis

**Cross conversions**
```
  → fiberhome len= 57390 e=0 w=1226 i=0 onus=608 sp=1044 remap=31 col=0
  → zte       len=233105 e=0 w=1226 i=0 onus=608 sp=1044 remap=1 col=0
  → datacom   len= 45940 e=0 w=1226 i=0 onus=608 sp=1044 remap=31 col=0
```

**Amostra de linhas não-mapeadas:**
```
  [!ZipFileCrc:61715E5C]
  [Saving user: metronw]
  [Saving time: 2000-01-12 09:56:30-03:00]
  [Active: H905MPLB; Standby: H905MPLB]
  [Patch Info: SPH309]
  [MA5800V100R021: 6610]
   switch vdsl mode to tr129
   xpon mode switch-to profile-mode
   sysmode end
   system modify logon password disable
```

**Subscriber edge (L9):**
```
  coverage     : 4.9% (30/608 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 48
  port_routes  : 96
  stb          : 0
  multicast    : 0
  eth_native_vlan: 21/117 (17.9%)
  integrity    : 100.0% OK
```

---

### OLT-ZTE-CRISTAL.txt

- vendor: **zte** (C600, conf=0.875)
- linhas: 3296 · cobertura **83.3%** · unparsed=551
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                9
  service_vlans        0
  uplinks              14
  lacp_groups          0
  static_routes        0
  pons                 16
  onus                 167
  service_ports        167
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             168
  unparsed             551
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len= 14875 e=166 w=334 i=0 onus=167 sp=167 remap=0 col=0
  → huawei    len= 31451 e=166 w=334 i=0 onus=167 sp=167 remap=0 col=0
  → datacom   len=  7780 e=166 w=334 i=0 onus=167 sp=167 remap=0 col=0
```

**Amostra de linhas não-mapeadas:**
```
  interface vport-1/3/1.1:1
  interface vport-1/3/1.2:1
  interface vport-1/3/1.3:1
  interface vport-1/3/1.4:1
  interface vport-1/3/1.5:1
  interface vport-1/3/1.6:1
  interface vport-1/3/1.7:1
  interface vport-1/3/1.8:1
  interface vport-1/3/1.9:1
  interface vport-1/3/1.10:1
```

**Subscriber edge (L9):**
```
  coverage     : 0.0% (0/167 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 0
  port_routes  : 0
  stb          : 0
  multicast    : 0
  eth_native_vlan: 0/167 (0.0%)
  integrity    : 100.0% OK
```

---

### OLT-ZTE-ITABAIANA.txt

- vendor: **zte** (C600, conf=0.5)
- linhas: 338 · cobertura **45.6%** · unparsed=184
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                3
  service_vlans        0
  uplinks              12
  lacp_groups          0
  static_routes        0
  pons                 16
  onus                 0
  service_ports        0
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1
  unparsed             184
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len=  2040 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
  → huawei    len=  2471 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
  → datacom   len=  1355 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
```

**Amostra de linhas não-mapeadas:**
```
  interface mgmt_eth
    ip address 136.1.1.100 255.255.255.0
  interface vlan4003
    description GERENCIA
    ip address 10.100.177.10 255.255.255.248
  interface null1
  login block 900 attempts 30 within 120
  login on-failure alarm
  system-user
    authorization-template 1
```

---

### OLT-ZTE-MUCURICI.txt

- vendor: **zte** (C600, conf=0.5)
- linhas: 382 · cobertura **48.7%** · unparsed=196
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                4
  service_vlans        0
  uplinks              12
  lacp_groups          0
  static_routes        0
  pons                 16
  onus                 0
  service_ports        0
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1
  unparsed             196
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len=  1975 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
  → huawei    len=  2485 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
  → datacom   len=  1371 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
```

**Amostra de linhas não-mapeadas:**
```
  interface mgmt_eth
    ip address 136.1.1.100 255.255.255.0
  interface vlan4004
    description GERENCIA
    ip address 10.100.177.42 255.255.255.252
  interface null1
  clock sync-source ntp priority 10
  clock timezone brazil -3
  login block 900 attempts 30 within 120
  login on-failure alarm
```

---

### PROVISIONAR_ONU.txt

- vendor: **zte** (C600, conf=0.25)
- linhas: 14 · cobertura **85.7%** · unparsed=2
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                0
  service_vlans        0
  uplinks              0
  lacp_groups          0
  static_routes        0
  pons                 1
  onus                 1
  service_ports        0
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             2
  unparsed             2
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len=   445 e=0 w=1 i=2 onus=1 sp=0 remap=1 col=0
  → huawei    len=   929 e=0 w=1 i=2 onus=1 sp=1 remap=0 col=0
  → datacom   len=   328 e=0 w=1 i=2 onus=1 sp=0 remap=1 col=0
```

**Amostra de linhas não-mapeadas:**
```
  service-port 1
   gpon 1/1/2 onu 0 gem 1 match vlan vlan-id 200 action vlan replace vlan-id 200
```

**Subscriber edge (L9):**
```
  coverage     : 0.0% (0/1 ONUs)
  radios       : 0
  ssids        : 0
  bridge_grps  : 0
  lan_services : 0
  wan_bindings : 0
  port_routes  : 0
  stb          : 0
  multicast    : 0
  eth_native_vlan: 0/1 (0.0%)
  integrity    : 100.0% OK
```

---

### SCRIPT-GER-OLT.txt

- vendor: **huawei** (MA5800, conf=0.083)
- linhas: 63 · cobertura **49.2%** · unparsed=32
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                0
  service_vlans        0
  uplinks              0
  lacp_groups          0
  static_routes        0
  pons                 0
  onus                 0
  service_ports        0
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     0
  wan_profiles         0
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             1
  unparsed             32
```

**Needs review** (total 2):
- `dba_profiles` `DBA-DEFAULT` · default conf=0.15
  - _Nenhum DBA detectado na origem nem inferível por nome. DBA-DEFAULT criado como placeholder — revise antes de produção._
- `traffic_profiles` `TT-DEFAULT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-DEFAULT' (bw=1024000 kbps)_

**DBA sintetizados:**
- `DBA-DEFAULT` (type4, max=1024000) conf=0.15 · default

**Cross conversions**
```
  → fiberhome len=   287 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
  → zte       len=   367 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
  → datacom   len=   218 e=0 w=0 i=0 onus=0 sp=0 remap=0 col=0
```

**Amostra de linhas não-mapeadas:**
```
  system modify logon password disable
  system user password security mode basic
  system user password security-length 8
  system user name security-length 6
  terminal user password
   Old Password(<=15 chars): [SENHA COMPLEXA INSERIDA NO PRIMEIRO ACESSO] New Password(length<6,15>): [NOVA SENHA PADRÃO] Confirm Password(length<6,15>): [CONFIRMAR A SENHA] Information takes effect Repeat this operation? (y/n)[n]:n
  terminal user name
   User Name(length<6,15>):cgravato User Password(length<6,15>): [SENHA PADRÃO] Confirm Password(length<6,15>): [CONFIRMAR A SENHA] User profile name(<=15 chars)[root]:root User's Level: 1. Common User 2. Operator 3. Administrator:3 Permitted Reenter Number(0--20):20 User's Appended Info(<=30 chars): [SÓ DAR ENTER] Adding user successfully Repeat this operation? (y/n)[n]:n
  link-aggregation 0/[SLOT] [PORTA-MASTER] egress-ingress workmode lacp-static
  link-aggregation add-member 0/[SLOT]/[PORTA-MASTER] 0/[SLOT] [PORTA-SECUNDÁRIA]
```

---

### Script_OLT_Huawei.txt

- vendor: **huawei** (MA5800, conf=0.333)
- linhas: 578 · cobertura **96.4%** · unparsed=21
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                0
  service_vlans        0
  uplinks              0
  lacp_groups          0
  static_routes        0
  pons                 1
  onus                 0
  service_ports        0
  dba_profiles         17
  traffic_profiles     17
  line_profiles        32
  service_profiles     32
  wan_profiles         1
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             0
  unparsed             21
```

**Needs review** (total 17):
- `traffic_profiles` `TT-SLOT1-PON0` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON0' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON1` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON1' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON2` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON2' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON3` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON3' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON5` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON5' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON5` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON5' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON6` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON6' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON7` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON7' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON8` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON8' (bw=1024000 kbps)_
- `traffic_profiles` `TT-SLOT1-PON9` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'SLOT1-PON9' (bw=1024000 kbps)_

**Cross conversions**
```
  → fiberhome len=  1504 e=0 w=1 i=0 onus=0 sp=0 remap=0 col=0
  → zte       len= 12066 e=0 w=1 i=0 onus=0 sp=0 remap=0 col=0
  → datacom   len=  1098 e=0 w=1 i=0 onus=0 sp=0 remap=0 col=0
```

**Amostra de linhas não-mapeadas:**
```
  switch vdsl mode to tr129
   xpon mode switch-to profile-mode
   sysmode end
    nat enable
   xpon anti-rogueont autodetect on
   gpon dba bandwidth-assignment-mode max-bandwidth-usage
   xpon ont-interoperability-mode gpon tcont-pq-priority-reverse enable
   xpon ont-interoperability-mode gpon ont-wan-config set-after-create
   gpon ont home-gateway config-method omci
   autosave interval on
```