# Compatibility Matrix

> Gerado por `generate_matrix.py`. Reflete o estado atual do parser, renderer e engine de equivalência de cada vendor.


## Scores globais por vendor

| Vendor | Parser coverage | Renderer completeness |
|--------|----------------:|----------------------:|
| **fiberhome** | 41% | 47% |
| **huawei** | 62% | 59% |
| **zte** | 49% | 49% |
| **datacom** | 38% | 38% |

## Semantic fidelity por par (origem → destino)

| | → **fiberhome** | → **huawei** | → **zte** | → **datacom** |
|---|---|---|---|---|
| **fiberhome** ↓ | — | 59% (8/17/11/0) | 56% (6/19/11/0) | 53% (5/21/10/0) |
| **huawei** ↓ | 62% (8/19/9/0) | — | 62% (8/19/9/0) | 59% (7/18/11/0) |
| **zte** ↓ | 58% (6/20/10/0) | 62% (9/16/11/0) | — | 55% (6/17/13/0) |
| **datacom** ↓ | 55% (5/21/10/0) | 58% (7/17/12/0) | 55% (6/17/13/0) | — |

Legenda dos contadores: (FULL / PARTIAL / NONE / UNSUPPORTED)


## Matriz detalhada por feature


### Origem: **fiberhome**

| Feature | → huawei | → zte | → datacom |
|---|---|---|---|
| `hostname` | ✅ 100% | ✅ 100% | ✅ 100% |
| `vlan` | ✅ 98% | ✅ 98% | ✅ 98% |
| `service_vlan` | ⚠️ 46% | ⚠️ 46% | ⚠️ 46% |
| `vlan_translation` | ⚠️ 68% | ⚠️ 62% | ⚠️ 59% |
| `qinq` | ❌ 43% | ⚠️ 46% | ⚠️ 46% |
| `uplink` | ✅ 93% | ✅ 96% | ✅ 96% |
| `uplink_lacp` | ❌ 43% | ❌ 43% | ⚠️ 49% |
| `static_route` | ✅ 85% | ⚠️ 82% | ⚠️ 82% |
| `mgmt_vlan_ip` | ✅ 98% | ✅ 98% | ⚠️ 83% |
| `boards` | ⚠️ 80% | ⚠️ 59% | ⚠️ 50% |
| `pon` | ✅ 92% | ✅ 92% | ✅ 92% |
| `onu_auth` | ✅ 98% | ✅ 98% | ✅ 92% |
| `onu_admin_state` | ⚠️ 60% | ⚠️ 69% | ⚠️ 57% |
| `onu_eth_ports` | ⚠️ 58% | ⚠️ 64% | ⚠️ 49% |
| `onu_native_vlan` | ⚠️ 61% | ⚠️ 67% | ⚠️ 52% |
| `onu_user_vlan` | ⚠️ 58% | ⚠️ 49% | ⚠️ 46% |
| `gem_tcont` | ⚠️ 62% | ⚠️ 56% | ⚠️ 53% |
| `dba_profile` | ⚠️ 65% | ⚠️ 56% | ⚠️ 65% |
| `traffic_profile` | ⚠️ 62% | ❌ 44% | ❌ 44% |
| `line_profile` | ⚠️ 63% | ⚠️ 57% | ⚠️ 54% |
| `service_profile` | ⚠️ 81% | ⚠️ 75% | ⚠️ 75% |
| `service_port` | ⚠️ 64% | ⚠️ 64% | ⚠️ 49% |
| `multicast_igmp` | ❌ 24% | ❌ 24% | ❌ 24% |
| `multicast_gem` | ❌ 20% | ❌ 20% | ❌ 20% |
| `wan_profile` | ❌ 37% | ❌ 16% | ❌ 16% |
| `pppoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `ipoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `policy_route` | ❌ 30% | ❌ 12% | ❌ 12% |
| `snmp` | ⚠️ 55% | ⚠️ 55% | ⚠️ 46% |
| `ssh_cipher_detail` | ❌ 40% | ❌ 40% | ❌ 40% |
| `aaa_radius` | ⚠️ 75% | ⚠️ 75% | ⚠️ 66% |
| `users` | ⚠️ 71% | ⚠️ 68% | ⚠️ 62% |
| `qos_attachment` | ⚠️ 57% | ⚠️ 57% | ⚠️ 48% |
| `omci_provisioning` | ✅ 85% | ⚠️ 79% | ⚠️ 76% |
| `stb_ports` | ❌ 16% | ❌ 16% | ❌ 16% |
| `ssid_binding` | ❌ 12% | ❌ 12% | ❌ 12% |

### Origem: **huawei**

