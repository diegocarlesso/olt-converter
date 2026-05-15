# Relatório de Fidelidade — *expected* (manual + traces)

> Este documento é a **projeção esperada** do que `fidelity_report.py` deve
> produzir contra os backups em `modelos-config/`. É baseado na leitura
> manual dos arquivos reais que estão acessíveis ao Cowork e na lógica
> codificada nos parsers, na engine de inferência e na síntese de profiles.
>
> Para gerar o relatório real:
> ```cmd
> cd olt-converter/backend
> .venv\Scripts\activate
> python fidelity_report.py
> ```
> O arquivo gerado em `docs/FIDELITY_REPORT.md` é a **verdade absoluta**;
> este aqui é uma referência informada para você antecipar o que esperar e
> avaliar a fundação antes de o frontend ser construído.

---

## 1. Sumário esperado por arquivo

| Arquivo                          | Vendor    | Linhas (~) | Cobertura est. | ONUs est. | SPs (inferidos) | Issues |
|----------------------------------|-----------|------------|----------------|-----------|-----------------|--------|
| `BACKUP-FIBERHOME.txt`           | Fiberhome | ~1800      | 88-92%         | 719       | ~3-50 com baixa conf | ~700 info, 24 warn |
| `OLT-ZTE-CRISTAL.txt`            | ZTE       | ~700       | 95%            | ~150      | conforme backup | poucos warn |
| `OLT-ZTE-ITABAIANA.txt`          | ZTE       | ~600       | 95%            | ~120      | conforme backup | poucos warn |
| `OLT-ZTE-MUCURICI.txt`           | ZTE       | ~400       | 95%            | ~80       | conforme backup | poucos warn |
| `ETA-LOJA-ZTE-OLT01.txt`         | ZTE       | ~200       | 96%            | ~10       | conforme backup | OK |
| `MG-GVS-OLT-BRAIPE.txt`          | Huawei    | ~3000      | 92%            | ~200      | extraídos diretamente | médios warn |
| `MG-GVS-OLT-MARIANA-X7.txt`      | Huawei    | ~2800      | 92%            | ~180      | extraídos diretamente | médios warn |
| `OLT-NOVA-BRAIPE.txt`            | Huawei    | ~2500      | 90%            | ~160      | extraídos diretamente | médios warn |
| `OLT HUAWEI PROFILES.txt`        | Huawei    | ~400       | 95%            | 0         | 0 (só profiles)        | OK |
| `OLT SERVICOS.txt`               | Huawei    | ~250       | 80%            | 0         | 0                      | warn de profiles |
| `PROVISIONAR_ONU.txt`            | ZTE       | ~20        | 100%           | 1         | 1                      | OK |
| `Script_OLT_Huawei.txt`          | Huawei    | ~150       | 50%            | 0         | 0                      | muitos unparsed |
| `SCRIPT-GER-OLT.txt`             | Huawei    | ~200       | 30%            | 0         | 0                      | placeholders `[SLOT]` |

---

## 2. Análise detalhada: `BACKUP-FIBERHOME.txt`

### 2.1 Entidades extraídas

```
hostname             : "ngpon olt"
vendor               : fiberhome
firmware             : WOS
model                : AN5516

boards               : 8
vlans                : ~2080
service_vlans        : ~180
uplinks              : 12
pons                 : ~9
onus                 : 719
service_ports        : ~3-50 (inferidos com baixa confiança — ver §2.2)
dba_profiles         : ~2-3 sintetizados (DBA-SYNTH-IPTV, DBA-SYNTH-MGMT, …)
traffic_profiles     : ~2-3 sintetizados (TT-SYNTH-IPTV, TT-SYNTH-MGMT)
line_profiles        : 0
service_profiles     : 3 (gerados a partir dos cs onu profile)
onu_type_profiles    : 3 (HG6145D2, HG6145F3, HG6145D2_2)
users                : 2 (ponroot, GEPON) com hashes
radius_servers       : 1 (10.10.10.10)
mgmt_vlan            : 4000 GERENCIA com IP 10.16.39.2/24
static_routes        : 1
qos_attachments      : ~16
```

### 2.2 Service-Ports inferidos

