# Endpoints da API

Base URL: `http://localhost:8000`

---

### GET /health
Verifica se a API está no ar.

```bash
curl http://localhost:8000/health
```
```json
{ "status": "ok" }
```

---

### GET /api/v1/map
Mapa completo com todos os setores e vagas.

```bash
curl http://localhost:8000/api/v1/map
```
```json
{
  "ts": "2026-05-09T10:00:00Z",
  "sectors": [
    { "sectorId": "A", "totalSpots": 30, "occupiedCount": 18, "freeCount": 12, "occupancyRate": 0.6 }
  ],
  "spots": [
    { "spotId": "A-01", "sectorId": "A", "currentState": "OCCUPIED", "lastChangeTs": "2026-05-09T09:00:00Z" }
  ]
}
```

---

### GET /api/v1/sectors
Ocupação resumida de cada setor.

```bash
curl http://localhost:8000/api/v1/sectors
```
```json
[
  { "sectorId": "A", "totalSpots": 30, "occupiedCount": 18, "freeCount": 12, "occupancyRate": 0.6 },
  { "sectorId": "B", "totalSpots": 30, "occupiedCount": 27, "freeCount": 3,  "occupancyRate": 0.9 },
  { "sectorId": "C", "totalSpots": 30, "occupiedCount": 10, "freeCount": 20, "occupancyRate": 0.33 }
]
```

---

### GET /api/v1/sectors/:sectorId/spots
Todas as vagas de um setor.

```bash
curl http://localhost:8000/api/v1/sectors/A/spots
```
```json
[
  { "spotId": "A-01", "sectorId": "A", "currentState": "OCCUPIED", "lastChangeTs": "2026-05-09T09:00:00Z" },
  { "spotId": "A-02", "sectorId": "A", "currentState": "FREE",     "lastChangeTs": "2026-05-09T08:30:00Z" }
]
```

---

### GET /api/v1/sectors/:sectorId/free-spots
Primeiras N vagas livres de um setor. Parâmetro `limit` opcional (padrão 10, máximo 100).

```bash
curl "http://localhost:8000/api/v1/sectors/B/free-spots?limit=5"
```
```json
[
  { "spotId": "B-03", "sectorId": "B", "currentState": "FREE", "lastChangeTs": "2026-05-09T09:30:00Z" },
  { "spotId": "B-07", "sectorId": "B", "currentState": "FREE", "lastChangeTs": "2026-05-09T08:00:00Z" }
]
```

---

### GET /api/v1/reports/turnover
Rotatividade de um setor em um período. Parâmetros `from` e `to` opcionais (padrão: últimas 24h).

```bash
curl "http://localhost:8000/api/v1/reports/turnover?sectorId=A"
curl "http://localhost:8000/api/v1/reports/turnover?sectorId=A&from=2026-05-09T08:00:00&to=2026-05-09T12:00:00"
```
```json
{
  "sectorId": "A",
  "fromTs": "2026-05-08T10:00:00Z",
  "toTs": "2026-05-09T10:00:00Z",
  "transitions": 142,
  "avgOccupiedDurationMin": 87.5,
  "avgFreeDurationMin": 12.3
}
```

---

### GET /api/v1/incidents
Incidentes detectados. Parâmetros opcionais: `status` (open/closed) e `sectorId`.

```bash
curl "http://localhost:8000/api/v1/incidents?status=open"
curl "http://localhost:8000/api/v1/incidents?status=open&sectorId=C"
```
```json
[
  {
    "id": 1,
    "type": "STUCK_OCCUPIED",
    "severity": "warning",
    "sectorId": "A",
    "spotId": "A-01",
    "status": "open",
    "tsOpen": "2026-05-09T10:05:00Z",
    "tsClose": null,
    "evidenceJson": "{\"idleMinutes\": 245, \"thresholdMin\": 240}"
  },
  {
    "id": 2,
    "type": "FLAPPING",
    "severity": "critical",
    "sectorId": "C",
    "spotId": "C-07",
    "status": "open",
    "tsOpen": "2026-05-09T10:10:00Z",
    "tsClose": null,
    "evidenceJson": "{\"events\": 12, \"windowMin\": 5}"
  }
]
```

| Tipo | Severidade | Quando abre |
|---|---|---|
| `STUCK_OCCUPIED` | warning | Vaga ocupada sem mudar por 4h (configurável) |
| `STUCK_FREE` | info | Vaga livre sem mudar por 24h (configurável) |
| `FLAPPING` | critical | Mais de 8 trocas em 5 minutos (configurável) |

---

### GET /api/v1/recommendation
Sugere setor alternativo quando o setor consultado está com 90%+ de ocupação. Registrado automaticamente no banco.

```bash
curl "http://localhost:8000/api/v1/recommendation?fromSector=A"
```

Setor lotado (≥ 90%):
```json
{
  "fromSector": "A",
  "recommendedSector": "C",
  "reason": "Sector A at 93% occupancy; Sector C has 18 free spots",
  "ts": "2026-05-09T10:20:00Z"
}
```

Setor com vagas (< 90%):
```json
{
  "fromSector": "A",
  "recommendedSector": null,
  "reason": "Sector A at 60% occupancy (below 90% threshold); no recommendation",
  "ts": "2026-05-09T10:20:00Z"
}
```