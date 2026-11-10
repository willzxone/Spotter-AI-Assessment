# Project Guide: study notes + Loom script

Personal notes for learning the codebase and recording the walkthrough. The submission docs are
`README.md` (run, check, deploy) and `docs/architecture.md` (design). This file summarises both and
adds a script for the video.

---

## 1. The project in one minute

A truck driver enters **origin, destination, departure time and load weight**. The app:

1. gets **up to 3 road routes** (OSRM),
2. drops a **checkpoint every 10, 25 or 50 miles** along each one,
3. works out **when the truck reaches each checkpoint**,
4. reads the **forecast for that place at that hour** (Open-Meteo),
5. scores each checkpoint with the **brief's risk table and load rules**,
6. **recommends the safest route**, using travel time only as the tie-breaker,
7. shows everything on a **map**, with a **48-hour weather heatmap** and a time slider.

**Stack:** Django 6 + Django Ninja (Python 3.13) on the backend, React 19 + Vite + TanStack
Router/Query/Form + Tailwind/shadcn + MapLibre on the frontend. It ships as one Docker image on
Render. Django serves both the API and the built React app.

**Outside services (all free, no API keys):** OSRM (routes), Photon/OpenStreetMap (place search),
Open-Meteo (weather), OpenFreeMap (map tiles).

---

## 2. Brief requirement → where it lives

| Requirement                              | Where                                                                           |
| ---------------------------------------- | ------------------------------------------------------------------------------- |
| Origin, destination, departure, load     | `frontend/src/features/trips/components/trip-form.tsx`, validated on both sides |
| Up to 3 route options from a routing API | `backend/modules/routing/` (OSRM alternatives + via-point detours)              |
| Weather every 10 / 25 / 50 miles         | `backend/modules/trips/checkpoints.py`                                          |
| Weather at the truck's ETA               | `backend/modules/trips/service.py` (reads the forecast hour of arrival)         |
| Risk from the brief's table + load rules | `backend/modules/risk/constants.py` + `service.py`                              |
| Recommend safest route, then fastest     | `backend/modules/trips/ranking.py`                                              |
| Routes, checkpoints, risk, ETAs on a map | `frontend/src/features/trips/` (map, route cards, checkpoint table)             |
| Heatmap + 48-hour slider                 | `heatmap-slider.tsx`, `use-route-map.ts`, backend `_heatmap()`                  |

---

## 3. How one plan is computed (`POST /rpc/trips/plan`)

All of this happens in `backend/modules/trips/service.py → plan()`:

1. **Validate the departure.** It can be up to 1 hour in the past (treated as "leaving now") and
   up to 7 days ahead. The whole trip must finish within the 15-day forecast horizon.
2. **Get routes.** `routing.plan()` asks OSRM for alternatives. If OSRM returns fewer than 3, it
   adds **via-point detours**: it pushes a midpoint sideways (15%, then 30% of the straight-line
   distance, on either side). A detour is kept only if it takes at most 1.5× the fastest time and
   less than 80% of it overlaps a route already kept. Routes are sorted fastest first and labelled
   A, B, C. Results are cached for 1 hour.
3. **Place checkpoints** (`checkpoints.py`): one at the origin, one every N miles, one at the
   destination. Each checkpoint **covers half the road to its neighbours**, so the risk miles add
   up exactly to the route length. Each ETA comes from the route's own timing (OSRM per-segment
   durations), not from an assumed average speed.
4. **Fetch weather once for everything.** The map is divided into **0.2° grid cells** (about
   22 × 17 km). That's roughly the resolution of weather models, and it caps how many forecasts
   are needed. Every checkpoint cell and every cell along the corridor (sampled every 8 km on all
   routes) is fetched in batches of 50 locations per Open-Meteo call and cached for 15 minutes.
5. **Score each checkpoint** (`risk.assess`) with the forecast **for the hour the truck arrives**,
   interpolated between whole hours.
6. **Summarise each route.** Miles at each risk level, a mile-weighted average risk (0–4) and the
   worst level.
7. **Rank and explain** (`ranking.py`). Each route gets a one-line verdict naming the criterion
   that decided it.
