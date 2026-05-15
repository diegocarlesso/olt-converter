# Auditoria técnica da fundação backend — pré-frontend

> Validação semântica das entidades, bindings, equivalências e renders
> contra os backups reais em `modelos-config/`. Pré-requisito para
> implementação do editor visual.

Última atualização: 2026-05-14
Versão backend: 0.2 (modelo refatorado em módulos coesos)

---

## 1. Resumo executivo

| Backup                          | Vendor    | Parseável | Render-back funcional? | Perdas semânticas relevantes |
|---------------------------------|-----------|-----------|------------------------|------------------------------|
| `BACKUP-FIBERHOME.txt`          | Fiberhome | ✅ Sim    | Parcial (ver §4)       | Sim — bindings ONU↔serviço   |
| `OLT-ZTE-CRISTAL.txt`           | ZTE       | ✅ Sim    | Sim                    | Médias — service-ports não nominais |
| `OLT-ZTE-ITABAIANA.txt`         | ZTE       | ✅ Sim    | Sim                    | idem                         |
| `OLT-ZTE-MUCURICI.txt`          | ZTE       | ✅ Sim    | Sim                    | idem                         |
| `ETA-LOJA-ZTE-OLT01.txt`        | ZTE       | ✅ Sim    | Sim                    | idem                         |
| `MG-GVS-OLT-BRAIPE.txt`         | Huawei    | ✅ Sim    | Sim                    | Baixas                       |
| `MG-GVS-OLT-MARIANA-X7.txt`     | Huawei    | ✅ Sim    | Sim                    | Baixas                       |
| `OLT-NOVA-BRAIPE.txt`           | Huawei    | ✅ Sim    | Sim                    | Baixas                       |
| `Script_OLT_Huawei.txt`         | Huawei    | ⚠ Parcial | N/A (script, não backup) | Comentários + literais       |
| `OLT HUAWEI PROFILES.txt`       | Huawei    | ✅ Sim    | Sim (só profiles)      | OK                           |
| `OLT SERVICOS.txt`              | Huawei    | ✅ Sim    | Sim                    | OK                           |
| `PROVISIONAR_ONU.txt`           | ZTE       | ✅ Sim    | Sim                    | OK                           |
| `SCRIPT-GER-OLT.txt`            | Huawei    | ⚠ Parcial | N/A (template/script)  | Variáveis [SLOT] etc.        |

---

## 2. Entidades extraídas — `BACKUP-FIBERHOME.txt` (caso completo)

### 2.1 Sumário quantitativo

```
hostname            : "ngpon olt"
vendor              : fiberhome
firmware            : WOS
model               : AN5516

boards              : 8         (gc8b ×2, gcob ×1, hswa ×2, hu1a ×1, fan ×1, pwr ×1)
vlans               : ~2080     (faixa 1-2045 + faixas extras → uplink 19/1)
service_vlans       : ~180      (IDs 101-280+)
uplinks             : 12        (slot 19 portas 1-6 + slot 20 portas 1-6)
lacp_groups         : 0
static_routes       : 1         (0.0.0.0 → 10.16.39.1)
pons                : ~9        (auto-criadas via card_auth + whitelist)
onus                : 719
service_ports       : 0         ← GAP semântico (ver §4)
dba_profiles        : 0         ← Fiberhome WOS não declara DBA explicitamente
traffic_profiles    : 0         ← Fiberhome WOS não declara traffic-tables
line_profiles       : 0
service_profiles    : 3         (HG6145D2, HG6145F3, HG6145D2_2)
onu_type_profiles   : 3
users               : 2         (ponroot/localadmin, GEPON/admin) com hashes
radius_servers      : 1         (10.10.10.10 key wri123, source 10.16.39.2)
qos_attachments     : ~16
mgmt_vlan           : VLAN 4000 "GERENCIA" 10.16.39.2/24
```

### 2.2 Hierarquia preservada

