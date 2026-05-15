# Classificação Operacional dos Gaps — Fidelity Layers

> Cada gap classificado em 5 dimensões de risco operacional. Esta tabela é a
> *prioridade real* para a evolução do pipeline antes do editor visual ser
> implementado.

Dimensões avaliadas:

| Eixo | O que mede |
|------|------------|
| **Impacto Operacional** (IO) | Quão visível é o problema para o operador no dia-a-dia (1=transparente, 5=quebra serviço) |
| **Perda Semântica** (PS) | Risco de informação ser silenciosamente descartada (1=zero, 5=alta) |
| **Render Inválido** (RI) | Probabilidade do CLI emitido ser rejeitado pelo vendor destino (1=zero, 5=alta) |
| **Provisionamento Incorreto** (PI) | Probabilidade do CLI ser aceito mas configurar errado (1=zero, 5=alta) |
| **Criticidade GPON** (CG) | Quão central é o conceito para um serviço GPON real (1=acessório, 5=núcleo) |

---

## Resumo prioridade (ordem de ataque)

| Rank | Gap | IO | PS | RI | PI | CG | Score | Status atual |
|------|-----|:--:|:--:|:--:|:--:|:--:|:-----:|--------------|
| 1 | GAP-1 ONU↔ServiceVLAN binding (Fiberhome WOS) | 5 | 5 | 3 | 5 | 5 | **23** | ✅ Mitigado: inferência + multi-file + provenance |
| 2 | GAP-3 ID Remapping (cross-vendor) | 4 | 2 | 5 | 5 | 4 | **20** | ✅ Implementado: remapping engine + policies + dry-run |
| 3 | GAP-2 DBA/Traffic ausentes (Fiberhome WOS) | 4 | 4 | 2 | 4 | 5 | **19** | ✅ Mitigado: synthesis engine + tier patterns |
| 4 | GAP-4 ONU.eth_ports (UNI semantics) | 4 | 4 | 2 | 4 | 5 | **19** | ⚠️ Foundation: precisa derivação automática |
| 5 | GAP-5 Multicast / IPTV / IGMP | 3 | 3 | 2 | 4 | 4 | **16** | ⚠️ Modelo existe, parsers não populam |
| 6 | GAP-6 Sessions (PPPoE/IPoE/WAN) | 3 | 2 | 1 | 3 | 3 | **12** | ⚠️ Modelo existe, parsers não populam |
| 7 | GAP-7 SSH ciphers detail | 1 | 2 | 1 | 2 | 1 | **7** | ❌ Não-prioritário, postpor |
| 8 | GAP-8 Fiberhome AN6000 parser | 4 | 3 | 3 | 4 | 3 | **17** | ❌ Não-prioritário (aguarda exemplo real) |

**Score = soma dos 5 eixos.** Quanto maior, mais urgente. Status:
✅ Implementado · ⚠️ Em andamento · ❌ Pendente

---

## GAP-1 — ONU↔ServiceVLAN binding (Fiberhome WOS)

**Sintoma**: backups Fiberhome não declaram `service-port` no save; a relação
ONU→VLAN é runtime (`gpononu add servport ...`) e fica fora do backup
principal.

**Riscos**:
- Render Huawei sai sem `service-port multi-service user-vlan` → ONUs sobem
  sem serviço.
- Render ZTE sai sem `service-port ... action vlan replace ...` → idem.

**Mitigação atual** (✅ implementada):
1. Engine de inferência com 5 sinais (native vlan, GEM mappings,
   port-vlan-translation, name match, PON convergence). Cada binding inferido
   carrega Provenance(`source=INFERENCE`, `confidence`, `signals`).
2. Multi-file import: operador pode subir o dump de `gpononu servport` e o
   merger preserva proveniência por arquivo.
3. Validação cruzada do binding (service-port → ONU/VLAN/PON existem).

**O que falta**:
- UI para revisão dos bindings inferidos com confidence < 0.7
- Sinais S6+ adicionais (uplink VLAN membership convergente, bridge mode hint).

---

## GAP-2 — DBA / Traffic profiles ausentes (Fiberhome WOS)