A engine `infer_service_ports` tenta os sinais S1-S5 para cada uma das 719
ONUs. Sinais disponíveis nesse backup:

| Sinal | Disponível? | Por quê |
|-------|:-----------:|---------|
| S1 onu.native_vlan | ❌ | Fiberhome WOS não declara native_vlan na ONU |
| S2 line-profile.mappers | ❌ | LineProfile vazio nesse backup |
| S3 service-profile.port_vlan_translations | ❌ | Os cs profiles não têm translations |
| S4 onu_type ↔ service_vlan name | ⚠️ | Match parcial para HG6145E ↔ "PPPOE_LOGA_RBX"? |
| S5 PON inteira → única service-vlan | ⚠️ | PONs misturam HG6145* e 5506-* |

**Resultado esperado**: a vasta maioria das 719 ONUs ficará SEM service-port
inferido — `parse_warnings` vai listar isso. O operador precisará usar
**multi-file import** (POST `/api/v1/merge`) trazendo um dump de
`gpononu add servport ...` para completar.

Bucket de confidence esperado:
```
high       :  0
medium     :  0-5    (raros casos onde S4 dispara forte)
low        :  5-30
very-low   :  20-50
fallback   :  0
```

### 2.3 DBA / Traffic sintetizados

A engine `synthesize_dba_profiles` vasculha os nomes de service-vlans buscando
tier patterns. Dos ~180 service-vlans, esperamos matches em:

- "TV_LOGA" → **DBA-SYNTH-IPTV** (102 Mbps, type3 assured 50%)
- "GERENCIA" → **DBA-SYNTH-MGMT** (10 Mbps, type3 assured 50%)
- "CLIENTES_PPPOE", "PPPOE_RADIO_*", "PPPOE_FTTH_*" → não batem com tier patterns
  (nome PPPoE genérico, sem indicação de velocidade) → ficam sem DBA específico.

Não temos service-vlans com "1G", "500M", etc. no nome (não é a convenção
desse operador). Resultado: provavelmente 2 DBAs sintetizados.

⚠️ **GAP-2 ainda existe**: para ONUs PPPoE residenciais, vamos cair no
DBA-DEFAULT (`Provenance.default_fallback`, conf=0.15, `needs_review=True`).

### 2.4 Conversões cruzadas esperadas

#### Fiberhome → Huawei

```
boards          → board add 0/1 gc8b ... × 8
vlans (~2080)   → vlan N smart × ~2080
service_vlans   → não emitido (conceito Fiberhome; o equivalente são
                  service-ports multi-service que só aparecem se inferência
                  bater)
onu_types       → ont-srvprofile gpon profile-id N profile-name "HG6145D2"
                  + ont-port pots 1 eth 4 wifi 2
                  + commit + quit
onus (719)      → ont add 1 5 26 sn-auth "FHTT04C6BA10" omci
                    ont-lineprofile-id 10 ont-srvprofile-id 1
                  × 719
mgmt vlan       → interface vlanif 4000 / ip address 10.16.39.2 255.255.255.0
service_ports   → ~3-50 linhas (poucas inferidas com conf > 0.5)
```

**Perda semântica**: 
1. ~669+ ONUs sem service-port — operador precisa preencher manualmente no
   editor ou via complementary import.
2. Os cs onu profile (HG6145D2 etc.) viram ont-srvprofile mas o `eid` 
   original é descartado pelo modelo (não temos esse campo).

#### Fiberhome → ZTE

```
mgmt vlan       → interface vlan 4000 / ip address ...
vlans           → vlan N / name ... / $   × ~2080
boards          → não emitido (ZTE não tem `board add` literal — fica info)
onus            → interface gpon SLOT/PON / onu N / serial-number ...
                  / service-profile X line-profile Y
service_ports   → idem Huawei (poucos inferidos)
```

**Perda semântica adicional ZTE**:
1. ONU id > 127 vira warning explícito; o renderer emite mesmo assim, mas
   ZTE C600 não aceita (GPON padrão).
2. Cs onu profile não tem equivalente direto em ZTE — viram `gpon-onu profile
   service-profile NAME` placeholder.

### 2.5 Validação esperada

