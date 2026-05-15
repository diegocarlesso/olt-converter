# Fidelity Report — pipeline real

> Gerado por `fidelity_report.py`. Reflete o estado *real* da
> pipeline (parse → inferência → síntese → equivalência → remap → render)
> contra os backups disponíveis. Use para calibrar a matriz de
> compatibilidade declarativa.

## 1. Sumário por arquivo

| Arquivo | Vendor | Linhas | Cobertura | ONUs | SPs | Inferência | Issues | Remaps |
|--------|--------|-------:|----------:|-----:|----:|----------:|-------:|-------:|
| datacom_dm4615_basic.cfg | datacom | 30 | 80.0% | 1 | 0 | 0.0% | 0e/0w | varia |
| fiberhome_an5516_basic.cfg | fiberhome | 38 | 100.0% | 3 | 0 | 0.0% | 0e/0w | varia |
| huawei_ma5800_basic.cfg | huawei | 44 | 97.7% | 2 | 4 | 100.0% | 0e/4w | varia |
| zte_c600_basic.cfg | zte | 45 | 100.0% | 2 | 2 | 0.0% | 0e/4w | varia |
| BACKUP-FIBERHOME.txt | fiberhome | 15992 | 17.9% | 711 | 0 | 0.0% | 0e/3w | varia |
| ETA-LOJA-ZTE-OLT01.txt | zte | 27647 | 8.6% | 0 | 0 | 0.0% | 0e/0w | varia |
| MG-GVS-OLT-BRAIPE.txt | huawei | 1780 | 79.9% | 565 | 983 | 73.8% | 0e/1132w | varia |
| MG-GVS-OLT-MARIANA-X7.txt | — | 8498 | FAIL | — | — | — | — | — |
| OLT HUAWEI PROFILES .txt | huawei | 2002 | 78.5% | 0 | 0 | 0.0% | 0e/1w | varia |
| OLT SERVICOS.txt | huawei | 1097 | 33.9% | 0 | 0 | 0.0% | 0e/1w | varia |
| OLT-NOVA-BRAIPE.txt | huawei | 2040 | 75.3% | 608 | 1040 | 70.2% | 0e/1226w | varia |
| OLT-ZTE-CRISTAL.txt | zte | 3296 | 41.8% | 167 | 0 | 0.0% | 0e/0w | varia |
| OLT-ZTE-ITABAIANA.txt | zte | 338 | 45.0% | 0 | 0 | 0.0% | 0e/0w | varia |
| OLT-ZTE-MUCURICI.txt | zte | 382 | 48.4% | 0 | 0 | 0.0% | 0e/0w | varia |
| PROVISIONAR_ONU.txt | zte | 14 | 85.7% | 1 | 0 | 0.0% | 0e/1w | varia |
| SCRIPT-GER-OLT.txt | huawei | 63 | 22.2% | 0 | 0 | 0.0% | 0e/0w | varia |
| Script_OLT_Huawei.txt | huawei | 578 | 63.1% | 0 | 0 | 0.0% | 0e/1w | varia |

## 2. Top unsupported commands (normalizados, agregados)

Patterns que aparecem em `raw_unparsed` após normalização (números e paths viram `<N>`/`<PATH>`).
Bom indicador de features a priorizar nos parsers.