| Feature | → fiberhome | → zte | → datacom |
|---|---|---|---|
| `hostname` | ✅ 100% | ✅ 100% | ✅ 100% |
| `vlan` | ✅ 95% | ✅ 98% | ✅ 98% |
| `service_vlan` | ⚠️ 46% | ❌ 16% | ❌ 16% |
| `vlan_translation` | ⚠️ 68% | ⚠️ 80% | ⚠️ 77% |
| `qinq` | ❌ 43% | ⚠️ 49% | ⚠️ 49% |
| `uplink` | ✅ 93% | ✅ 93% | ✅ 93% |
| `uplink_lacp` | ⚠️ 49% | ⚠️ 52% | ⚠️ 58% |
| `static_route` | ✅ 85% | ⚠️ 67% | ⚠️ 67% |
| `mgmt_vlan_ip` | ✅ 98% | ✅ 98% | ⚠️ 83% |
| `boards` | ⚠️ 80% | ⚠️ 59% | ⚠️ 50% |
| `pon` | ✅ 86% | ✅ 98% | ✅ 98% |
| `onu_auth` | ✅ 98% | ✅ 98% | ✅ 92% |
| `onu_admin_state` | ⚠️ 60% | ⚠️ 75% | ⚠️ 63% |
| `onu_eth_ports` | ⚠️ 64% | ⚠️ 82% | ⚠️ 67% |
| `onu_native_vlan` | ⚠️ 67% | ⚠️ 82% | ⚠️ 67% |
| `onu_user_vlan` | ⚠️ 70% | ⚠️ 73% | ⚠️ 70% |
| `gem_tcont` | ⚠️ 71% | ⚠️ 80% | ⚠️ 77% |
| `dba_profile` | ⚠️ 83% | ⚠️ 83% | ✅ 92% |
| `traffic_profile` | ⚠️ 77% | ⚠️ 74% | ⚠️ 74% |
| `line_profile` | ⚠️ 72% | ⚠️ 84% | ⚠️ 81% |
| `service_profile` | ⚠️ 84% | ⚠️ 84% | ⚠️ 84% |
| `service_port` | ⚠️ 79% | ✅ 94% | ⚠️ 79% |
| `multicast_igmp` | ❌ 24% | ❌ 24% | ❌ 24% |
| `multicast_gem` | ❌ 20% | ❌ 20% | ❌ 20% |
| `wan_profile` | ❌ 43% | ❌ 43% | ❌ 43% |
| `pppoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `ipoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `policy_route` | ❌ 36% | ❌ 36% | ❌ 36% |
| `snmp` | ⚠️ 55% | ⚠️ 58% | ⚠️ 49% |
| `ssh_cipher_detail` | ⚠️ 49% | ⚠️ 49% | ⚠️ 49% |
| `aaa_radius` | ⚠️ 78% | ⚠️ 57% | ⚠️ 48% |
| `users` | ⚠️ 56% | ⚠️ 47% | ❌ 41% |
| `qos_attachment` | ⚠️ 54% | ⚠️ 48% | ❌ 39% |
| `omci_provisioning` | ✅ 85% | ✅ 94% | ✅ 91% |
| `stb_ports` | ❌ 16% | ❌ 16% | ❌ 16% |
| `ssid_binding` | ❌ 12% | ❌ 12% | ❌ 12% |

### Origem: **zte**

| Feature | → fiberhome | → huawei | → datacom |
|---|---|---|---|
| `hostname` | ✅ 100% | ✅ 100% | ✅ 100% |
| `vlan` | ✅ 95% | ✅ 98% | ✅ 98% |
| `service_vlan` | ⚠️ 46% | ❌ 16% | ❌ 16% |
| `vlan_translation` | ⚠️ 62% | ⚠️ 80% | ⚠️ 71% |
| `qinq` | ⚠️ 46% | ⚠️ 49% | ⚠️ 52% |
| `uplink` | ✅ 96% | ✅ 93% | ✅ 96% |
| `uplink_lacp` | ❌ 43% | ⚠️ 46% | ⚠️ 52% |
| `static_route` | ⚠️ 82% | ⚠️ 67% | ⚠️ 64% |
| `mgmt_vlan_ip` | ✅ 98% | ✅ 98% | ⚠️ 83% |
| `boards` | ⚠️ 59% | ⚠️ 59% | ❌ 29% |
| `pon` | ✅ 86% | ✅ 98% | ✅ 98% |
| `onu_auth` | ✅ 98% | ✅ 98% | ✅ 92% |
| `onu_admin_state` | ⚠️ 69% | ⚠️ 75% | ⚠️ 72% |
| `onu_eth_ports` | ⚠️ 70% | ⚠️ 82% | ⚠️ 73% |
| `onu_native_vlan` | ⚠️ 79% | ✅ 88% | ⚠️ 79% |
| `onu_user_vlan` | ⚠️ 61% | ⚠️ 73% | ⚠️ 61% |
| `gem_tcont` | ⚠️ 65% | ⚠️ 80% | ⚠️ 71% |
| `dba_profile` | ⚠️ 74% | ⚠️ 83% | ⚠️ 83% |
| `traffic_profile` | ⚠️ 59% | ⚠️ 74% | ⚠️ 56% |
| `line_profile` | ⚠️ 66% | ⚠️ 84% | ⚠️ 75% |
| `service_profile` | ⚠️ 78% | ⚠️ 84% | ⚠️ 78% |
| `service_port` | ⚠️ 79% | ✅ 94% | ⚠️ 79% |
| `multicast_igmp` | ❌ 24% | ❌ 24% | ❌ 24% |
| `multicast_gem` | ❌ 20% | ❌ 20% | ❌ 20% |
| `wan_profile` | ❌ 16% | ❌ 37% | ❌ 16% |
| `pppoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `ipoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `policy_route` | ❌ 12% | ❌ 30% | ❌ 12% |
| `snmp` | ⚠️ 55% | ⚠️ 58% | ⚠️ 49% |
| `ssh_cipher_detail` | ❌ 40% | ❌ 40% | ❌ 40% |
| `aaa_radius` | ⚠️ 75% | ⚠️ 54% | ⚠️ 45% |
| `users` | ⚠️ 53% | ⚠️ 47% | ❌ 38% |
| `qos_attachment` | ⚠️ 48% | ❌ 42% | ❌ 33% |
| `omci_provisioning` | ⚠️ 79% | ✅ 94% | ✅ 85% |
| `stb_ports` | ❌ 16% | ❌ 16% | ❌ 16% |
| `ssid_binding` | ❌ 12% | ❌ 12% | ❌ 12% |