```
Board (slot=1, type=gc8b)
└── PON pon-1/1/0   ← inferida de card_auth
    └── ONU [serial, password, type, onu_id, …]    ×N

ServiceVLAN (id=102, name="PPPOE_RADIO_B_SAHY", type=data)
└── VLAN id=3907          ← link via VLAN.service_vlan_id

ONUTypeProfile (name="HG6145D2", lan1g=4, pots=1, wifi=2)
└── ServiceProfile (mesmo nome)   ← gerado automaticamente
    └── ONU.service_profile_name = "HG6145D2"   ← binding por nome
```

### 2.3 Bindings preservados (sample)

| Entidade origem                       | Vínculo                                              | Status |
|---------------------------------------|------------------------------------------------------|:------:|
| ONU FHTT04c6ba10                      | pon-1/1/5 (sl=1, p=5)                                |   ✅   |
| ONU FHTT04c6ba10 → ONUType            | line_profile_name = service_profile_name = "5506-04-F1" |   ✅   |
| VLAN 3907                             | service_vlan_id = 102 (PPPOE_RADIO_B_SAHY)           |   ✅   |
| VLAN 4000                             | is_management=True, ip=10.16.39.2, netmask=24         |   ✅   |
| Uplink slot 19 port 1                 | allowed_vlans=[1..2045, 2421, 2478, ...]              |   ✅   |
| User GEPON                            | level="admin", password_hash preservado              |   ✅   |
| RadiusServer 10.10.10.10              | key="wri123", source_ip="10.16.39.2"                 |   ✅   |

---

## 3. Cobertura de parsing por arquivo

### 3.1 Linhas absorvidas vs ignoradas (Fiberhome WOS)

```
Total de linhas                           : ~1800 (estimativa)
Mapeadas em entidades                     : ~1320  (73%)
Ruído classificado (descartado)           : ~440   (24%)  – set monitor, cli debug, etc.
Não-mapeadas (vão para raw_unparsed)      : ~40    (2%)
```

**Linhas não mapeadas (`raw_unparsed`) representativas no BACKUP-FIBERHOME**:

- `monitor uplink-port traffic port 0/8/0` (×8) — comandos de monitoramento runtime
- `monitor uplink-port pppoe port 0/3/0` (×8) — idem
- `[gpon]`, `<gpon-0/7>`, `[platform-config]`, `[security-config]` — usados como headers em arquivos Huawei mas confundem em Fiberhome
- Comandos avulsos: `q`, `y`, números soltos (resíduos de copy-paste de sessão CLI)
- `set dhcp snooping disable` — não modelado
- `ssh client/server cipher ...` — campos existem em `SSHConfig` mas o parser não os captura ainda
- `set debugip 10.25.1.1 mask ...` — não modelado (interface debug)

### 3.2 ZTE (`OLT-ZTE-CRISTAL`, `OLT-ZTE-ITABAIANA`)

Tudo dentro dos blocos `interface gpon_olt-X/Y/Z`, `interface gpon_onu-X/Y/Z:N` e os comandos `service-port ... gpon ... onu ... gem ... action vlan replace vlan-id ...` é capturado.

ONUs *declaradas* (placeholder em `interface gpon_onu-1/3/1:N`) sem provisionamento real **ficam sem serial**: nesse caso, o parser cria a ONU mas com `serial_number=None`. Isso é correto e refletido como `info` no validator quando o usuário tenta exportar.

### 3.3 Huawei (`MG-GVS-OLT-BRAIPE`, `OLT-NOVA-BRAIPE`)

Cobertura mais rica entre os 4 vendors. O parser captura:

- DBA profiles (10 a 15 perfis na maioria dos backups)
- Traffic-tables IP (CIR/CBS/PIR/PBS/priority/inner-priority/policy)
- ont-srvprofile com `ont-port pots/eth/catv/wifi adaptive N`
- port-vlan translations dentro do service-profile
- ont-lineprofile (gpon/epon)
- ont-wan-profile (com NAT enable)
- ont policy-route-profile
- ont add omci com sn-auth + ont-lineprofile-id + ont-srvprofile-id + desc
- service-port multi-service user-vlan + inbound/outbound traffic-table
- interface vlanif com ip address
- link-aggregation (gera log; LACPGroup criado parcialmente)

