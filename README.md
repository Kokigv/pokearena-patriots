# PokéArena

Juego de cartas Pokémon por turnos simultáneos. Proyecto del curso CE-1116 (equipo Patriots).

**Sprint 1:** identidad de prueba, **Crear carta**, **Buscar carta** y **Crear ubicación**.

**Sprint 2:** **Inicio de sesión con proveedor** (Google, US 116), **Recibir colección inicial**
(US 123) y **Explorar el catálogo y mi colección** (US 124), con todos los criterios de aceptación
de éxito, error y alternos.

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

### Entrar con Google (US 116)
1. En Google Cloud Console cree un *ID de cliente de OAuth* de tipo aplicación web con el origen
   autorizado `http://localhost:8080`.
2. Ponga el Client ID en `.env` como `GOOGLE_CLIENT_ID=...` y levante con
   `docker compose up --build` (la web lo recibe al compilarse).
3. En la web aparece el botón **Iniciar sesión con Google**. La API valida el ID token de Google
   una sola vez (`POST /v1/auth/google`) y responde con su propia credencial; en el primer
   ingreso crea la cuenta (Elo 0) y entrega la colección inicial.

Sin `GOOGLE_CLIENT_ID` se puede seguir entrando con el usuario de prueba, que sigue exactamente el
mismo flujo (cuenta, colección inicial y credencial) y queda marcado como cuenta de prueba.

### Entrar como administrador
En la web, botón **Entrar como usuario de prueba** con el sujeto `admin-1`. El rol de
administrador se asigna por configuración (`ADMIN_SUBJECTS` en `.env`, sujetos de prueba o correos
de Google). Cualquier otro usuario entra como jugador: ve **Catálogo y mi colección** y recibe
`403` en las pantallas de administración.

Por API:

```bash
TOKEN=$(curl -s -X POST localhost:8080/v1/dev/tokens -H 'Content-Type: application/json' \
  -d '{"subject":"admin-1"}' | jq -r .access_token)

# Jugador: colección inicial y catálogo con lo que posee
curl localhost:8080/v1/me/collection -H "Authorization: Bearer $TOKEN"
curl "localhost:8080/v1/catalog?type=AGUA&cost_min=1&cost_max=3&owned=true" -H "Authorization: Bearer $TOKEN"

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

Sin instalar Python, todo dentro de Docker (formato, lint, tipos, arquitectura y las 137 pruebas):

```bash
docker compose run --rm tests
```

Con Python local:

```bash
cd api
docker compose exec postgres psql -U pokearena -c "create database pokearena_test"   # una vez
export DATABASE_URL=postgresql+psycopg://pokearena:pokearena@localhost:5432/pokearena_test
pytest -q                     # 137 pruebas, incluidas las de 10.000 cartas
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
├─ identity/          cuentas, inicio de sesión con Google, credenciales propias (JWT) y roles
│  ├─ domain/ application/ infrastructure/ api/
├─ collection/        colección inicial, cubos y exploración del catálogo con lo que posee
│  ├─ domain/ application/ infrastructure/ api/
└─ catalog/           cartas, habilidades y ubicaciones (fachada pública para otros módulos)
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

## Decisiones relevantes del Sprint 2

| Tema | Decisión |
|---|---|
| Inicio de sesión | `POST /v1/auth/google` valida el ID token con PyJWT y las llaves públicas de Google (firma, emisor, audiencia = `GOOGLE_CLIENT_ID`, expiración) **una sola vez**, y entrega un JWT propio de 15 minutos con el id de la cuenta como sujeto. Token inválido: `401 invalid-provider-token`; Google caído: `503 identity-provider-unavailable`; en ambos casos no se crea cuenta. |
| Una cuenta por identidad | La cuenta se asocia a `(proveedor, sujeto)`, no al correo. Esa pareja es la llave primaria de `player_identities` y se inserta con `ON CONFLICT DO NOTHING`: dos ingresos simultáneos crean una sola cuenta. Un segundo proveedor es solo otro adaptador del puerto `IdentityProvider`. |
| Identidad ↔ Colección | Identidad define el puerto `PlayerOnboarding` y Colección lo implementa; `main.py` (raíz de composición) los conecta. Ningún módulo importa al otro al revés (contratos de `import-linter`). |
| Colección inicial | 15 cartas Comunes distintas con imagen lista, elegidas en el servidor con `secrets.SystemRandom`, y 1,000 cubos. Billetera, cartas y primer movimiento de cubos se guardan en **una transacción** (unidad de trabajo): todo o nada. La llave primaria de `player_wallets` garantiza que se entregue exactamente una vez, aunque haya dos ingresos simultáneos. Si faltan Comunes o la entrega falla, el jugador entra igual y la recibe en un próximo ingreso. |
| Explorar catálogo | `GET /v1/catalog` usa la fachada del catálogo con paginación por cursor (10.000 cartas, p95 bajo 200 ms en las pruebas) y une en memoria las copias del jugador. `owned=true` pasa la colección como filtro al catálogo, así la paginación sigue siendo correcta. |
| Caché | Las páginas del catálogo general y la lista de Comunes se guardan en Redis 30 s (`CATALOG_CACHE_SECONDS`). La colección del jugador nunca se guarda en caché. Si Redis falla, se lee directo de PostgreSQL. |
