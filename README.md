# PokéArena

Juego de cartas Pokémon por turnos simultáneos. Proyecto del curso CE-1116 (equipo Patriots).

**Sprint 1:** identidad de prueba, **Crear carta**, **Buscar carta** y **Crear ubicación**, con
todos los criterios de aceptación de éxito, error y alternos.

## Levantar todo con un comando

Requisitos: Docker y Docker Compose.

```bash
cp .env.example .env        # opcional: cambiar secretos y administradores
docker compose up --build
```

| Qué | Dónde |
|---|---|
| Web de administración | http://localhost:8080 |
| API (Swagger) | http://localhost:8080/docs |
| Contrato OpenAPI | [`api/openapi.yaml`](api/openapi.yaml) |

Compose levanta PostgreSQL, Redis, las migraciones, **2 réplicas de la API** y Nginx como
balanceador (que además sirve la web). La respuesta trae el encabezado `X-Upstream` con la
réplica que atendió cada solicitud.

### Entrar como administrador
En la web, botón **Entrar como usuario de prueba** con el sujeto `admin-1`. El rol de
administrador se asigna por configuración (`ADMIN_SUBJECTS` en `.env`). Cualquier otro sujeto
entra como jugador y recibe `403` en el catálogo.

Por API:

```bash
TOKEN=$(curl -s -X POST localhost:8080/v1/dev/tokens -H 'Content-Type: application/json' \
  -d '{"subject":"admin-1"}' | jq -r .access_token)

curl -X POST localhost:8080/v1/cards -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -F name=Pikachu -F cost=2 -F power=3 -F type=ELECTRICO -F rarity=COMUN \
  -F ability_code=HAB-000 -F image=@pikachu.png

curl "localhost:8080/v1/cards?name=pika&cost_min=1&cost_max=3" -H "Authorization: Bearer $TOKEN"
```

### Cargar 10.000 cartas de prueba

```bash
docker compose exec api python scripts/seed_cards.py 10000
```

## Desarrollo local sin Docker para la API

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d postgres redis              # desde la raíz del repo
export DATABASE_URL=postgresql+psycopg://pokearena:pokearena@localhost:5432/pokearena
export ADMIN_SUBJECTS=admin-1
alembic upgrade head
uvicorn pokearena.main:app --reload             # http://localhost:8000/docs
```

Web en modo desarrollo (reenvía `/v1` a `localhost:8000`):

```bash
cd web && npm install && npm run dev            # http://localhost:5173
```

## Pruebas y calidad

Sin instalar Python, todo dentro de Docker (formato, lint, tipos, arquitectura y las 88 pruebas):

```bash
docker compose run --rm tests
```

Con Python local:

```bash
cd api
docker compose exec postgres psql -U pokearena -c "create database pokearena_test"   # una vez
export DATABASE_URL=postgresql+psycopg://pokearena:pokearena@localhost:5432/pokearena_test
pytest -q                     # 88 pruebas, incluidas las de 10.000 cartas
ruff format --check . && ruff check .
mypy
PYTHONPATH=src lint-imports   # pruebas de arquitectura (RNF-ARQ-04)
```

El mismo pipeline corre en GitHub Actions en cada PR (`.github/workflows/ci.yml`).

## Arquitectura

Monolito modular con arquitectura hexagonal (ADR-001 en la wiki, V4). Cada módulo tiene:

```
api/src/pokearena/
├─ shared/            configuración, errores problem+json, idempotencia, base de datos
├─ identity/          credenciales propias (JWT) y roles por configuración
│  ├─ domain/ application/ infrastructure/ api/
└─ catalog/           cartas, habilidades y ubicaciones
   ├─ domain/         reglas puras: valores permitidos, imágenes, efectos, búsqueda
   ├─ application/    casos de uso y puertos (interfaces)
   ├─ infrastructure/ PostgreSQL, Pillow, almacenamiento de imágenes
   └─ api/            rutas FastAPI y construcción de dependencias
```

`import-linter` verifica que el dominio no importe frameworks ni infraestructura, que se respeten
las capas y que los módulos solo se usen por su API pública.

## Decisiones relevantes del Sprint 1

| Tema | Decisión |
|---|---|
| Autenticación | La API solo acepta JWT emitidos por ella misma. En el Sprint 1 se obtienen con `POST /v1/dev/tokens`, que no existe con `APP_ENV=production` (hay una prueba que lo verifica). |
| 401 vs 403 | `unauthenticated` / `token-expired` (401) y `forbidden` (403), en `application/problem+json`. |
| Código de carta | `PKA-<TIPO>-<NNN>` con un contador por tipo bloqueado en la misma transacción del INSERT: dos administradores nunca reciben el mismo código y un fallo no consume números. Después de 999 sigue 1000. |
| Reintentos | Encabezado `Idempotency-Key` obligatorio. Redis devuelve la respuesta original al reintento (aunque llegue a otra réplica) y la columna única en PostgreSQL impide duplicados aunque se pierda Redis. |
| Imágenes | Validación con Pillow (formato real, 5 MB, proporción, resolución). La versión pequeña se genera en la misma solicitud con 3 intentos (ADR-002); si falla, la carta queda `FAILED`, no visible para jugadores, y se reintenta con `POST /v1/cards/{code}/image/retry`. |
| Búsqueda | Índice trigram sobre el nombre sin tildes, filtros combinables y paginación por cursor ordenada por (tipo, consecutivo): estable, sin repetidos ni omitidos. p95 de ~15 ms con 10.000 cartas en las pruebas. |
| Habilidades | Se siembra `HAB-000 Sin Habilidad`. Crear habilidad es del Sprint 2; las reglas de evolución (no a sí misma, sin ciclos) ya se validan al crear cartas. |