### Origem: **datacom**

| Feature | → fiberhome | → huawei | → zte |
|---|---|---|---|
| `hostname` | ✅ 100% | ✅ 100% | ✅ 100% |
| `vlan` | ✅ 95% | ✅ 98% | ✅ 98% |
| `service_vlan` | ⚠️ 46% | ❌ 16% | ❌ 16% |
| `vlan_translation` | ⚠️ 59% | ⚠️ 77% | ⚠️ 71% |
| `qinq` | ⚠️ 46% | ⚠️ 49% | ⚠️ 52% |
| `uplink` | ✅ 96% | ✅ 93% | ✅ 96% |
| `uplink_lacp` | ⚠️ 49% | ⚠️ 52% | ⚠️ 52% |
| `static_route` | ⚠️ 82% | ⚠️ 67% | ⚠️ 64% |
| `mgmt_vlan_ip` | ⚠️ 83% | ⚠️ 83% | ⚠️ 83% |
| `boards` | ⚠️ 50% | ⚠️ 50% | ❌ 29% |
| `pon` | ✅ 86% | ✅ 98% | ✅ 98% |
| `onu_auth` | ✅ 92% | ✅ 92% | ✅ 92% |
| `onu_admin_state` | ⚠️ 57% | ⚠️ 63% | ⚠️ 72% |
| `onu_eth_ports` | ⚠️ 55% | ⚠️ 67% | ⚠️ 73% |
| `onu_native_vlan` | ⚠️ 64% | ⚠️ 73% | ⚠️ 79% |
| `onu_user_vlan` | ⚠️ 58% | ⚠️ 70% | ⚠️ 61% |
| `gem_tcont` | ⚠️ 62% | ⚠️ 77% | ⚠️ 71% |
| `dba_profile` | ⚠️ 83% | ✅ 92% | ⚠️ 83% |
| `traffic_profile` | ⚠️ 59% | ⚠️ 74% | ⚠️ 56% |
| `line_profile` | ⚠️ 63% | ⚠️ 81% | ⚠️ 75% |
| `service_profile` | ⚠️ 78% | ⚠️ 84% | ⚠️ 78% |
| `service_port` | ⚠️ 64% | ⚠️ 79% | ⚠️ 79% |
| `multicast_igmp` | ❌ 24% | ❌ 24% | ❌ 24% |
| `multicast_gem` | ❌ 20% | ❌ 20% | ❌ 20% |
| `wan_profile` | ❌ 16% | ❌ 37% | ❌ 16% |
| `pppoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `ipoe_session` | ❌ 12% | ❌ 12% | ❌ 12% |
| `policy_route` | ❌ 12% | ❌ 30% | ❌ 12% |
| `snmp` | ⚠️ 46% | ⚠️ 49% | ⚠️ 49% |
| `ssh_cipher_detail` | ❌ 40% | ❌ 40% | ❌ 40% |
| `aaa_radius` | ⚠️ 66% | ⚠️ 45% | ⚠️ 45% |
| `users` | ⚠️ 47% | ❌ 41% | ❌ 38% |
| `qos_attachment` | ❌ 39% | ❌ 33% | ❌ 33% |
| `omci_provisioning` | ⚠️ 76% | ✅ 91% | ✅ 85% |
| `stb_ports` | ❌ 16% | ❌ 16% | ❌ 16% |
| `ssid_binding` | ❌ 12% | ❌ 12% | ❌ 12% |


Legenda: ✅ FULL (≥85%) · ⚠️ PARTIAL (45-84%) · ❌ NONE (1-44%) · 🚫 UNSUPPORTED (0%)

Número ao lado do badge = `semantic_fidelity_score` calculado como média ponderada (parser 30% + renderer 30% + equivalência 40%).