8. **Build the heatmap.** A 0–4 risk score for every corridor cell, every hour from the departure
   hour to +48 h.

---

## 4. The rules (`backend/modules/risk/constants.py`)

### Risk table (from the brief)

| Condition | Low      | Moderate  | High      | Severe    | No Travel    |
| --------- | -------- | --------- | --------- | --------- | ------------ |
| Wind      | < 25 mph | 25–34     | 35–44     | 45–54     | ≥ 55 mph     |
| Rain      | < 0.10   | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | > 1.00 in/hr |
| Snow      | < 0.5    | 0.5–1.0   | 1.0–2.0   | 2.0–3.0   | > 3.0 in/hr  |

- A value **exactly on a shared boundary goes to the higher band** (25 mph is Moderate). The
  exceptions are the brief's "greater than" rows: rain of exactly 1.00 and snow of exactly 3.0 are
  still Severe.
- **Wind means sustained wind.** Gusts are shown in the UI for context but don't change the level,
  because the brief's thresholds are for sustained wind.
- **Rain = rain + showers** from Open-Meteo (showers are convective rain).

### Load rules (they can only raise the wind level)

| Wind      | Load        | Becomes   |
| --------- | ----------- | --------- |
| 45–55 mph | > 30,000 lb | No Travel |
| 35–45 mph | > 40,000 lb | Severe    |

**A checkpoint's level = the worst of (wind after load rules, rain, snow).** The conditions that
produced that level are listed as its "drivers" (the "Why" column in the table).

### Ranking order (`ranking.py → CRITERIA`)

Routes are compared one criterion at a time, and **the first criterion that differs decides**:

1. Fewest **No Travel** miles. This isn't in the brief's list, but No Travel is worse than Severe,
   so it comes first.
2. Fewest **Severe** miles
3. Fewest **High** miles
4. Lowest **average risk** (mile-weighted, 0–4)
5. Shortest **travel time**

Comparisons are rounded (miles to 0.1, average to 0.01, time to the minute) so noise doesn't decide.
Example verdict: _"Recommended: fewest No Travel miles (0 mi vs 225 mi on Route A)."_

### Heatmap score

`risk.score()` returns a **continuous** 0–4 score (level + how far into its band), so the colours
fade smoothly. `floor(score)` always equals the real level, and **every decision uses the level,
never the score**.

---

## 5. Backend architecture (`backend/`)

A **modular monolith**, the same shape as the reference repo:

```
server/    Django settings, URLs, WSGI          ← top layer
modules/   geocoding, routing, weather, risk, trips
core/      kernel, config, errors, RPC builders, the single API, middleware, TS generator
common/    framework-free geometry (distance, polylines, simplification)
```

**Layers only import downward.** `import-linter` enforces this (contracts in `pyproject.toml`):

- `server → modules → core → common`
- a module never reaches into another module's `adapters` or `router`; it uses only the other
  module's `service`, `dto` or `constants`
- pure logic (`common`, risk rules, geo) imports no Django or HTTP code

### Anatomy of a module

| File           | Role                                                                          |
| -------------- | ----------------------------------------------------------------------------- |
| `module.py`    | Manifest: name, version, shared services needed, procedures, start/stop hooks |
| `router.py`    | Thin RPC procedures (input/output are pydantic models)                        |
| `service.py`   | Business logic; the only file other modules may call                          |
| `adapters.py`  | The outside service behind a swappable interface (off / simulated / live)     |
| `dto.py`       | Shapes the module hands out (camelCase on the wire, unknown keys rejected)    |
| `constants.py` | Tunables and fixed tables                                                     |

`routing` and `weather` have **no router**: they're internal services that `trips` uses.
`modules/__init__.py` is the **registry** (the list of modules, in boot order).

### Kernel (`core/kernel.py`)

Boots each module in registry order. It checks that the shared services each module `requires`
exist, configures the module's adapter and runs its `start` hook. `/readyz` returns 200 only after
boot, so a misconfigured deploy never takes traffic.

### API: RPC, not REST

Every procedure is `POST /rpc/<module>/<procedure>` with a JSON body.

