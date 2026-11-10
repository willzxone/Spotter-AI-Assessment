# Architecture

One deployable. Django serves the RPC API under `/rpc/`, the health probes, and the built
React app. The backend is a modular monolith; the frontend is organised by feature. Both
follow the same shape as the reference architecture (core + self-contained modules on the
server, `src/features/<name>/` on the client), adapted to Django and a Vite SPA. The
differences, and the reasons for them, are at the end.

## Backend: modular monolith

```
backend/
  common/    framework-free helpers (great-circle maths, polylines, simplification)
  core/      kernel, config, errors, logging, middleware, HTTP client, RPC builders, the one API
  modules/   geocoding, routing, weather, risk, trips; one package each
  server/    Django settings, URLs, WSGI
```

### Layers

`server -> modules -> core -> common`. A layer may import the ones to its right, never to its
left. `core` knows nothing about any module; the only thing it imports from `modules/` is the
registry in `modules/__init__.py`, which lists the modules in boot order.

### A module

| File           | Role                                                                                                                                                                                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `module.py`    | The manifest: name, version, the shared services it needs (`config`, `http`, `cache`, `logger`), its procedures, and `register` / `start` / `stop` hooks. The kernel refuses to boot if a module asks for a service core does not provide.                                     |
| `router.py`    | Thin procedures. Input and output are pydantic models (`core.schema.ApiSchema`): camelCase on the wire, unknown keys rejected, frozen.                                                                                                                                          |
| `service.py`   | The business logic, and the only surface other modules may call.                                                                                                                                                                                                              |
| `adapters.py`  | The outside service behind a swappable interface, in three modes (see below).                                                                                                                                                                                                  |
| `dto.py`       | The shapes the module hands out.                                                                                                                                                                                                                                              |
| `constants.py` | Tunables and fixed tables.                                                                                                                                                                                                                                                    |

`trips` also has `checkpoints.py` (placing checkpoints along a route) and `ranking.py`
(ordering routes and writing the verdict). `routing` and `weather` have no router: they are
internal services that `trips` composes.

### Rules, enforced by `lint-imports`

The contracts live in `backend/pyproject.toml` under `[tool.importlinter]`:

1. **Layers**: `server -> modules -> core -> common`.
2. **Module boundaries**: a module never reaches into another module's `adapters`, `module`
   or `router`. It goes through the other module's `service` (or its `dto` / `constants`).
3. **Pure logic stays pure**: `common` and the risk rules do no I/O. They cannot import
   `httpx`, Django's cache, or any module that does.

### RPC, not REST

Every procedure is `POST /rpc/<module>/<procedure>` with a JSON body:

| Procedure          | Purpose                                                                   | Rate limit       |
| ------------------ | ------------------------------------------------------------------------- | ---------------- |
| `geocoding/search` | Place search for the origin and destination pickers                       | 90 / min per IP  |
| `risk/rules`       | The thresholds and load rules, so the UI legend never drifts from the code | none             |
| `trips/plan`       | Plan up to 3 routes, score weather at every checkpoint, recommend one     | 20 / min per IP  |

Every failure uses one envelope:

```json
{ "error": { "code": "VALIDATION_FAILED", "message": "...", "data": {}, "requestId": "..." } }
```

| Code                   | HTTP |
| ---------------------- | ---- |
| `BAD_REQUEST`          | 400  |
| `NOT_FOUND`            | 404  |
| `VALIDATION_FAILED`    | 422  |
| `RATE_LIMITED`         | 429  |
| `UPSTREAM_UNAVAILABLE` | 502  |
| `SERVICE_DISABLED`     | 503  |
| `INTERNAL`             | 500  |

Validation errors list each problem as `{path, message}`, so the client can attach them to
form fields. An internal error never leaks details; the client gets the `requestId`, and the
log line under that id has the traceback. The middleware accepts a well-formed incoming
`X-Request-Id` or mints one, echoes it on the response and stamps it on every log line.

The OpenAPI schema is at `/rpc/openapi.json`. The interactive docs at `/rpc/docs` exist only
when `DEBUG` is on.

### Outside services: off, simulated or live

| Service   | `live`                         | `simulated`                                     |
| --------- | ------------------------------ | ----------------------------------------------- |
| routing   | OSRM (public demo server)      | Great-circle legs bowed sideways into 3 routes  |
| geocoding | Photon (OpenStreetMap)         | A fixed gazetteer of major US freight hubs      |
| weather   | Open-Meteo hourly forecast     | Deterministic storms that drift across the map  |

`ROUTING_MODE`, `GEOCODING_MODE` and `WEATHER_MODE` pick the mode. `off` disables the feature,
and its calls fail with `SERVICE_DISABLED`. Everything defaults to `live` (all three APIs are
free and need no key), except under `DJANGO_ENV=test`, which defaults to `simulated` so tests
never touch the network.