| # | Ocorrências | Pattern |
|--:|------------:|---------|
| 1 | 1207 | `vlan port eth_0/<N> mode tag vlan <N>` |
| 2 | 1202 | `service-port <N> vport <N> user-vlan <N> vlan <N>` |
| 3 | 1092 | `interface gpon-onu_1/<PATH>:<N>` |
| 4 | 1092 | `sn-bind enable sn` |
| 5 | 1092 | `pon-onu-mng gpon-onu_1/<PATH>:<N>` |
| 6 | 711 | `set onu_pon_type slot <N> pon <N> onu <N> pon_type <N>` |
| 7 | 711 | `set service_ba sl <N> p <N> o <N> ty iptv fix <N> as <N> max <N>` |
| 8 | 711 | `set service_ba sl <N> p <N> o <N> ty data fix <N> as <N> max <N>` |
| 9 | 708 | `set service_ba sl <N> p <N> o <N> ty voi fix <N> as <N> max <N>` |
| 10 | 668 | `security-mgmt <N> state enable mode forward protocol web` |
| 11 | 630 | `gemport <N> tcont <N>` |
| 12 | 625 | `switchport-bind switch_0/<N> veip <N>` |
| 13 | 617 | `onu <N> type ZTE-F660 sn <SN>` |
| 14 | 609 | `tcont <N> gap mode2` |
| 15 | 598 | `set port_separate slot <N> pon <N> onu <N> separate disable` |
| 16 | 568 | `gemport <N> name INTERNET tcont <N>` |
| 17 | 543 | `security-mgmt <N> start-src-ip <N>.<N>.<N>.<N> end-src-ip <N>.<N>.<N>.<N>` |
| 18 | 542 | `tr069-mgmt <N> state unlock` |
| 19 | 534 | `firewall enable level low anti-hack disable` |
| 20 | 527 | `tcont <N> name INTERNET profile 1Gb` |
| 21 | 505 | `switchport-bind switch_0/<N> iphost <N>` |
| 22 | 486 | `set wifi_serv_cfg slot <N> pon <N> onu <N> serv_no <N> wifi enable district brazil channel <N> standard <N>.11bgn txpower <N> frequency <N>.4ghz freq_bandwidth 20mhz/40mhz` |
| 23 | 476 | `dhcp-ip ethuni eth_0/<N> from-onu` |
| 24 | 471 | `onu wps-config slot <N> pon <N> onu <N> switch enable switch_5g enable` |
| 25 | 463 | `tcont <N> profile i6-1GB` |
| 26 | 455 | `set wifi_serv_cfg slot <N> pon <N> onu <N> serv_no <N> wifi enable district brazil channel <N> standard <N>.11ac txpower <N> frequency <N>.8ghz freq_bandwidth 80mhz` |
| 27 | 434 | `service INTERNET gemport <N> vlan <N>` |
| 28 | 415 | `tr069-mgmt <N> acs https://acs.brasiltecpar.com.br:<N>/` |
| 29 | 391 | `set wifi_serv_wlan slot <N> pon <N> onu <N> serv_no <N> index <N> ssid disable fh_ssid3 hide disable authmode wpa2psk encrypt_type aes wpakey <HEX> interval <N> radius_serv ipv4 <N>.<N>.<N>.<N> port <N> pswd null wep_length 40bit key_index <N> wep_key null null null null wapi_serv_addr <N>.<N>.<N>.<N> <N> wifi_connect_num <N>` |
| 30 | 391 | `set wifi_serv_wlan slot <N> pon <N> onu <N> serv_no <N> index <N> ssid disable fh_ssid4 hide disable authmode wpa2psk encrypt_type aes wpakey <HEX> interval <N> radius_serv ipv4 <N>.<N>.<N>.<N> port <N> pswd null wep_length 40bit key_index <N> wep_key null null null null wapi_serv_addr <N>.<N>.<N>.<N> <N> wifi_connect_num <N>` |

## 3. Entidades que precisam de revisão (needs_review=True)

Contagem por coleção. `needs_review` é setado quando algo foi
inferido com baixa confiança, sintetizado, default-fallback ou remapeado.

| Coleção | needs_review |
|---------|-------------:|
| `traffic_profiles` | 50 |
| `dba_profiles` | 16 |

## 4. Bindings inferidos (cobertura por confidence)

Cobertura média da inferência de service-ports: **15.2%** das ONUs receberam binding.

Distribuição global por bucket de confidence:

| Bucket | Bindings |
|--------|---------:|
| medium | 2 |
| high | 844 |

### Exemplos representativos (origem do binding rastreável)

- **huawei_ma5800_basic.cfg** · ONU gpon 0/1:0 → VLAN 100 · conf=**0.85**
  - reason: _service-profile Generic_1_V100 traduz para VLAN 100_
  - signals: `service-profile Generic_1_V100 eth1 translation=100 user_vlan=100`
