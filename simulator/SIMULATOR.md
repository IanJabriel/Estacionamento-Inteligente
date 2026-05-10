# Simulador — Smart Parking

Simula 90 sensores (3 setores × 30 vagas) publicando eventos MQTT em tempo real.

---

## Como funciona

Cada vaga roda de forma independente, alternando entre `FREE` e `OCCUPIED` com tempos realistas:

- **FREE → OCCUPIED:** 5 a 30 minutos simulados
- **OCCUPIED → FREE:** 30 minutos a 6 horas simuladas

Durante horários de pico (8h–10h e 17h–19h simulados) as vagas ocupam mais rápido.

A escala de tempo é controlada pela variável `TIME_FACTOR`:
- `TIME_FACTOR=60` → 1 segundo real = 1 minuto simulado (padrão)
- `TIME_FACTOR=5` → 1 segundo real = 5 minutos simulados (bom para demo)

O simulador lê o `failures.json` a cada **1 segundo** e aplica as falhas em tempo real — sem precisar reiniciar nada.

---

## Falhas injetáveis (`failures.json`)

| Tipo | O que faz | Incidente gerado |
|---|---|---|
| `stuck_occupied` | Trava a vaga como OCUPADA para sempre | `STUCK_OCCUPIED` |
| `stuck_free` | Trava a vaga como LIVRE para sempre | `STUCK_FREE` |
| `flapping` | Vaga fica trocando de estado 5x rapidamente, descansa 5s e repete | `FLAPPING` |

### Exemplo de configuração de teste

```json
{
  "stuck_occupied": ["A-01", "A-02"],
  "stuck_free": ["B-05"],
  "flapping": ["C-07", "C-08"]
}
```

- `A-01` e `A-02` ficam travadas como OCCUPIED
- `B-05` fica travada como FREE
- `C-07` e `C-08` ficam em flapping (trocas rápidas)

### Limpar todas as falhas

```json
{
  "stuck_occupied": [],
  "stuck_free": [],
  "flapping": []
}
```

---

## Verificar no terminal

```bash
# Ver logs do simulador em tempo real
docker compose logs -f simulator

# Ver incidentes gerados na API
curl "http://localhost:8000/api/v1/incidents?status=open"
```