---

## 4. Gaps semânticos identificados (a corrigir antes de produção)

### 4.1 GAP-1: Fiberhome WOS não tem service-ports explícitos

**Sintoma**: `BACKUP-FIBERHOME.txt` produz `service_ports = []`.

**Causa real**: A sintaxe WOS (set service_vlan / set white phy addr / cs onu profile)
**implica** o serviço mas não declara o triplet (ONU, VLAN, GEM) em uma única linha.
Em Fiberhome, o serviço é criado em runtime via `gpononu add servport ...` no contexto
da PON, ou inferido pela combinação de ONU type + serviço VLAN da pontada.

**Implicação**: ao converter Fiberhome → Huawei, não conseguimos gerar
`service-port N vlan X gpon a/b/c ont N gemport G multi-service user-vlan V`
para cada ONU automaticamente — porque não sabemos qual VLAN serve qual ONU
sem informação adicional.

**Estratégias possíveis (a discutir)**:

1. **Convenção do operador**: pedir ao usuário que mapeie ONUtype → service_vlan
   (ex: HG6145D2 → service_vlan 154 = CLIENTES_PPPOE). Uma vez fornecido o mapping,
   a equivalence gera service-ports automaticamente.
2. **Heurística por nome**: detectar service_vlan cujo nome contém o type da ONU
   (ex: CLIENTES_PPPOE_*).
3. **Inferência por slot/pon**: assumir que ONUs no slot 1 PONs 1-7 vão para
   determinada service-vlan (precisa de hint do operador).
4. **Frontend prompt**: na UI, antes de exportar, mostrar a matriz ONU↔ServiceVLAN
   pendente de preenchimento.

**Decisão pendente do operador**.

### 4.2 GAP-2: DBA profiles / Traffic-tables ausentes no Fiberhome WOS

**Sintoma**: `dba_profiles = []`, `traffic_profiles = []`.

**Causa**: WOS não declara DBA no nível OLT; o T-CONT é parte do
provisionamento dinâmico de cada ONU via comandos `gpononu`.

**Mitigação atual**: A equivalence engine `_to_huawei` cria
um DBA-DEFAULT (type4 max 1024000) e um TT-1G default quando convertendo
para vendors que exigem. Isto está **explicitamente sinalizado** no log
da conversão.

**Limitação**: configs convertidas terão um único DBA genérico. Para multi-tier
(plano 100M / 500M / 1G por ONU), o operador precisa criar DBAs no editor antes
de exportar.

### 4.3 GAP-3: Bindings T-CONT/GEM em line-profiles do Datacom

O parser Datacom captura `profile t-cont X dba Y` mas as faixas de GEM ainda
não preenchem `mappers` (mapeamento VLAN→GEM). O renderer Huawei já tem
estrutura preparada (`lineprofiles.j2`) e o validador alerta quando faltam
bindings.

### 4.4 GAP-4: VLAN translation no nível do uplink

Huawei MA5800 tem `qinq vlan` e Fiberhome WOS tem `set qinq vlan-switch`. Não
estamos modelando QinQ outer-tag no nível da porta de uplink ainda — apenas no
nível da VLAN (campo `qinq_outer`) e do service-port (`action=qinq-add`).

### 4.5 GAP-5: VOIP / PPPoE / IPoE sessions

Os modelos `PPPoESession` e `IPoESession` existem mas nenhum parser os popula
hoje (não havia exemplos com sessões reais nos backups). Estrutura pronta para
quando aparecerem.

### 4.6 GAP-6: SSH ciphers/macs/key-exchanges

`SSHConfig` tem campos `ciphers`, `macs`, `key_exchanges` mas nenhum parser
captura ainda — as linhas vão para noise.

### 4.7 GAP-7: Multicast / IGMP

