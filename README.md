# Weather-Aware Truck Routing

Plan a truck trip between two places. The app proposes up to three routes, samples the
weather at every checkpoint for the hour the truck will actually reach it, classifies the risk
with the brief's thresholds and load rules, and recommends the safest route. It shows routes,
checkpoints, ETAs, risk levels, and a 48-hour weather heatmap of the corridor on a map.

- **Backend:** Django + Django Ninja, a modular monolith with RPC procedures under `/rpc/`
- **Frontend:** React 19, Vite, TanStack Router / Query / Form, Tailwind + shadcn/ui, MapLibre
- **Outside services:** all free with no API key: OSRM (routing), Photon (geocoding), Open-Meteo (weather)

The design, the rules and the ranking are explained in [`docs/architecture.md`](docs/architecture.md).

## What it does

| Requirement                                         | Where                                                                          |
| --------------------------------------------------- | ------------------------------------------------------------------------------ |
| Origin, destination, departure time, load weight    | Trip form (`features/trips/components/trip-form.tsx`), validated on both sides |
| 3 route options from a routing API                  | `modules/routing`: OSRM alternatives, topped up with via-point detours         |
| Weather every 10 / 25 / 50 miles                    | `modules/trips/checkpoints.py`; the user picks the interval                    |
| Weather at the truck's ETA at each checkpoint       | ETAs from the route's own timing; hourly forecast at that hour                 |
| Risk from the brief's thresholds and load rules     | `modules/risk` (table in `constants.py`, mirrored in the UI's "Risk rules")    |
| Recommend safest, balancing risk and time           | `modules/trips/ranking.py`; the verdict names the deciding criterion           |
| Routes, checkpoints, risk, ETAs, summaries on a map | Route cards, map, checkpoint table, checkpoint card                            |
| Weather heatmap with a 48-hour slider               | Corridor heatmap plus a slider with playback; a truck marker follows the clock |

## Running locally

Requirements: Python 3.13, Node 22+, and pnpm 10 (`corepack enable` gives the pinned version).

**Backend** (port 8000):

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # defaults work as-is; see below
.venv/bin/python manage.py runserver
```

**Frontend** (port 3000; proxies `/rpc` to the backend):

```bash
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:3000.

### Live or simulated

By default the backend calls the real APIs. To work offline, or to avoid the public demo
servers' rate limits, set these in `backend/.env`:

```bash
ROUTING_MODE=simulated
GEOCODING_MODE=simulated
WEATHER_MODE=simulated
```

Simulated mode is deterministic: synthetic routes, a gazetteer of major US freight hubs, and
storms that drift across the map. The UI says when any data is simulated. Each variable also
accepts `off`, which disables that feature.

`backend/.env.example` documents every setting. The app checks them all at boot and refuses to
start with a list of what is wrong.

## Checks

```bash
# backend: tests, lint, format, types, architecture contracts, generated-types freshness
cd backend
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy .
.venv/bin/lint-imports
DJANGO_ENV=test .venv/bin/python manage.py export_ts --check

# frontend: prettier, eslint (incl. feature boundaries), tsc, vitest
cd frontend
pnpm check
```

After changing a backend DTO, regenerate the frontend's API types:

```bash
cd backend && DJANGO_ENV=test .venv/bin/python manage.py export_ts
```

## Deploying

The `Dockerfile` builds the frontend, then runs Django under gunicorn. Django serves the API
and the built app from one origin, with WhiteNoise for the hashed assets.

```bash
docker build -t truck-routing .
docker run -p 8000:8000 \
  -e SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  -e ALLOWED_HOSTS=localhost \
  truck-routing
```

The container defaults to `DJANGO_ENV=production`:

| Variable        | Value                                                                                                       |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| `SECRET_KEY`    | Required. 32+ random characters                                                                             |
| `ALLOWED_HOSTS` | Required. The public hostname(s), comma-separated. Optional on Render (see below)                           |
| `NUM_PROXIES`   | Proxy hops in front of the app (usually `1` on a PaaS), so rate limits see the client's IP, not the proxy's |

Any host that runs a Dockerfile and injects `PORT` works as-is (Render, Railway, Fly.io). Health
checks: `/healthz` for liveness, `/readyz` for readiness.

### Render

`render.yaml` is a Blueprint for one free Docker web service. In the Render dashboard choose
**New > Blueprint**, connect the repo, and apply. Render generates `SECRET_KEY`, sets
`NUM_PROXIES=1`, and checks `/readyz` before routing traffic. `ALLOWED_HOSTS` can stay unset:
the app trusts `RENDER_EXTERNAL_HOSTNAME`, which Render injects with the service's
`onrender.com` name. Add `ALLOWED_HOSTS` only when you attach a custom domain.

Free instances sleep after 15 minutes idle, so the first request after a pause takes a while.

## Layout

```
backend/
  common/    framework-free geometry helpers
  core/      kernel, config, errors, RPC builders, the single API
  modules/   geocoding, routing, weather, risk, trips
  server/    Django settings and URLs
  tests/
frontend/
  src/features/   trips, places, risk
  src/routes/     thin file routes
  src/integrations/  rpc client + generated types, query client, MapLibre
  test/
docs/architecture.md
```