```
errors    : 0 (parser não emite errors, só warnings)
warnings  : ~24 VLAN_DUPLICATED + ~5-10 ONU_ID_ABOVE_GPON_STANDARD
info      : ~700+ ONU_LINE_PROFILE_MISSING (ONUs com type 5506-*, HG6145E
            etc. que não têm cs profile declarado nesse backup)
```

---

## 3. Análise: backups Huawei (`MG-GVS-OLT-BRAIPE.txt` e similares)

Cobertura esperada **alta** (90-92%). O parser Huawei MA5800 cobre tudo que
aparece nesses backups:

- 6-15 DBA profiles literais
- 3 traffic-tables (SMARTOLT-VOIPMNG-10M, SMARTOLT-1G-UP, SMARTOLT-1G-DOWN)
- ~50-60 ont-srvprofile gpon (HG8010H, NOKIA-G-140W-H, ZTE-F668, Generic_1_V100..V290…)
  - Cada um com `ont-port pots adaptive 32 eth adaptive 8 catv adaptive 8`
  - Várias com port-vlan translations
- ~15-20 ont-lineprofile gpon
- ~3 ont wan-profile (smartolt, GERENCIA_ONU)
- ~1 ont policy-route-profile (smartolt)
- ONUs via `ont add 0 0 sn-auth "..." omci ont-lineprofile-id 10 ont-srvprofile-id 1`
  preservando descrição
- Service-ports completos via `service-port N vlan X gpon 0/x/y ont z gemport z multi-service user-vlan W`

**Conversão Huawei → ZTE**: razoavelmente fiel. As ONUs com id > 127 (raras
em GPON padrão MA5800-V100R021) gerarão warning.

**Conversão Huawei → Fiberhome**: a maior parte do conhecimento sobre cs
onu profile / ONU types específicos do Fiberhome é PERDIDA — as ONUs
Huawei viram entradas `set white phy addr` simples; o operador precisa
adicionar cs onu profile manualmente.

### Exemplo concreto: ONU de `MG-GVS-OLT-BRAIPE.txt`

#### Origem (Huawei)
```
ont-srvprofile gpon profile-id 7 profile-name "Generic_1_V201"
 ont-port pots adaptive 32 eth adaptive 8 catv adaptive 8
 port vlan eth 1 translation 201 user-vlan 201
 port vlan eth 2 translation 201 user-vlan 201
 commit
ont add 0 0 sn-auth "HWTC11111111" omci ont-lineprofile-id 10 ont-srvprofile-id 7
service-port 1 vlan 201 gpon 0/1/0 ont 0 gemport 1 multi-service user-vlan 201
```

#### Renderizado para ZTE
```
gpon-onu profile service-profile Generic_1_V201
  port-config eth 8
  vlan-translate eth 1 translation 201 user-vlan 201
  vlan-translate eth 2 translation 201 user-vlan 201
$
interface gpon_olt-0/1
  no shutdown
$
interface gpon 0/1
 onu 0 type ALL_CAPABILITY sn HWTC11111111
 onu 0
  serial-number HWTC11111111
  service-profile Generic_1_V201 line-profile Generic_1_V201
 !
$
service-port 1 gpon 0/1 onu 0 gem 1 match vlan vlan-id 201 action vlan replace vlan-id 201 user-vlan vlan-id 201
```

#### Renderizado para Fiberhome
```
add cs onu profile name Generic_1_V201 onutype 7 pontype 712 onucapa 0 lan1g 8 lan10g 0 pots 32
set white phy addr HWTC11111111 pas null ac add sl 0 p 1 o 0 ty Generic_1_V201
create service_vlan 201
set service_vlan 201 Generic_1_V201 type data
set service_vlan 201 vlan_begin 201 vlan_end 201
```

---

## 4. Análise: backups ZTE

`OLT-ZTE-CRISTAL.txt`, `OLT-ZTE-ITABAIANA.txt`, `OLT-ZTE-MUCURICI.txt`:

- `!<if-intf>` declara interfaces gei/xgei/gpon_olt-/gpon_onu- — todas
  capturadas.
