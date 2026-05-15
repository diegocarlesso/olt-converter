# OLT Config Converter Engine

> Conversor profissional, modular e extensível de configurações de OLTs entre
> múltiplos vendors (Fiberhome, ZTE, Huawei, Datacom).

A arquitetura segue rigorosamente o princípio:

```
CONFIG ORIGEM  →  MODELO INTERNO PADRONIZADO (OLTConfig)  →  CONFIG DESTINO
```

Nada de substituição bruta de texto. Os parsers populam um modelo Pydantic
universal e renderers usam templates Jinja2 para gerar a CLI do vendor destino.

## Estrutura

```
olt-converter/
├── backend/                    # FastAPI + Pydantic + Jinja2
│   ├── app/
│   │   ├── models/             # Modelo universal OLTConfig
│   │   ├── parsers/            # 1 pacote por vendor/modelo
│   │   │   ├── fiberhome/an5516/
│   │   │   ├── zte/c600/
│   │   │   ├── huawei/ma5800/
│   │   │   └── datacom/dm4615/
│   │   ├── renderers/          # Idem, espelhando os parsers
│   │   ├── templates/          # Jinja2 (vlan.j2, pon.j2, ...)
│   │   ├── services/           # mapping, validator, conversion
│   │   ├── api/                # rotas e schemas FastAPI
│   │   └── main.py
│   └── requirements.txt
├── frontend/                   # React + Vite + Tailwind + Monaco
│   ├── src/
│   │   ├── components/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── store.js
│   ├── package.json
│   └── vite.config.js
├── examples/                   # Configs sintéticas para testes
├── uploads/                    # Configs enviadas via API
├── exports/                    # Configs geradas
└── README.md
```

## Vendors suportados

| Vendor    | Parser | Renderer | Modelo principal      |
|-----------|:------:|:--------:|-----------------------|
| Fiberhome |   ✅   |    ✅    | AN5516 / AN5116-06B   |
| ZTE       |   ✅   |    ✅    | C300 / C320 / C600    |
| Huawei    |   ✅   |    ✅    | MA5800 / MA5680T      |
| Datacom   |   ✅   |    ✅    | DM4615 / DM4610       |

## Funcionalidades

- **Detecção automática** do vendor da configuração
- **Parsing modular** de VLANs, uplinks, PONs, ONUs, service-ports,
  GEMPorts, T-CONTs, DBA/Line/Service profiles, Traffic profiles
- **Renderização** via templates Jinja2 (fácil customização)
- **Sistema de mapeamento** de interfaces entre vendors (editável via YAML)
- **Validação** com severidades (error/warning/info)
- **Diff visual** Monaco Diff Editor (origem ↔ destino)
- **Upload / download** de configurações
- **API REST** documentada via OpenAPI (`/docs`)
- **Logs estruturados** (structlog)
- **Frontend dark theme** moderno com 3 painéis (origem / estrutura / destino)

---

## Instalação

### Pré-requisitos

- Python 3.12+
- Node.js 18+ (com npm)

### Backend

```bash
cd olt-converter/backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse:
- Swagger UI:  http://localhost:8000/docs
- Health:      http://localhost:8000/health

### Frontend

```bash
cd olt-converter/frontend
npm install
npm run dev
```

Acesse:  http://localhost:5173

> O Vite faz proxy `/api/*` → `http://localhost:8000` automaticamente.
> Em produção, sirva o backend com gunicorn/uvicorn workers e o `dist/`
> do frontend por trás de um Nginx.

---

## Como usar

1. Suba **backend** e **frontend**
2. No frontend, clique em **📂 Upload** e selecione um arquivo de
   `examples/` ou da pasta `modelos-config/`
3. O vendor de origem é detectado automaticamente
4. Selecione o vendor **Destino** no topo
5. Clique em **⚙️ Converter**
6. Veja o **Diff** e baixe a configuração resultante em **💾 Download**

---

## Endpoints da API

| Método | Rota                       | Descrição                                  |
|--------|----------------------------|--------------------------------------------|
| POST   | `/api/v1/upload`           | Upload + detecção de vendor                |
| POST   | `/api/v1/parse`            | Parse de configuração → OLTConfig          |
| POST   | `/api/v1/render`           | OLTConfig → CLI de um vendor               |
| POST   | `/api/v1/convert`          | Pipeline completa: text → text             |
| POST   | `/api/v1/validate`         | Valida um OLTConfig                        |
| POST   | `/api/v1/export/{vendor}`  | Render + download como arquivo .cfg        |
| GET    | `/api/v1/vendors`          | Lista vendors disponíveis                  |
| GET    | `/api/v1/models/{vendor}`  | Lista modelos de um vendor                 |

### Exemplo (curl)

```bash
curl -X POST http://localhost:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{
    "config_text": "hostname OLT-LAB\nvlan add 100 CLIENTES",
    "source_vendor": "fiberhome",
    "target_vendor": "zte"
  }'
```

---

## Estendendo com um novo vendor

1. Crie `backend/app/parsers/<vendor>/<model>/parser.py` herdando de
   `BaseParser` e decorando a classe com `@register_parser`
2. Crie `backend/app/renderers/<vendor>/<model>/renderer.py` herdando de
   `BaseRenderer` e decorando a classe com `@register_renderer`
3. Crie os templates Jinja2 em `backend/app/templates/<vendor>/<model>/`
4. Atualize `app/parsers/registry.py::_autoload` e
   `app/renderers/registry.py::_autoload` com os novos imports
5. (Opcional) Adicione mapeamentos de interface em
   `app/services/mapping_data.yaml`

A pipeline é descoberta automaticamente via decorators — sem mexer no resto.

---

## Roadmap

- [ ] IA: detecção/correção automática de blocos não-parseados
- [ ] Histórico e auditoria (banco SQLite/Postgres)
- [ ] Multiusuário com perfis e permissões
- [ ] Exportação para PDF (relatório de conversão)
- [ ] Templates customizáveis via UI
- [ ] Comparação entre duas configs vivas
- [ ] Suporte a EPON / XGS-PON

---

## Licença

Uso interno do operador. Adapte conforme necessidade.