**Sintoma**: o save WOS não tem `dba-profile add`; profiles são provisionados
em runtime via `gpononu add ttont`.

**Riscos**:
- Render Huawei sem DBA → MA5800 rejeita `ont add omci` referenciando
  `ont-lineprofile` sem T-CONT bound a DBA.
- Render ZTE sem `gpon-profile tcont` → similar.

**Mitigação atual** (✅ implementada):
1. Synthesis engine com 13 tier patterns (1G/500M/300M/200M/100M/50M/VOIP/
   IPTV/MGMT/CORP) match por nome de service-vlan.
2. DBA-DEFAULT fallback marcado como `Provenance.default_fallback`
   (confidence=0.15, `needs_review=True`).
3. Traffic profiles sintetizados a partir dos DBA (TT-SYNTH-*).

**O que falta**:
- Catálogo configurável por ISP (templates próprios).
- Aprendizado: lembrar mapeamentos aprovados pelo operador.

---

## GAP-3 — ID Remapping cross-vendor

**Sintoma**: Fiberhome usa ONU id 1..128. ZTE/Huawei GPON aceitam 0..127.
Profile ids em Huawei são pequenos (1..200); Fiberhome usa 10000+. VLAN
4093 é reservada em Huawei.

**Riscos**:
- ONU 128 enviada para ZTE → CLI rejeita.
- Profile id 10000 → Huawei rejeita.
- VLAN 4093 emitida → conflito com management interno Huawei.

**Mitigação atual** (✅ implementada):
1. `RemappingPolicy` por (vendor, model) com ranges e VLANs reservadas.
2. `remap_for(config, target)` determinístico, com collision avoidance,
   preserva todos bindings (atualiza service-ports referenciando a ONU).
3. Dry-run via `POST /api/v1/remap/dry-run` — retorna tabela `old_id→new_id`
   por categoria sem aplicar.
4. Provenance: cada ID remapeado anota `reason` na entidade afetada
   (`needs_review=True`).

**O que falta**:
- UI mostrando a tabela antes de confirmar o convert.
- Política configurável (operador pode preferir manter ID 128 e abortar
  conversão).

---

## GAP-4 — UNI / Ethernet ports semantics

**Sintoma**: `ONU.eth_ports` está modelado mas só ZTE C600 popula (do bloco
`ethernet N`). Fiberhome WOS e Huawei não emitem essa info por porta.

**Riscos**:
- Render Huawei → ZTE: portas que tinham native_vlan distinta no Huawei
  (via service-port multi-service) podem ser geradas com mesmo native em
  todas as ethX no ZTE.
- Render Fiberhome → Huawei: `lan1g=4` no cs profile gera 4 portas eth
  iguais; mas operador pode querer VLAN distinta por porta (TV/Internet/VoIP).

**Mitigação proposta** (⚠️ a fazer):
1. Derivar `EthernetPort` por ONU a partir de:
   - `cs onu profile.lan1g` (Fiberhome)
   - `ont-srvprofile.ont-port eth N` (Huawei)
   - `service-port.user_vlan` (Huawei multi-service)
2. Modelo expandido com:
   - `tagged_vlans: list[int]`
   - `untagged_vlans: list[int]`
   - `vlan_isolation: bool`
   - `bridge_group: int`
   - `wan_binding: str` (nome do WAN profile)
   - `ssid_binding: str` (id do SSID)
   - `uni_behavior: enum {bridge | router | mixed}`
3. Renderers respeitam.

**Próximo passo**: implementar derivação automática + expandir modelo.

---

## GAP-5 — Multicast / IPTV / IGMP

**Sintoma**: o modelo tem `MulticastConfig`, `IGMPConfig` mas nenhum parser
popula ainda.

**Riscos**:
- Operador com IPTV verá multicast totalmente ausente após conversão.
- Falha silenciosa: validador não acusa porque a entidade simplesmente não
  existe.

**Mitigação proposta** (⚠️ a fazer):
1. Expandir `MulticastConfig` com:
   - `mvlan` (multicast VLAN)
   - `igmp_profile_ref`
   - `multicast_gem_binding` (gem dedicado ao multicast)
   - `stb_ports: list[int]` (portas Ethernet UNI dedicadas a STB)
   - `fast_leave: bool`