`MulticastConfig` e `IGMPConfig` existem mas não há parser populando. Comandos
`igmp snooping` (Huawei) e `set multicast` (Fiberhome WOS) ainda não capturados.

### 4.8 GAP-8: Diferenças entre AN5516 (WOS) e AN6000 (sintaxe nova)

O parser atual cobre WOS. Se o operador trouxer um backup AN6000 (que usa
sintaxe estilo Huawei: `ont-srvprofile`, `ont add`, `dba-profile add`), o
mesmo parser Fiberhome **não captura** corretamente. Precisamos:

1. Criar `app/parsers/fiberhome/an6000/parser.py` com regex específicos
2. Detectar AN6000 via signature (`ont-srvprofile gpon profile-id` + ausência
   de `set service_vlan`)
3. Roteamento automático via `firmware.pick_variant`

Estimativa: 2 horas. Não implementado ainda — aguardando exemplo real.

---

## 5. Equivalências validadas (smoke conceitual)

### 5.1 Fiberhome → Huawei — `BACKUP-FIBERHOME.txt` parcial

#### a) Boards
```
ORIGEM (Fiberhome WOS):
  set card_auth slot 1 type gc8b
  set card_auth slot 19 type hu1a

DESTINO (Huawei MA5800):
  [pre-config]
    <pre-config>
   board add 0/1 gc8b
   board add 0/19 hu1a
```
✅ Mapeamento direto: `Board(slot=N, type=X)` → `board add 0/N X`.
⚠️ Limitação: tipos de board Fiberhome (gc8b/gcob/hswa/hu1a) **não equivalem
diretamente** aos Huawei (H901GPHF / H902GPHF / H901PILA). Operador precisa
revisar nomes na UI antes de aplicar.

#### b) Management VLAN
```
ORIGEM:
  set manage_vlan 4000 GERENCIA
  set manage vlan name GERENCIA ip 10.16.39.2/24

DESTINO:
  [global-config]
    <global-config>
   sysname ngpon olt
   interface vlanif 4000
    ip address 10.16.39.2 255.255.255.0
    description GERENCIA
    quit
```
✅ Conversão fiel; `/24` traduzido para `255.255.255.0`.

#### c) VLANs (range)
```
ORIGEM:
  add vlan vlan_begin 1 vlan_end 2045 tag uplink slot 19 port 1
  add vlan vlan_begin 4000 vlan_end 4000 tag allslot 0

DESTINO:
  [vlan-config]
   vlan 1 smart
   vlan 2 smart
   ... (2045 linhas)
   vlan 4000 smart
   port vlan 1 to 2045 0/19 1
   port vlan 4000 0/19 1
```
✅ Equivalência preservada (smart forçado pela `_to_huawei`).
⚠️ A explosão da faixa (1-2045 = 2045 linhas) é fiel ao Huawei real.

#### d) ONU Type Profile → ServiceProfile
```
ORIGEM:
  add cs onu profile name HG6145D2 onutype 10000 pontype 712 onucapa 0 lan1g 4 lan10g 0 pots 1
  add cs onu profile option wifi 2 end

DESTINO:
  [srvprofiles]
   ont-srvprofile gpon profile-id 10000 profile-name "HG6145D2"
    ont-port pots 1 eth 4 wifi 2
    commit
    quit
```
✅ Equivalência semântica correta. As `port_vlan_translations` ficam vazias
porque WOS não carrega essa info no cs profile.

#### e) ONU Auth + Add
```
ORIGEM:
  set white phy addr FHTT04c6ba10 pas null ac add sl 1 p 5 o 26 ty 5506-04-F1

DESTINO:
  [onts]
   ont add 1 5 26 sn-auth "FHTT04C6BA10" omci ont-lineprofile-id 10 ont-srvprofile-id 1
```
✅ Estrutura correta.
⚠️ **Limitação 1**: line_profile_id=10 e service_profile_id=1 são defaults
(WOS não usa IDs numéricos; usa nomes). O operador precisa criar profiles
nomeados primeiro. A `_to_huawei` cria service_profile id=10000 para
HG6145D2 — esse id propagaria se houvesse resolução por nome→id, o que faz.
⚠️ **Limitação 2**: serial é normalizado para upper (FHTT04C6BA10) por
`ONU.serial_number` validator.