| Procedure          | What it does                 | Rate limit      |
| ------------------ | ---------------------------- | --------------- |
| `geocoding/search` | Place search for the pickers | 90 / min per IP |
| `risk/rules`       | The risk table + load rules  | none            |
| `trips/plan`       | The whole plan               | 20 / min per IP |

Also `/healthz` (liveness), `/readyz` (readiness) and `/rpc/openapi.json`; `/rpc/docs` is only
available when `DEBUG` is on.

**One error format:** `{"error": {"code", "message", "data", "requestId"}}`. The codes are
`BAD_REQUEST` 400, `NOT_FOUND` 404, `VALIDATION_FAILED` 422, `RATE_LIMITED` 429,
`UPSTREAM_UNAVAILABLE` 502, `SERVICE_DISABLED` 503 and `INTERNAL` 500. Every request gets an
`X-Request-Id` that also appears in the logs.

### Adapters: off / simulated / live

Set by `ROUTING_MODE`, `GEOCODING_MODE` and `WEATHER_MODE`:

- **live**: the real API (default in development and production)
- **simulated**: deterministic, no network. Routes are straight-line arcs, places come from a
  list of ~35 US freight hubs, and **3 made-up storms drift east** (used by the tests)
- **off**: the feature returns `SERVICE_DISABLED`

### Config (`core/config.py`)

The only file that reads environment variables. It checks everything at boot and **refuses to
start, listing every problem at once**. Production requires a `SECRET_KEY` of 32+ characters, a
public hostname and `DEBUG` off.

---

## 6. Frontend architecture (`frontend/src/`)

**Feature-based** layout (same rules as the reference repo):

```
routes/            thin route files (TanStack file routes)
features/
  trips/           the planner: form, map, route cards, heatmap slider, checkpoint table/card
  places/          place search box (debounced, cached)
  risk/            risk badge, legend, "Risk rules" dialog
components/ui/     shadcn primitives (generated)
components/shared/ shared components with no feature logic
integrations/      rpc client + generated API types, query client, MapLibre setup
```

- Each feature has `pages/ components/ hooks/ utils/ api/ constants.ts index.ts`.
  **Components hold markup only; the logic sits in a hook beside them.**
- ESLint blocks one feature from importing another's internals; only the feature's `index.ts`
  is public.
- **Types come from the backend:** `manage.py export_ts` turns Django's OpenAPI schema into
  `integrations/rpc/api.gen.ts`. `--check` fails if that file is stale, so the frontend and
  backend can't drift apart.
- **`rpc()` client** (`integrations/rpc/client.ts`): posts to `/rpc/<path>` and turns the error
  envelope into an `RpcError`. It retries once, and only for network or upstream (502) failures.
- **The form** (TanStack Form + zod) uses the same rules as the backend: load from 0 to 200,000 lb,
  departure from 1 h ago to 7 days ahead, origin and destination must differ.
- **The map** (MapLibre GL, OpenFreeMap basemap):
  - each route line is coloured by risk segment; the selected route is thicker
  - clicking a checkpoint opens its card
  - a truck marker shows where the truck is at the slider's hour
  - the heatmap layer is updated per hour by switching which value it reads, not by re-uploading
    the polygons, which keeps the slider smooth

### Differences from the reference architecture, and why

| Reference                    | Here                                     | Why                                                                      |
| ---------------------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| Auth, BFF proxy, tenancy     | none                                     | No accounts or private data; rate limits guard the outside-service calls |
| MongoDB                      | no database                              | Nothing needs to persist; caches are enough                              |
| Background workers, webhooks | none                                     | A plan is computed within the request                                    |
| oRPC + zod, types inferred   | Django Ninja + pydantic, types generated | The brief requires Django                                                |
| TanStack Start (SSR)         | Vite SPA served by Django                | One process, one origin; the map is client-only anyway                   |

---

## 7. Design decisions worth saying out loud

- **Weather at the ETA, not "now".** A storm 300 miles ahead matters only if it's still there
  when the truck arrives.
- **Checkpoints cover road, not points.** Each one owns half the gap to its neighbours, so "miles
  at Severe" is a real distance and the ranking compares like with like.