2. Capturar:
   - Huawei: `igmp snooping enable`, `igmp policy-profile`, `multicast-vlan`
   - Fiberhome: `set multicast`, `gpononu add mcastservice`
3. Validar binding: stb_port ⊂ ONU.eth_ports.
4. Emitir warning se IPTV service-vlan detectada mas sem MulticastConfig.

---

## GAP-6 — Session semantics (PPPoE/IPoE/WAN bindings)

**Sintoma**: modelos `PPPoESession`, `IPoESession`, `WANProfile` existem;
apenas Huawei popula `WANProfile` parcialmente. PPPoE/IPoE sessions raramente
aparecem em saves (são runtime via RADIUS).

**Riscos**:
- ONUs em router mode (NAT habilitado, WAN profile) perdem configuração no
  destino.
- Policy-route profiles desaparecem.

**Mitigação proposta** (⚠️ a fazer):
1. Expandir `WANProfile`:
   - `mode: enum {bridge | router | mixed}`
   - `nat_enabled`, `dhcp_enabled`, `pppoe_enabled`
   - `vlan_id`
   - `policy_route_profile_ref`
   - `subscriber_metadata: dict` (campos opcionais para RADIUS)
2. Binding ONU↔WANProfile por nome.
3. Render ZTE: vincula via line-profile + service-profile customizado.
4. Render Fiberhome: gera `ont wan-profile` no AN6000 (não no AN5516 WOS).

---

## GAP-7 — SSH ciphers / MAC / KEX

**Sintoma**: `SSHConfig` tem campos `ciphers`, `macs`, `key_exchanges` mas
parser Huawei não captura `ssh server cipher ...` (cai em noise).

**Riscos**:
- Conformidade de segurança: operador que padronizou ciphers seguros perde
  a config.

**Postponed**: prioridade baixa, postpor para depois do editor.

---

## GAP-8 — Fiberhome AN6000 (sintaxe nova)

**Sintoma**: AN6000 usa sintaxe estilo Huawei (`ont add`, `ont-srvprofile`,
`dba-profile add`). Parser Fiberhome atual cobre só WOS (AN5516).

**Mitigação proposta** (⚠️ depende de exemplo real):
- Criar `app/parsers/fiberhome/an6000/parser.py` com signatures distintas:
  - `ont-srvprofile gpon profile-id ...` presente
  - `set service_vlan` ausente
- Detecção automática direciona para o parser correto via
  `firmware.pick_variant`.

**Aguardando**: exemplo real de backup AN6000 para implementar com qualidade.

---

## Resumo das ações para "Fidelity Layers"

| Camada | O que entrega | Status |
|--------|---------------|:------:|
| L1 — Proveniência | Toda entidade rastreável (source/confidence/signals/origin) | ✅ |
| L2 — Inferência multi-sinal | Bindings ONU↔VLAN com confidence | ✅ |
| L3 — Síntese controlada | DBA/Traffic profiles sintéticos com fallback explícito | ✅ |
| L4 — Equivalência semântica | Adaptação cross-vendor preservando significado | ✅ |
| L5 — ID Remapping | Determinístico + dry-run + collision avoidance | ✅ |
| L6 — Compatibility Matrix | Fidelidade mensurada feature×vendor×direção | ✅ |
| L7 — Validação cruzada | Bindings, ranges, refs, duplicatas | ✅ |
| L8 — Multi-file merge | Combina múltiplos arquivos com proveniência | ✅ |
| **L9 — UNI semantics** | Ethernet ports detalhadas | ⚠️ Próximo |
| **L10 — Multicast** | IPTV/IGMP/MVLAN/STB | ⚠️ Próximo |
| **L11 — Session/WAN** | PPPoE/IPoE/router mode | ⚠️ Próximo |
| L12 — Editor visual | UI consumindo o modelo já estabilizado | ❌ Aguardando |

A meta é cravar L9-L11 antes do frontend para que ele já nasça mostrando
todas as facetas operacionais.
