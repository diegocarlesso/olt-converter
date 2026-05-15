# Technical Audit (2026-05-15)

## 1) Arquitetura atual mapeada
- Estrutura principal já contém `parsers/`, `renderers/`, `models/`, `services/`, `templates/`, `api`.
- Ausências: camada explícita `compatibility/` e `validators/` dedicadas no padrão requerido (existia em `services/*`).

## 2) Acoplamentos vendor-specific
- Alto acoplamento em parsers específicos extensos em `backend/app/parsers/*/*/parser.py`.
- Modelo universal já coexistia com semântica, porém misturado a entidades legadas e serviços.

## 3) Parsers monolíticos
- `backend/app/parsers/fiberhome/an5516/parser.py` é parser grande e centralizado.

## 4) Lógica em templates
- Templates existentes têm baixo-médio acoplamento sintático por vendor (esperado), sem validação de negócio detectada na auditoria rápida.

## 5) Ausência de normalização
- Parcial: já havia `unified_model.py`; faltava um núcleo mínimo e explícito para etapas prioritárias pedidas.

## 6) Gaps de testes
- Existia apenas `backend/smoke_test.py`.
- Não havia suíte organizada `tests/parsers`, `tests/renderers`, `tests/validators`, `tests/roundtrip`.

## 7) Priorização
1. Consolidar núcleo universal explícito (feito).
2. Padronizar parser base mínimo `detect()/parse()` (feito).
3. Modularizar parser Fiberhome por domínio (feito, versão mínima).
4. Criar compatibility e validation engines dedicados (feito, baseline).
5. Ampliar fixtures reais e cobertura multi-firmware (pendente).

## Débitos técnicos
- Integrar novo núcleo com pipeline legado sem duplicação de modelos.
- Expandir parser Fiberhome para sintaxes reais adicionais.
- Evoluir renderer Huawei para cobertura completa (DBA/TCONT/GEM).
- Enriquecer roundtrip com reparse do destino.

## Riscos estruturais restantes
- Coexistência de modelo legado e novo núcleo pode causar divergência sem governança.
- Renderer baseline pode perder semântica avançada até cobrir perfis completos.
- Matrix de compatibilidade ainda enxuta para enterprise-grade.
