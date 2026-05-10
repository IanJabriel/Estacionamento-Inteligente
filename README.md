# Estacionamento Inteligente — MVP

MVP completo em Python: backend FastAPI + broker Mosquitto MQTT + simulador assíncrono + SQLite.
3 setores (A, B, C) × 30 vagas = 90 vagas no total.

## Estrutura do projeto

```
.
├── docker-compose.yml          # mosquitto + parking-api + simulator
├── mosquitto/config/           # configuração do broker (anônimo na porta 1883)
├── src/                        # backend FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # entrada da app, lifespan, routers
│   ├── config.py               # configurações via variáveis de ambiente
│   ├── database.py             # engine SQLAlchemy + seed inicial das 90 vagas
│   ├── models.py               # tabelas do banco (ORM)
│   ├── schemas.py              # schemas Pydantic (entrada/saída)
│   ├── mqtt_consumer.py        # consumidor MQTT em background thread
│   ├── background.py           # workers periódicos: scan de incidentes + snapshots
│   ├── routes/                 # endpoints REST
│   │   ├── map.py
│   │   ├── sectors.py
│   │   ├── reports.py
│   │   ├── incidents.py
│   │   └── recommendation.py
│   └── services/               # lógica de negócio
│       ├── ingestion.py        # ingestão idempotente de eventos por eventId
│       ├── sectors.py          # estatísticas, vagas livres e snapshots
│       ├── recommendation.py   # sugestão de setor alternativo
│       ├── incidents.py        # detecção de STUCK e FLAPPING
│       └── reports.py          # relatório de rotatividade
└── simulator/                  # publicador MQTT
    ├── Dockerfile
    ├── requirements.txt
    ├── simulator.py            # simulador assíncrono (asyncio) com 90 corrotinas
    └── failures.json           # injeção de falhas (relido a cada 1 segundo)
```

## Como rodar

### 1) Subir tudo com Docker

```bash
docker compose up --build
```

Sobe os 3 serviços:
- `mosquitto` na porta `1883`
- `parking-api` em `http://localhost:8000` (Swagger em `/docs`)
- `parking-simulator` publicando eventos para as 90 vagas

### 2) Rodar sem Docker

Suba só o broker:
```bash
docker compose up mosquitto
```

API:
```bash
cd src
pip install -r requirements.txt
export MQTT_HOST=localhost        # PowerShell: $env:MQTT_HOST="localhost"
export DB_PATH=./data/parking.db
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Simulador:
```bash
cd simulator
pip install -r requirements.txt
export MQTT_HOST=localhost
python simulator.py
```

### 3) Injetar falhas

Edite o `simulator/failures.json` com o sistema rodando. O simulador relê o arquivo a cada **1 segundo** e aplica as mudanças em tempo real — sem reiniciar nada:

```json
{
  "stuck_occupied": ["A-01"],
  "stuck_free": ["B-15"],
  "flapping": ["C-07"]
}
```

| Tipo | O que faz | Incidente gerado |
|---|---|---|
| `stuck_occupied` | Trava a vaga como OCCUPIED | `STUCK_OCCUPIED` (warning) |
| `stuck_free` | Trava a vaga como FREE | `STUCK_FREE` (info) |
| `flapping` | Vaga troca de estado 5x rapidamente e repete | `FLAPPING` (critical) |

Os incidentes `STUCK_OCCUPIED` e `STUCK_FREE` abrem após a vaga ficar parada pelo tempo configurado nas env vars `STUCK_OCCUPIED_MIN` e `STUCK_FREE_MIN`. O `FLAPPING` abre quando uma vaga ultrapassa `FLAPPING_MAX_CHANGES` eventos dentro de `FLAPPING_WINDOW_MIN` minutos.

Para limpar todas as falhas:
```json
{
  "stuck_occupied": [],
  "stuck_free": [],
  "flapping": []
}
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `TIME_FACTOR` | `60` | Escala de tempo do simulador: 1s real = N minutos simulados |
| `STUCK_OCCUPIED_MIN` | `240` | Minutos parado para abrir incidente STUCK_OCCUPIED |
| `STUCK_FREE_MIN` | `1440` | Minutos parado para abrir incidente STUCK_FREE |
| `FLAPPING_WINDOW_MIN` | `5` | Janela em minutos para detectar flapping |
| `FLAPPING_MAX_CHANGES` | `8` | Trocas dentro da janela para abrir incidente FLAPPING |
| `OCCUPANCY_THRESHOLD` | `0.90` | Taxa de ocupação para gerar recomendação de setor |

> **Dica para demonstração:** defina `STUCK_OCCUPIED_MIN=2` e `STUCK_FREE_MIN=2` no `docker-compose.yml` para ver os incidentes aparecerem em 2 minutos reais.

## Endpoints REST

| Método | Caminho | Descrição |
|--------|---------|-----------|
| GET | `/api/v1/map` | Mapa completo (setores + vagas + estado atual) |
| GET | `/api/v1/sectors` | Estatísticas de ocupação por setor |
| GET | `/api/v1/sectors/{sectorId}/spots` | Todas as vagas de um setor |
| GET | `/api/v1/sectors/{sectorId}/free-spots?limit=10` | Primeiras N vagas livres |
| GET | `/api/v1/reports/turnover?sectorId=A&from=...&to=...` | Rotatividade e tempo médio de permanência |
| GET | `/api/v1/incidents?status=open` | Incidentes detectados (filtrável por status e setor) |
| GET | `/api/v1/recommendation?fromSector=A` | Sugestão de setor alternativo quando lotado |
| GET | `/health` | Verificação de saúde da API |

## Tópicos MQTT

- Eventos de vaga: `campus/parking/sectors/{sectorId}/spots/{spotId}/events`
- Status do gateway: `campus/parking/sectors/{sectorId}/gateway/status`

Payload de evento:
```json
{
  "eventId": "uuid",
  "ts": "2026-05-09T12:34:56Z",
  "sectorId": "A",
  "spotId": "A-01",
  "state": "OCCUPIED",
  "source": "sensor"
}
```

## Teste rápido

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/sectors
curl "http://localhost:8000/api/v1/sectors/A/free-spots?limit=5"
curl "http://localhost:8000/api/v1/recommendation?fromSector=A"
curl "http://localhost:8000/api/v1/incidents?status=open"
```

## Como funciona (resumo)

O backend é uma aplicação FastAPI com separação clara de responsabilidades: `routes/` são adaptadores HTTP finos, `services/` contém a lógica de negócio, `models.py` define o schema SQLAlchemy e o SQLite é criado e populado automaticamente na inicialização com as 90 vagas. Um consumidor paho-mqtt roda em background thread, assina o tópico wildcard de eventos e persiste cada mensagem via `services/ingestion.py`, que usa o `eventId` para idempotência, grava em `spot_events` e atualiza a linha em `spots`. Dois workers periódicos rodam em paralelo: um tira snapshots de ocupação por setor, o outro escaneia incidentes de STUCK e FLAPPING usando thresholds configuráveis. O serviço de recomendação é acionado quando a ocupação atinge 90% e sugere o setor com mais vagas livres. O simulador é um script Python assíncrono (asyncio) com uma corrotina por vaga, publicando ciclos realistas de FREE/OCCUPIED com bias de horário de pico e suporte a injeção de falhas via `failures.json` relido a cada segundo.