- **huawei_ma5800_basic.cfg** · ONU gpon 0/1:1 → VLAN 100 · conf=**0.85**
  - reason: _service-profile Generic_1_V100 traduz para VLAN 100_
  - signals: `service-profile Generic_1_V100 eth1 translation=100 user_vlan=100`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/0:0 → VLAN 201 · conf=**1.0**
  - reason: _service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/0:1 → VLAN 201 · conf=**1.0**
  - reason: _service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/0:2 → VLAN 201 · conf=**1.0**
  - reason: _service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **MG-GVS-OLT-BRAIPE.txt** · ONU gpon 0/0:3 → VLAN 201 · conf=**1.0**
  - reason: _service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **OLT-NOVA-BRAIPE.txt** · ONU gpon 0/0:0 → VLAN 201 · conf=**1.0**
  - reason: _service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`
- **OLT-NOVA-BRAIPE.txt** · ONU gpon 0/0:1 → VLAN 201 · conf=**1.0**
  - reason: _service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201 | service-profile Generic_1_V201 traduz para VLAN 201_
  - signals: `service-profile Generic_1_V201 eth1 translation=201 user_vlan=201, service-profile Generic_1_V201 eth2 translation=201 user_vlan=201, service-profile Generic_1_V201 eth3 translation=201 user_vlan=201, service-profile Generic_1_V201 eth4 translation=201 user_vlan=201`

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

## 6. Heatmap origem → destino (conversões reais)

Soma das métricas dos arquivos analisados. Cores: 🟢 OK · 🟡 atenção · 🔴 problema.

| origem ↓ destino → | **fiberhome** | **huawei** | **zte** | **datacom** |
|---|---|---|---|---|
| **fiberhome** | — | 🟢 2f · 0e · 0w · 8r | · | 🟢 2f · 0e · 3w · 5r |
| **huawei** | 🟡 7f · 0e · 2365w · 292r | — | 🟢 4f · 0e · 3w · 230r | 🟡 7f · 0e · 2365w · 292r |
| **zte** | 🟢 6f · 0e · 1w · 1r | 🟢 6f · 0e · 1w · 0r | — | 🟢 6f · 0e · 1w · 1r |
| **datacom** | 🟢 1f · 0e · 0w · 0r | 🟢 1f · 0e · 0w · 0r | · | — |

Legenda: `f`=arquivos, `e`=errors, `w`=warnings, `r`=remaps aplicados

## 7. Scores globais derivados da matriz

| Vendor | parser_coverage | renderer_completeness |
|--------|---------------:|---------------------:|
| **fiberhome** | 41% | 47% |
| **huawei** | 62% | 59% |
| **zte** | 49% | 49% |
| **datacom** | 38% | 38% |

### semantic_fidelity por par

| | → **fiberhome** | → **huawei** | → **zte** | → **datacom** |
|---|---|---|---|---|
| **fiberhome** | — | 59% (8/17/11/0) | 56% (6/19/11/0) | 53% (5/21/10/0) |
| **huawei** | 62% (8/19/9/0) | — | 62% (8/19/9/0) | 59% (7/18/11/0) |
| **zte** | 58% (6/20/10/0) | 62% (9/16/11/0) | — | 55% (6/17/13/0) |
| **datacom** | 55% (5/21/10/0) | 58% (7/17/12/0) | 55% (6/17/13/0) | — |

Contadores entre parênteses: (FULL / PARTIAL / NONE / UNSUPPORTED)

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
  → zte       FAIL: UndefinedError("'dict object' has no attribute 'service_profile_name'")
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
  → zte       FAIL: UndefinedError("'dict object' has no attribute 'service_profile_name'")
  → datacom   len=   794 e=0 w=0 i=0 onus=3 sp=0 remap=2 col=0
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
  → zte       FAIL: UndefinedError("'dict object' has no attribute 'service_profile_name'")
  → datacom   len=   613 e=0 w=4 i=0 onus=2 sp=4 remap=1 col=0
```

**Amostra de linhas não-mapeadas:**
```
   system modify logon password disable
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

---

### BACKUP-FIBERHOME.txt

- vendor: **fiberhome** (AN5516, conf=1.0)
- linhas: 15992 · cobertura **17.9%** · unparsed=13122
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               8
  vlans                2086
  service_vlans        83
  uplinks              12
  lacp_groups          0
  static_routes        1
  pons                 11
  onus                 711
  service_ports        0
  dba_profiles         1
  traffic_profiles     1
  line_profiles        0
  service_profiles     3
  wan_profiles         0
  onu_type_profiles    3
  users                2
  radius_servers       1
  qos_attachments      28
  warnings             711
  unparsed             13122
```

