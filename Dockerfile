# One image, one process: Django serves the RPC API and the built React app.
#
#   docker build -t weather-aware-truck-routing .
#   docker run -p 8000:8000 \
#     -e SECRET_KEY=<32+ random chars> -e ALLOWED_HOSTS=<public hostname> \
#     weather-aware-truck-routing
#
# Production refuses to boot without SECRET_KEY and ALLOWED_HOSTS (see backend/.env.example).
# Routing, geocoding and weather default to the live public APIs, which need no keys.

# ---- Frontend: compile the React app to static files -------------------------------
FROM node:24-slim AS frontend
WORKDIR /app/frontend
# package.json pins pnpm through "packageManager"; corepack installs exactly that version.
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# ---- Runtime: the Django app behind gunicorn ---------------------------------------
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_ENV=production \
    DEBUG=false \
    PORT=8000
WORKDIR /app/backend

# Runtime dependencies only; the dev tooling in requirements-dev.txt stays out of the image.
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
# Settings default FRONTEND_DIST_DIR to ../frontend/dist, i.e. /app/frontend/dist here.
COPY --from=frontend /app/frontend/dist /app/frontend/dist
# Index the hashed assets into STATIC_ROOT so WhiteNoise serves them from one directory.
# Run as development: production would demand runtime secrets that a build never has.
RUN DJANGO_ENV=development python manage.py collectstatic --noinput

RUN useradd --system --uid 10001 app
USER app

EXPOSE 8000
# Hosts like Render, Railway and Fly inject PORT; the app logs its own access lines.
# The system user has no home directory, so gunicorn's control socket (gunicornc, which
# nothing in a container uses) has nowhere to live; turn it off instead of logging an error.
CMD ["sh", "-c", "exec gunicorn server.wsgi --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --timeout 60 --no-control-socket"]