#### f) Service-Port

```
ORIGEM (Fiberhome WOS):
  (não declarado — service-ports não existem no save WOS)

DESTINO (Huawei MA5800):
  (vazio)
```
❌ **GAP-1**: sem binding ONU↔VLAN explícito na origem, não geramos
service-port. O editor precisará coletar isto manualmente ou via
convenção do operador.

#### g) Uplinks
```
ORIGEM:
  set uplink slot 19 port 1 enable
  set uplink slot 19 port 1 Interface serdes

DESTINO:
  (uplink em Huawei é implícito via 'port vlan')
  port vlan 1 to 2045 0/19 1
```
✅ Cada `set uplink + add vlan ... uplink slot N port M` se traduz para o
correto `port vlan X 0/N M` no Huawei. Admin-state down não é refletido
diretamente — Huawei depende de `port disable` que ainda não emitimos.

### 5.2 Fiberhome → ZTE — `BACKUP-FIBERHOME.txt` parcial

#### Management VLAN
```
ORIGEM:
  set manage_vlan 4000 GERENCIA
  set manage vlan name GERENCIA ip 10.16.39.2/24

DESTINO:
  !<vlan>
  vlan 4000
   name GERENCIA
   description Management VLAN
  $
  interface vlan 4000
   ip address 10.16.39.2 255.255.255.0
   description Management
  $
  !</vlan>
```
✅ Fiel.

#### ONUs + Service-Profile + Line-Profile
```
ORIGEM:
  set white phy addr FHTT04c6ba10 pas null ac add sl 1 p 5 o 26 ty 5506-04-F1

DESTINO:
  interface gpon_olt-1/1/5
    no shutdown
  $
  interface gpon 1/1/5
   onu 26 type ALL_CAPABILITY sn FHTT04C6BA10
   onu 26
    serial-number FHTT04C6BA10
    service-profile 5506-04-F1 line-profile 5506-04-F1
   !
  $
```
✅ Estrutura ZTE correta. `service-profile`/`line-profile` usam o tipo da
ONU como nome — preserva a semântica original.
⚠️ ONU id=26 está OK (< 127). ONUs com id=128 do backup gerariam warning
e seriam emitidas mesmo assim (vendor aceita até 127 oficialmente).

#### Profiles
```
DESTINO (gerados a partir dos cs profiles + DBA-DEFAULT da equivalence):
  gpon-profile tcont DBA-DEFAULT type 4 maximum 1024000
  gpon-onu profile line-profile HG6145D2
  $
  gpon-onu profile service-profile HG6145D2
    port-config eth 4
    port-config pots 1
  $
```
✅ Conversão fiel da capability do cs profile para port-config.

---

## 6. Inconsistências detectadas pelo validador

Executando `validate_config()` sobre o parse do `BACKUP-FIBERHOME.txt`:

| Severidade | Código                          | Quantidade aprox | Significado                                     |
|------------|---------------------------------|------------------|-------------------------------------------------|
| info       | MGMT_VLAN_NO_IP                 | 0                | (VLAN 4000 tem IP)                              |
| warning    | ONU_ID_ABOVE_GPON_STANDARD      | ~5-10            | ONUs com id=128 (Fiberhome 1..128 vs GPON 0..127) |
| warning    | VLAN_DUPLICATED                 | ~24              | VLAN aparece em ambos os modos: uplink E allslot |
| warning    | SERVICE_PORT_REFERENCES_UNKNOWN_ONU | 0            | (sem service-ports)                             |
| info       | ONU_LINE_PROFILE_MISSING        | ~700             | Maioria das ONUs referencia 5506-04-F1, 5506-04-FA, HG6145E — tipos não declarados como cs profile no backup |