**Needs review** (total 2):
- `dba_profiles` `DBA-SYNTH-MGMT` · synthesis conf=0.75
  - _Sintetizado a partir de: service_vlan 'GERENCIA'_
- `traffic_profiles` `TT-SYNTH-MGMT` · synthesis conf=0.7
  - _Sintetizado a partir do DBA 'DBA-SYNTH-MGMT' (bw=10240 kbps)_

**DBA sintetizados:**
- `DBA-SYNTH-MGMT` (type3, max=10240) conf=0.75 · synthesis

**Cross conversions**
```
  → huawei    len= 95933 e=0 w=0 i=746 onus=711 sp=0 remap=6 col=0
  → zte       FAIL: UndefinedError("'dict object' has no attribute 'service_profile_name'")
  → datacom   len= 74571 e=0 w=3 i=746 onus=711 sp=0 remap=3 col=0
```

**Amostra de linhas não-mapeadas:**
```
  set autho sl 1 p 1 ty HG6145D2 o 1 phy FHTTc08ed612 pas null
  set autho sl 1 p 1 ty 5506-04-FA o 2 phy FHTT9cd168e8 pas null
  set autho sl 1 p 1 ty HG6145F3 o 3 phy FHTTfe2413ac pas null
  set autho sl 1 p 1 ty HG6145D2_2 o 4 phy FHTTc0a67080 pas null
  set autho sl 1 p 1 ty HG6145D2 o 5 phy FHTTfe0361b9 pas null
  set autho sl 1 p 1 ty HG6145D2 o 6 phy FHTTfe0365aa pas null
  set autho sl 1 p 1 ty 5506-04-FA o 7 phy FHTT969314f8 pas null
  set autho sl 1 p 1 ty HG6145E o 8 phy FHTTc030eb8a pas null
  set autho sl 1 p 1 ty HG6145D2_2 o 9 phy FHTTfe1aa553 pas null
  set autho sl 1 p 1 ty HG6145F3 o 10 phy FHTTfe242c88 pas null
```

---

### ETA-LOJA-ZTE-OLT01.txt

- vendor: **zte** (C600, conf=0.375)
- linhas: 27647 · cobertura **8.6%** · unparsed=25280
- inferência: **0.0%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                9
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
  unparsed             25280
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
  → fiberhome len=  1736 e=0 w=0 i=1 onus=0 sp=0 remap=0 col=0
  → huawei    len=   846 e=0 w=0 i=1 onus=0 sp=0 remap=0 col=0
  → datacom   len=   510 e=0 w=0 i=1 onus=0 sp=0 remap=0 col=0
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

---

### MG-GVS-OLT-BRAIPE.txt

- vendor: **huawei** (MA5800, conf=0.667)
- linhas: 1780 · cobertura **79.9%** · unparsed=358
- inferência: **73.8%** das ONUs receberam binding

**Entidades**
```
  boards               0
  vlans                12
  service_vlans        0
  uplinks              4
  lacp_groups          0
  static_routes        0
  pons                 16
  onus                 565
  service_ports        983
  dba_profiles         8
  traffic_profiles     11
  line_profiles        15
  service_profiles     16
  wan_profiles         2
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             148
  unparsed             358
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
  → fiberhome len= 53538 e=0 w=1132 i=0 onus=565 sp=983 remap=30 col=0
  → zte       FAIL: UndefinedError("'dict object' has no attribute 'service_profile_name'")
  → datacom   len= 42864 e=0 w=1132 i=0 onus=565 sp=983 remap=30 col=0
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

### MG-GVS-OLT-MARIANA-X7.txt — FAIL
```
parse failed: 1 validation error for ServicePort
service_port_id
  Input should be greater than or equal to 1 [type=greater_than_equal, input_value=0, input_type=int]
    For further information visit https://errors.pydantic.dev/2.13/v/greater_than_equal