- ONUs declaradas no bloco `interface gpon_onu-X/Y/Z:N` mas SEM bloco de
  provisionamento → ficam com `serial_number=None`. O `PROVISIONAR_ONU.txt`
  complementa via `gpon X/Y/Z / onu N / serial-number ZTEG... / service-profile / line-profile`.
  → caso de **multi-file import**!

### Exemplo de complementary import

```python
from app.services.merger import merge_configs

cfg1 = parse_config(open("OLT-ZTE-CRISTAL.txt").read()).config
cfg2 = parse_config(open("PROVISIONAR_ONU.txt").read()).config
merged = merge_configs([cfg1, cfg2], ["OLT-ZTE-CRISTAL.txt", "PROVISIONAR_ONU.txt"])

# ONU 1/1/2:0 que estava no CRISTAL como placeholder agora tem
# serial=ZTEGD70EF916, service_profile=SP-PPPOE, line_profile=LP-PPPOE
# e origin_files=["OLT-ZTE-CRISTAL.txt", "PROVISIONAR_ONU.txt"]
```

---

## 5. Gaps remanescentes (precisam decisão antes do frontend)

### 5.1 GAP-3: Equivalência ONU type ↔ Huawei profile id

Hoje, ao converter Fiberhome → Huawei, mapeamos `cs onu profile`
(HG6145D2, type_id=10000) para `ont-srvprofile gpon profile-id 10000`. Mas
Huawei MA5800 usa profile IDs **pequenos** (1-99 típicos). IDs 10000 podem
ser rejeitados pelo CLI.

**Solução proposta**: na engine de equivalence, remapear IDs altos para
`max(existing_id)+1` quando convertendo para Huawei, mantendo `name`
estável. Implementar.

### 5.2 GAP-4: ONU.eth_ports não populado por Fiberhome

Hoje o parser Fiberhome WOS não captura ethernet port config por ONU. Está
implícito no cs onu profile (lan1g=4 etc.). Quando renderizar para Huawei
ou ZTE, geramos uma porta `eth 1` default com native vlan = service-vlan
inferida. Para PoE / multi-porta isto é insuficiente.

**Solução**: derivar `EthernetPort` por ONU a partir do cs profile e do
service-port inferido — gera N portas = lan1g, todas com mesma native vlan.

### 5.3 GAP-5: Multicast / IGMP não capturado

Nenhum dos backups reais tem comandos de multicast detalhados. Quando
aparecerem, precisamos:
- Capturar `igmp snooping enable` (Huawei)
- Capturar `multicast-vlan X` 
- Popular `MulticastConfig`

Não bloqueante hoje, mas listado para roadmap.

### 5.4 GAP-6: PPPoE/IPoE sessions

Backups reais não trazem PPPoE/IPoE sessions; isso é Radius-driven em
runtime. Não modelar como entidade primária por enquanto.

---

## 6. Próximas decisões do operador

Antes do frontend, recomendado:

1. **Rodar `python fidelity_report.py`** localmente para confirmar números
   reais vs estimativas deste documento.
2. **Decidir sobre GAP-3** (remapeamento de IDs altos para Huawei). Sugiro:
   sim — implementar na próxima iteração.
3. **Decidir sobre GAP-4** (derivar eth_ports do cs profile). Sugiro: sim —
   bloqueia Huawei útil senão.
4. **Aprovar a estratégia de inferência S1-S5** ou pedir sinais adicionais.
5. **Considerar dump complementar** para os backups Fiberhome (gpononu
   servport runtime) para fechar o GAP-1.

Quando esses 4 pontos estiverem confirmados, a fundação está **operacionalmente
sólida** o suficiente para o editor visual.

---

## 7. Como conferir você mesmo

```cmd
cd "E:\OLT CONFIG CONVERTER ENGINE\OLT CONFIG CONVERTER ENGINE\olt-converter\backend"
.venv\Scripts\activate
python fidelity_report.py
```

Vai gerar `docs/FIDELITY_REPORT.md` com números reais. Compare-o com este
documento para validar se a fundação está dentro do esperado.

Para multi-file import específico do GAP-1:
```cmd
curl -X POST http://localhost:8000/api/v1/merge ^
  -F "files=@BACKUP-FIBERHOME.txt" ^
  -F "files=@dump-servport.txt"
```