- **Safety first, time last.** Travel time only breaks ties, and the verdict says which rule
  decided.
- **The UI legend comes from the server** (`risk/rules`), so the displayed rules always match
  the logic.
- **Grid cells + batching + caching** keep a cross-country plan to a handful of weather calls.
- **Generated types + import contracts + config validation** turn whole classes of mistakes into
  build or boot errors.
- **Simulated mode** makes the tests deterministic and lets you demo every risk level on demand.

**Honest limits (good for Q&A):**

- OSRM's public server uses a **car** profile: no truck height or weight restrictions.
- Caches are per process (Django local memory); several instances would want Redis.
- The public OSRM, Photon and Open-Meteo servers have rate limits (I hit Open-Meteo's while
  testing).
- Forecasts get less reliable further out, so departures are capped at 7 days.

---

## 8. Running, demoing, checking

**Run locally** (two terminals):

```bash
cd backend && .venv/bin/python manage.py runserver          # :8000
cd frontend && pnpm dev                                      # :3000, open http://localhost:3000
```

**Demo every risk level with real roads and simulated storms** (environment variables override
`backend/.env`):

```bash
cd backend
ROUTING_MODE=live GEOCODING_MODE=live WEATHER_MODE=simulated .venv/bin/python manage.py runserver
```

The storms are placed relative to the departure hour, so the result is the same whenever you run it.

**Best demo trip: Dallas → Kansas City, 25-mile checkpoints.** Measured on 2026-11-10; OSRM may
shift the numbers slightly:

| Load      | Route A (fastest, ~9.4 h)        | Route B (~9.6 h)                 | Recommended |
| --------- | -------------------------------- | -------------------------------- | ----------- |
| 20,000 lb | 125 mi No Travel, 134 mi Severe  | 0 No Travel, 27 Severe, 339 High | B           |
| 35,000 lb | **225 mi No Travel** (load rule) | 0 No Travel, 27 Severe, 339 High | B           |
| 45,000 lb | 225 mi No Travel                 | High miles become **291 Severe** | B           |

Two things to point out: (1) the load rules visibly change the colours; (2) the app gives up
about 12 minutes to avoid every No Travel mile.

With **live** weather, today's forecast across the US tops out around Moderate (central Montana,
~27 mph). That's why the simulated mode is useful for showing High, Severe and No Travel.

**Quality gates:**

```bash
# backend: 144 tests
cd backend
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy .
.venv/bin/lint-imports                                      # architecture contracts
DJANGO_ENV=test .venv/bin/python manage.py export_ts --check  # generated types up to date

# frontend: 55 tests (prettier, eslint, tsc, vitest)
cd frontend && pnpm check
```

What the tests cover:

- **Backend:** risk boundaries and load rules, ranking and verdicts, checkpoint placement, geometry,
  adapters against mocked HTTP, services, the full API, config validation, the TS generator.
- **Frontend:** form schema and interaction, route results, formatting, geometry, map data,
  truck progress.

**Deploy:** `render.yaml` is a Render Blueprint for a Docker web service on the free plan, with
health check `/readyz`, an auto-generated `SECRET_KEY` and `NUM_PROXIES=1`. Render's own hostname
is trusted automatically. **The free tier sleeps after 15 idle minutes, so open the site about a
minute before recording.**

---

## 9. Loom script (target ~8 minutes; the brief asks for 5–10)

**Before recording:** wake the Render app; have the local simulated-weather server running in
another tab; open these files in the editor: `trips/service.py`, `trips/checkpoints.py`,
`risk/constants.py`, `risk/service.py`, `trips/ranking.py`, `routing/adapters.py`,
`core/kernel.py`, `core/config.py`, `modules/__init__.py`, `pyproject.toml`, `api.gen.ts`,
`features/trips/`.

### 0:00–0:30 · Intro

> "This is a weather-aware truck router. You give it a trip and a load, and it compares up to
> three routes by the weather the truck will actually drive through, then recommends the safest.
> Django and Django Ninja on the back, React and MapLibre on the front, hosted on Render, using
> only free data sources."