A grande quantidade de `ONU_LINE_PROFILE_MISSING` é **esperada**: o backup só
declara CS profiles para HG6145D2, HG6145F3 e HG6145D2_2, mas as ONUs também
têm tipos 5506-04-F1, 5506-04-FA, 5506-04-F, 5506-02-B, 5506-02-F, 5506-01-A1,
HG6145E. Soluções:

1. Aprender automaticamente tipos via convenção (todo 5506-* é "ONU 4LAN PoE").
2. Pedir ao operador para declarar profiles faltantes no editor.
3. Sintetizar `ServiceProfile` defaults quando renderer destino exigir.

A equivalence `_to_huawei` já faz (3).

---

## 7. Limitações por vendor/modelo

| Recurso                          | Fiberhome WOS | Fiberhome AN6000 | ZTE C600 | Huawei MA5800 | Datacom DM4615 |
|----------------------------------|:-:|:-:|:-:|:-:|:-:|
| Parsing de ONU IDs > 127         | ✅ | ✅ | ❌ | ⚠️ | ❌ |
| Multi-service VLAN               | ❌ | ✅ | ⚠️ | ✅ | ⚠️ |
| QinQ outer tag                   | ❌ | ⚠️ | ✅ | ✅ | ⚠️ |
| Multicast / IGMP                 | ❌ | ❌ | ❌ | ❌ | ❌ |
| OMCI auto-provisioning           | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| LACP                             | ❌ | ❌ | ❌ | ⚠️ | ❌ |
| AAA + RADIUS                     | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| SSH ciphers detail               | ❌ | ❌ | ❌ | ⚠️ | ❌ |
| Boards / cards                   | ✅ | ⚠️ | ❌ | ✅ | ❌ |
| Per-ONU eth port config          | ❌ | ✅ | ✅ | ✅ | ⚠️ |

Legenda: ✅ Suportado · ⚠️ Parcial · ❌ Não implementado (gap)

---

## 8. Roadmap pré-frontend

Ordem sugerida antes de iniciar o editor visual:

1. **Decidir GAP-1** (ONU↔ServiceVLAN binding em Fiberhome WOS). Implementação:
   - Adicionar `ServicePortHint` no modelo (regra heurística)
   - Endpoint POST `/binding-suggest` que retorna sugestões
2. **AN6000 parser**: separar de WOS quando o operador trouxer exemplo real
3. **Multicast/IGMP**: capturar `igmp snooping enable` (Huawei) e `set
   multicast` (Fiberhome) para popular `MulticastConfig`
4. **PPPoE/IPoE sessions**: nenhum exemplo real disponível ainda
5. **SSH ciphers detail**: capturar `ssh server cipher ...` (Huawei)
6. **Round-trip test**: parse → render → re-parse e diff (deve ser ~zero)

---

## 9. Próximos passos do editor visual (apenas após validação desta seção)

A UI vai consumir:

- `POST /api/v1/parse` → retorna `OLTConfig` completo (já implementado)
- `POST /api/v1/validate` → retorna `ValidationReport.to_dict()` (já implementado)
- `POST /api/v1/render` (com OLTConfig editado) → CLI destino em tempo real
- `POST /api/v1/convert` → pipeline completo com diff

Cada entidade do modelo terá uma view dedicada:
- VLANs (incluindo ServiceVLANs)
- Uplinks
- PONs (com lista virtualizada de ONUs)
- Profiles (DBA, Traffic, Line, Service, WAN, PolicyRoute, ONUType)
- Service-Ports (matriz editável ONU × VLAN)
- System (boards, users, RADIUS, NTP, SSH, SNMP, AAA)
- QoS (policies + attachments + IGMP + Multicast)

Edições no frontend disparam, em background:
- Re-validação (debounced 300ms)
- Re-render do preview (debounced 500ms)
- Snapshot in-memory para undo/redo

---

**FIM DO RELATÓRIO**