```


---

### OLT HUAWEI PROFILES .txt

- vendor: **huawei** (MA5800, conf=0.167)
- linhas: 2002 · cobertura **78.5%** · unparsed=430
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
  unparsed             430
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
  → fiberhome len=   292 e=0 w=1 i=0 onus=0 sp=0 remap=198 col=88
  → zte       len= 53062 e=0 w=1 i=0 onus=0 sp=0 remap=198 col=88
  → datacom   len=   223 e=0 w=1 i=0 onus=0 sp=0 remap=198 col=88
```

**Amostra de linhas não-mapeadas:**
```
    tcont 5 dba-profile-id 10
    gem add 5 eth tcont 5
    gem mapping 5 0 vlan 1510
    tcont 4 dba-profile-id 10
    gem add 1 eth tcont 4
    gem mapping 1 0 vlan 1511
    tcont 4 dba-profile-id 10
    gem add 1 eth tcont 4
    gem mapping 1 0 vlan 1520
    tcont 4 dba-profile-id 10
```

---

### OLT SERVICOS.txt

- vendor: **huawei** (MA5800, conf=0.417)
- linhas: 1097 · cobertura **33.9%** · unparsed=725
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
  unparsed             725
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
  → zte       len=  3698 e=0 w=1 i=0 onus=0 sp=0 remap=32 col=0
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
   xpon anti-rogueont autodetect on
  y
   gpon dba bandwidth-assignment-mode max-bandwidth-usage
```

---

### OLT-NOVA-BRAIPE.txt

- vendor: **huawei** (MA5800, conf=0.75)
- linhas: 2040 · cobertura **75.3%** · unparsed=504
- inferência: **70.2%** das ONUs receberam binding

**Entidades**
```
  boards               4
  vlans                14
  service_vlans        0
  uplinks              4
  lacp_groups          0
  static_routes        0
  pons                 16
  onus                 608
  service_ports        1040
  dba_profiles         8
  traffic_profiles     11
  line_profiles        18
  service_profiles     17
  wan_profiles         2
  onu_type_profiles    0
  users                0
  radius_servers       0
  qos_attachments      0
  warnings             181
  unparsed             504
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
  → fiberhome len= 57846 e=0 w=1226 i=0 onus=608 sp=1040 remap=31 col=0
  → zte       FAIL: UndefinedError("'dict object' has no attribute 'service_profile_name'")
  → datacom   len= 46292 e=0 w=1226 i=0 onus=608 sp=1040 remap=31 col=0
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

---

### OLT-ZTE-CRISTAL.txt

- vendor: **zte** (C600, conf=0.875)
- linhas: 3296 · cobertura **41.8%** · unparsed=1918
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
  warnings             168
  unparsed             1918
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
  → fiberhome len= 14875 e=0 w=0 i=0 onus=167 sp=0 remap=0 col=0
  → huawei    len= 16237 e=0 w=0 i=0 onus=167 sp=0 remap=0 col=0
  → datacom   len=  7780 e=0 w=0 i=0 onus=167 sp=0 remap=0 col=0
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

---

### OLT-ZTE-ITABAIANA.txt

- vendor: **zte** (C600, conf=0.5)
- linhas: 338 · cobertura **45.0%** · unparsed=186
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
  unparsed             186
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
- linhas: 382 · cobertura **48.4%** · unparsed=197
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
  unparsed             197
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

---

### SCRIPT-GER-OLT.txt

- vendor: **huawei** (MA5800, conf=0.083)
- linhas: 63 · cobertura **22.2%** · unparsed=49
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
  unparsed             49
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
  config
  system modify logon password disable
  system user password security mode basic
  system user password security-length 8
  system user name security-length 6
  terminal user password
  Old Password(<=15 chars): [SENHA COMPLEXA INSERIDA NO PRIMEIRO ACESSO]
  New Password(length<6,15>): [NOVA SENHA PADRÃO]
  Confirm Password(length<6,15>): [CONFIRMAR A SENHA]
  Information takes effect
```

---

### Script_OLT_Huawei.txt

- vendor: **huawei** (MA5800, conf=0.333)
- linhas: 578 · cobertura **63.1%** · unparsed=213
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
  unparsed             213
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
  → zte       len=  9814 e=0 w=1 i=0 onus=0 sp=0 remap=0 col=0
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
    monitor uplink-port traffic port 0/8/0
```