### 0:30–2:30 · Live demo (hosted app, real data)

- Fill the form: **Chicago → Atlanta**, departure _Now_, **35,000 lb**, every **25 mi**. Press Plan.
- **Route cards:** rank, _Recommended_ badge, worst level, drive time, distance, arrival, the
  risk-miles bar, and the verdict sentence. Point out that the verdict names the deciding rule.
- **Map:** routes coloured by risk segment; click another route to select it; click a checkpoint
  to open its card (wind, gust, rain, snow, level, why).
- **Checkpoint table:** mile, ETA, risk and readings; clicking a row rings that checkpoint on the
  map and brings it into view.
- **Heatmap slider:** press play. The corridor colours change hour by hour and the truck marker
  moves along the route.
- Point to the "Routing: OSRM · Weather: Open-Meteo" line under the results: the data is live.

### 2:30–4:00 · Risk logic on demand (local, simulated storms)

> "Real weather today is calm, so to show every level I run the same app with simulated storms.
> The UI says so in a banner."

- **Dallas → Kansas City at 35,000 lb.** Route A is fastest but has ~225 No Travel miles; the app
  recommends B, which is about 12 minutes slower.
- Change the load to **20,000 lb** and re-plan: A's No Travel miles drop, because the 45–55 mph
  - over 30,000 lb rule no longer applies.
- Change to **45,000 lb**: B's High miles turn Severe (35–45 mph + over 40,000 lb).
- Open **Risk rules**: "this table comes from the server, so it can't drift from the logic."

### 4:00–6:30 · Code tour

- **Layers** (`server → modules → core → common`); open `pyproject.toml` to show the
  import-linter contracts.
- **A module:** open `modules/trips/` and walk through module, router, service, dto, constants.
- **`trips/service.py → plan()`:** the 8 steps from section 3 (routes → checkpoints → one weather
  fetch → score at ETA → rank → heatmap).
- **`checkpoints.py`:** each checkpoint covers half the gap to its neighbours.
- **`risk/constants.py` + `risk/service.py`:** the brief's table as data, boundary handling, load
  rules, worst-of.
- **`ranking.py`:** the CRITERIA tuple, first difference decides, generated verdict.
- **`routing/adapters.py`:** off / simulated / live behind one interface; via-point detours when
  OSRM returns fewer than 3 routes.
- **`core/config.py`:** refuses to boot with a list of every problem. **`core/kernel.py`:** boots
  modules; `/readyz`.
- **Frontend:** `features/` layout, a component with its hook, `api.gen.ts` generated from the
  backend (`export_ts --check` in CI), `rpc()` client.

### 6:30–7:30 · Quality and deploy

- Run `pytest` (144) and `pnpm check` (55), or show the commands.
- `Dockerfile`: build the frontend, then run Django under gunicorn as a non-root user, with
  WhiteNoise serving the assets. `render.yaml`: one-click Blueprint, health check on `/readyz`.

### 7:30–8:00 · Trade-offs and next steps

> "If I took this further: a truck-aware router for height and weight limits, a shared Redis
> cache for multiple instances, and paid weather and routing tiers for higher rate limits."

---

## 10. Likely questions, short answers

- **Why RPC instead of REST?** It mirrors the reference architecture: one request shape, every
  procedure typed end to end, and the TS types are generated from it.
- **Why 0.2° cells?** That's about the forecast models' resolution, so finer cells add calls
  without adding information.
- **Why do gusts not affect risk?** The brief's thresholds are for sustained wind. Gusts are shown
  so the driver still sees them.
- **What if OSRM returns only one route?** Via-point detours fill the gap, but only real
  alternatives are kept: no more than 1.5× the fastest time and less than 80% overlap. Sometimes
  only one sensible road exists, and the verdict says so.
- **How are rate limits applied per user?** Per client IP using Django's cache. `NUM_PROXIES`
  tells the app how many proxy hops to skip so it sees the real IP.
- **Why no database?** Nothing needs to persist. Routes (1 h), forecasts (15 min) and place
  searches (24 h) are cached.
- **Why does Django serve the React app?** One origin, so no CORS or second server, and simple
  hosting on a free tier.