### Configuration

`core/config.py` is the only code that reads the environment. It reads `backend/.env` (if
present), lets the real environment override it, validates everything, and refuses to boot
with a list of every problem rather than failing on the first. Production additionally
requires a real `SECRET_KEY`, `ALLOWED_HOSTS` and `DEBUG=false`. A half-configured adapter
(an Open-Meteo key without the commercial endpoint, or the reverse) is a boot error, not a
silent fallback.

There is no database: nothing needs to persist. Route, weather and place lookups are cached
in Django's local-memory cache.

### How a plan is computed (`trips.service.plan`)

1. **Routes.** `routing` asks OSRM for alternatives. When it returns fewer than 3, via-point
   detours fill the gap. A detour is dropped if it is over 1.5x the fastest duration or mostly
   retraces a route already kept. Results are cached for an hour.
2. **Checkpoints.** A checkpoint goes at the origin, every 10, 25 or 50 miles after it (the
   user picks), and at the destination. Each ETA comes from the route's cumulative driving time at that
   distance, so it follows the road's real speeds rather than an average.
3. **Weather.** Checkpoints snap to a 0.2 degree grid, so nearby points share one forecast.
   Each cell's hourly forecast is fetched once (50 cells per request) and cached for 15 minutes.
4. **Risk.** Each checkpoint is scored on the forecast for the hour the truck gets there.
   Wind, rain and snow are classified against the brief's table (`modules/risk/constants.py`).
   The load rules can then raise the wind level for a heavy truck, and the worst level wins.
   Every result records which condition drove it.
5. **Ranking.** Routes are compared criterion by criterion, and the first that differs decides:
   fewest No Travel miles, fewest Severe miles, fewest High miles, lowest average risk, then
   shortest travel time. No Travel comes first because it is stricter than Severe. Miles are
   compared at 0.1 mi, so rounding noise never beats a real difference later in the list.
   The verdict sentence names the criterion that decided.
6. **Heatmap.** Corridor cells are collected every 8 km along every route and scored hourly
   for the 48 hours after departure. The UI slider moves through them without another request.

Departures may be up to an hour in the past (the "leaving now" case) and up to 7 days ahead.
A trip whose arrival falls beyond the forecast horizon is refused rather than scored on
missing data.

## Frontend: feature-based SPA

Vite + React 19, TanStack Router (file routes), TanStack Query and TanStack Form, Tailwind v4
with shadcn/ui, and MapLibre GL on an OpenFreeMap basemap (no key needed).

```
frontend/src/
  routes/            thin file routes; each renders one feature page
  features/<name>/   trips, places, risk
    pages/           whole screens, exported from the feature's index.ts
    components/      markup only
    hooks/           the logic beside each component (state, queries, derived values)
    utils/           pure helpers, unit-tested without a DOM
    api/             queryOptions for the feature's procedures
    constants.ts     fixed copy and lookup tables
    index.ts         the feature's only public surface
  components/ui/     shadcn primitives (generated)
  components/shared/ feature-agnostic components
  integrations/      rpc client + generated types, query client, MapLibre setup
```

### Rules, enforced by ESLint (`frontend/eslint.config.js`)

- A feature imports another feature only through its `index.ts`, never a deep path.
- `components/ui` are leaf primitives; `components/shared` may use them but no feature.
- `integrations` cannot reach into features.
- Routes are leaf nodes: data flows route -> feature, never the reverse.

### Data

`integrations/rpc/client.ts` is the single fetch path. It posts to `/rpc/<path>`, unwraps the
error envelope into a typed `RpcError`, and marks network failures and `UPSTREAM_UNAVAILABLE`
as transient. Only those get a retry, once; a 4xx would give the same answer twice. Query keys come from the procedure path.

The request and response types in `integrations/rpc/api.gen.ts` are generated from the
backend's OpenAPI schema by `python manage.py export_ts`. Run with `--check`, it fails when
the committed file is stale, so the two sides cannot drift apart unnoticed.

## Where this differs from the reference architecture, and why

| Reference                                         | Here                                         | Why                                                                                                                                 |
| ------------------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Auth, BFF proxy with httpOnly cookies, tenancy     | None; all procedures are public               | There are no accounts or private data. Abuse is bounded by per-IP rate limits on the two procedures that call outside services.  |
| Background workers, webhooks                      | None                                         | Nothing is asynchronous. A plan is computed inside the request.                                                                     |
| Database models                                   | No database                                  | Nothing needs to persist; caches are enough.                                                                                       |
| oRPC + zod, types inferred                        | Django Ninja + pydantic, types generated      | The stack is Django. Generation (with a CI check) gives the same single source of truth.                                           |
| Server-rendered TanStack Start                    | Vite SPA served by Django                     | One process, one origin, simplest to host. The map is client-only anyway, so SSR would add a Node server for little gain.          |
