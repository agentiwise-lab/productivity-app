#!/usr/bin/env bash
# =============================================================================
# productivity-app — commands & runbook
# =============================================================================
# This is a human runbook AND an LLM knowledge base. It is NOT meant to be
# executed top-to-bottom; copy the block you need. Every command assumes you are
# in the repo root (…/agentiwise/productivity-app) unless a `cd` says otherwise.
#
# ARCHITECTURE (very different from ad_analytics — read this first):
#   backend/   FastAPI (Python 3.11, managed by `uv`). ASGI app is
#              `backend.composition:app`. The ONLY place that reads env is
#              backend/composition.py. Runs behind Caddy/nginx in prod.
#   mobile/    Expo / React Native app (NOT a web frontend). Dev = Expo Go on a
#              phone or a simulator. Prod = an EAS build shipped to devices.
#              There is nothing to "deploy to a web server" for the client.
#   supabase/  Migrations only. The database is Supabase-managed Postgres
#              (project ref nmglxvlkterckxurrhnb). We use it as STORAGE ONLY —
#              no Supabase Auth. The backend owns auth end to end.
#   No Redis, no Prefect, no Docker in this repo (the prefect/ folder is empty).
#
# AUTH MODEL: the app signs its own JWTs. `AUTH_MODE=own` (production/real) vs
#   `AUTH_MODE=dev` (local shortcut that trusts an X-User-Id header). The JWT
#   `sub` = public.users.id = the Composio user_id, so every request is scoped
#   to the signed-in user, and each user connects their OWN Composio accounts.
#
# INTEGRATIONS: Composio managed OAuth (GitHub, Slack, Google Calendar, Linear,
#   Gmail, Google Docs). Composio owns the OAuth tokens; we store only a pointer
#   + status + provider identity in public.connections.
#
# EMAIL: OTP codes are sent via Loops. If Loops env is unset, the OTP is printed
#   to the backend log (so you can test signup locally with no email at all).
#
# Full deployment architecture & rationale: docs/deployment-plan.md
#   (Caddy + sslip.io gives free HTTPS on the raw EC2 IP — no domain needed).
# =============================================================================


# =============================================================================
# 0. ONE-TIME PREREQUISITES (local dev machine)
# =============================================================================
# - uv (Python package/venv manager):   curl -LsSf https://astral.sh/uv/install.sh | sh
# - Node 22+ and npm (for the mobile app).
# - Expo Go app on your phone (App Store / Play Store) for on-device dev.
# - Xcode (for the iOS simulator) — optional.
# Versions this repo was built against: Python 3.11, uv 0.8, Node 22.


# =============================================================================
# 1. LOCAL DEV — BACKEND
# =============================================================================
# Install deps into .venv (reads pyproject.toml + uv.lock):
uv sync

# --- Run the backend --------------------------------------------------------
# IMPORTANT: composition.py only builds the ASGI app when APP_EAGER_START is set
# (otherwise `backend.composition:app` is None and every request 500s). So the
# canonical run command is:
APP_EAGER_START=1 uv run uvicorn backend.composition:app --host 0.0.0.0 --port 8000

# --host 0.0.0.0 (not 127.0.0.1) so a phone on the same wifi can reach it.
# Use 127.0.0.1 only if you exclusively test in the iOS simulator on this Mac.

# Save logs to a file while running (handy for reading the dev OTP, see §3):
APP_EAGER_START=1 uv run uvicorn backend.composition:app --host 0.0.0.0 --port 8000 \
  2>&1 | tee /tmp/productivity-backend.log

# If port 8000 is busy (you already have a server running), pick another:
lsof -iTCP:8000 -sTCP:LISTEN -n -P            # see who holds it
APP_EAGER_START=1 uv run uvicorn backend.composition:app --host 0.0.0.0 --port 8010


# =============================================================================
# 2. LOCAL DEV — MOBILE (Expo)
# =============================================================================
cd mobile
npm install

# Point the app at your backend. On a PHONE, localhost = the phone, so you MUST
# use the Mac's LAN IP. Find it:
ipconfig getifaddr en0                          # e.g. 192.168.0.104
# Then set mobile/.env:
#   EXPO_PUBLIC_API_URL=http://<MAC_LAN_IP>:8000     (e.g. http://192.168.0.104:8000)
#   EXPO_PUBLIC_AUTH_MODE=own                        (own = real login; dev = X-User-Id)
#   EXPO_PUBLIC_DEV_USER_ID=<a real uuid>            (only used when AUTH_MODE=dev)

# Start Expo (scan the QR with Expo Go, or press i for iOS sim / a for Android):
npx expo start
# If the phone can't connect, use a tunnel (works across networks/firewalls):
npx expo start --tunnel
cd ..


# =============================================================================
# 3. AUTH MODES & THE DEV OTP
# =============================================================================
# dev  mode: backend trusts `X-User-Id` header; no login. Mobile sends the header.
#            Good for UI work. NEVER use in production.
# own  mode: backend validates its own Bearer JWT; mobile shows the login flow.
#
# Backend .env: AUTH_MODE=own   |   Mobile mobile/.env: EXPO_PUBLIC_AUTH_MODE=own
# (the two are independent switches — keep them in sync).
#
# Reading the OTP locally WITHOUT Loops configured: it is logged. In the backend
# log look for a line like:  "LOOPS not configured; OTP for you@x.com is 123456".
grep -oE "OTP for .* is [0-9]{6}" /tmp/productivity-backend.log | tail -1


# =============================================================================
# 4. TESTS & TYPE CHECKS
# =============================================================================
uv run pytest -q                                 # backend (384+ tests)
uv run pytest tests/test_auth_service.py -q      # one file
cd mobile && npx tsc --noEmit && cd ..           # mobile type check

# --- Live smoke test of the whole own-mode flow (against real Supabase) ------
# Start the backend in own mode on :8010 first, then:
BASE=http://127.0.0.1:8010; EMAIL=you@example.com; PW=Testpass-12345
curl -s -X POST $BASE/auth/otp/send   -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\"}"
# read the code from the backend log, then:
curl -s -X POST $BASE/auth/otp/verify -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"code\":\"NNNNNN\"}"
curl -s -X POST $BASE/auth/register   -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"code\":\"NNNNNN\",\"password\":\"$PW\"}"
#   -> returns {access_token, refresh_token}. Then:
TOKEN=...; curl -s $BASE/feed -H "Authorization: Bearer $TOKEN"                 # 200
curl -s -X POST $BASE/connections/github/link -H "Authorization: Bearer $TOKEN"  # -> Composio URL


# =============================================================================
# 5. DATABASE / MIGRATIONS (Supabase)
# =============================================================================
# Migrations live in supabase/migrations/ (0001..0006). 0004/0005/0006 (own-auth
# + connections status) are ALREADY APPLIED to project nmglxvlkterckxurrhnb.
#
# Apply via Supabase CLI (if linked) — preferred for reproducibility:
#   supabase link --project-ref nmglxvlkterckxurrhnb
#   supabase db push
# Or paste a migration file into the Supabase dashboard SQL editor.
#
# The backend connects with the SERVICE ROLE key (bypasses RLS) and scopes every
# query by user_id in code. RLS is enabled deny-by-default; the advisories about
# "RLS enabled, no policy" are EXPECTED and intentional.


# =============================================================================
# 6. COMPOSIO SETUP (integrations)
# =============================================================================
# One managed-OAuth "auth config" per toolkit must exist; its id (ac_...) goes in
# a COMPOSIO_AUTH_CONFIG_* env var. These are ALREADY CREATED for this account:
#   github ac_MAJfI3IXTzZ2  | slack ac_Qf9iy2_Ih2fT | googlecalendar ac_ojwYFr0WZ94Y
#   linear ac_XC2u1Kn0h6Nj  | gmail ac_wwp8BHE4Yqtz | googledocs ac_KJqxuKTHd4cq
#
# To (re)create one programmatically (Python, uses COMPOSIO_API_KEY from .env):
#   from composio import Composio
#   c = Composio(api_key=...)
#   c.auth_configs.create(toolkit="notion", options={"type": "use_composio_managed_auth"})
# List existing:  c.auth_configs.list()
#
# WEBHOOK (real-time push ingestion — optional for basic use, needed for live
# feed updates): in the Composio dashboard set the webhook URL to
#   https://<BACKEND_PUBLIC_HOST>/webhooks/composio
# and put its signing secret in COMPOSIO_WEBHOOK_SECRET. Locally you can tunnel:
#   ngrok http 8000    # then use the ngrok https URL as the webhook target
#
# CALLBACK URL: COMPOSIO_CALLBACK_URL is where the user returns after OAuth.
# For the mobile app it is the app deep-link scheme (host-INdependent):
#   COMPOSIO_CALLBACK_URL=productivityapp://composio-callback
# (matches "scheme": "productivityapp" in mobile/app.json). In Expo Go the custom
# scheme may not auto-return; that's fine — the app polls /connections/{p}/status
# after the browser closes. A standalone/dev build deep-links back cleanly.


# =============================================================================
# 7. LOOPS SETUP (OTP email) — steps for a NEW, ISOLATED setup
# =============================================================================
# Do NOT reuse ad_analytics' Loops key/template — keep this app fully separate.
# Loops billing is per-ACCOUNT, so "separate credits" means a separate Loops
# account/workspace (or at least accept that sends count against your one plan).
#
# Steps:
#  1. Create/sign in to a Loops account for this app: https://loops.so
#  2. Verify your sending domain (or use Loops' default sender for testing).
#  3. Create a TRANSACTIONAL email:  Loops dashboard -> Transactional -> Create.
#     - Add a data variable named exactly:  otp
#     - In the body, reference it, e.g.:  "Your code is {{otp}}"
#     - Publish it and copy its Transactional ID (looks like clxxxxxxxx).
#  4. Get your API key:  Settings -> API -> create key.
#  5. Put both in the backend .env:
#       LOOPS_API_KEY=<key>
#       LOOPS_OTP_TRANSACTIONAL_ID=<transactional id>
#  6. Restart the backend. Now /auth/otp/send emails a real code instead of
#     logging it. (Unset either var again to fall back to console logging.)


# =============================================================================
# 8. ENVIRONMENT VARIABLES — REFERENCE (★ = changes per host / deployment)
# =============================================================================
# --- backend/.env -----------------------------------------------------------
#   AUTH_MODE=own                         # own (prod) | dev (local only)
#   AUTH_JWT_SECRET=<32+ random chars>    # our JWT signing secret. KEEP SECRET.
#   AUTH_JWT_ISSUER=productivity-app      # optional (defaults shown)
#   AUTH_JWT_AUDIENCE=app                 # optional
#   AUTH_ACCESS_TTL_MIN=15                # optional
#   AUTH_REFRESH_TTL_DAYS=30              # optional
#   OTP_TTL_MIN=10 / OTP_RESEND_COOLDOWN_SEC=60 / OTP_MAX_ATTEMPTS=5   # optional
#   LOOPS_API_KEY=...                     # optional (unset -> OTP logged)
#   LOOPS_OTP_TRANSACTIONAL_ID=...        # optional
#   SUPABASE_URL=... / SUPABASE_SERVICE_ROLE_KEY=... / SUPABASE_ANON_KEY=...
#   COMPOSIO_API_KEY=...
#   COMPOSIO_WEBHOOK_SECRET=...
#   COMPOSIO_AUTH_CONFIG_GITHUB / _SLACK / _GOOGLECALENDAR / _LINEAR / _GMAIL / _GOOGLEDOCS
#   COMPOSIO_CALLBACK_URL=productivityapp://composio-callback   # mobile scheme
# ★ CORS_ORIGINS=...                      # comma-separated allowed web origins.
#                                         # Native app needs none; the Expo WEB
#                                         # preview and any hosted web client do.
#   COMPOSIO_USER_ID=<uuid>               # legacy/dev fallback only; unused in own+Supabase
#
# --- mobile/.env ------------------------------------------------------------
# ★ EXPO_PUBLIC_API_URL=http://192.168.0.104:8000   # LOCAL: Mac LAN IP
#                                                    # PROD:  https://<ec2>.sslip.io
#   EXPO_PUBLIC_AUTH_MODE=own
#   EXPO_PUBLIC_DEV_USER_ID=<uuid>        # only when AUTH_MODE=dev
#
# --- Set in the Composio DASHBOARD, not env (★ per host) --------------------
# ★ Webhook target URL:  https://<BACKEND_PUBLIC_HOST>/webhooks/composio
#
# .env files are gitignored and NEVER committed. Set them per machine/host.


# =============================================================================
# 9. PRODUCTION — AWS EC2 (see docs/deployment-plan.md for the full rationale)
# =============================================================================
# Model: one small EC2 instance runs the FastAPI backend over HTTPS via Caddy +
# sslip.io (free auto-TLS on the raw IP, NO domain required). The mobile app is
# an EAS build that points at that HTTPS URL. Supabase stays managed (no change).
#
# The public backend host will look like:  https://<IP-WITH-DASHES>.sslip.io
#   e.g. instance 13.54.201.9  ->  https://13-54-201-9.sslip.io
#
# --- 9a. First-time server prep --------------------------------------------
#   ssh -i <key>.pem ec2-user@<EC2_IP>
#   sudo yum install -y git             # (Amazon Linux) or apt on Ubuntu
#   curl -LsSf https://astral.sh/uv/install.sh | sh      # install uv
#   git clone git@github-vicky81125:agentiwise-lab/productivity-app.git
#   cd productivity-app && uv sync
#   # Create backend .env on the server with the PROD values (see §8). Critically:
#   #   AUTH_MODE=own, a strong AUTH_JWT_SECRET, real Supabase + Composio keys,
#   #   CORS_ORIGINS set to your web origin(s) if any.
#   # If the box has <2GB RAM, add swap (see §12).
#
# --- 9b. Run the backend as a service (systemd) ----------------------------
#   Create /etc/systemd/system/productivity-backend.service :
#     [Unit]
#     Description=productivity-app backend
#     After=network.target
#     [Service]
#     WorkingDirectory=/home/ec2-user/productivity-app
#     EnvironmentFile=/home/ec2-user/productivity-app/.env
#     Environment=APP_EAGER_START=1
#     ExecStart=/home/ec2-user/.local/bin/uv run uvicorn backend.composition:app --host 127.0.0.1 --port 8000
#     Restart=always
#     User=ec2-user
#     [Install]
#     WantedBy=multi-user.target
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now productivity-backend
#   sudo systemctl status productivity-backend
#   journalctl -u productivity-backend -f            # logs (and the dev OTP)
#
# --- 9c. HTTPS in front (Caddy + sslip.io) ---------------------------------
#   Install Caddy, then /etc/caddy/Caddyfile :
#     13-54-201-9.sslip.io {
#         reverse_proxy 127.0.0.1:8000
#     }
#   sudo systemctl restart caddy
#   # Caddy fetches a Let's Encrypt cert for the sslip.io host automatically.
#   # Security group: open 80 + 443 inbound; keep 8000 closed to the world.
#
# --- 9d. Point the world at it ---------------------------------------------
#   ★ Composio dashboard webhook  -> https://13-54-201-9.sslip.io/webhooks/composio
#   ★ mobile/.env EXPO_PUBLIC_API_URL -> https://13-54-201-9.sslip.io  (then rebuild)
#   ★ backend .env CORS_ORIGINS -> add any web origin that will call the API
#
# --- 9e. Redeploy on new code ----------------------------------------------
#   ssh ec2-user@<EC2_IP>
#   cd /home/ec2-user/productivity-app && git pull && uv sync
#   sudo systemctl restart productivity-backend
#   # Apply any new DB migration via Supabase (§5) BEFORE the code that needs it.


# =============================================================================
# 10. MOBILE — PRODUCTION BUILD (EAS)
# =============================================================================
# The client is shipped to devices, not hosted. Before building, set
# mobile/.env EXPO_PUBLIC_API_URL to the PROD https backend URL (§9d).
cd mobile
npm install -g eas-cli            # once
eas login
eas build:configure              # once, creates eas.json
eas build --profile production --platform ios       # or android / all
# For internal testing without the stores: `eas build --profile preview`.
cd ..


# =============================================================================
# 11. DEV -> PRODUCTION CHECKLIST (what actually has to change)
# =============================================================================
#  [ ] backend .env: AUTH_MODE=own, strong unique AUTH_JWT_SECRET (NOT the dev one)
#  [ ] backend .env: real LOOPS_API_KEY + LOOPS_OTP_TRANSACTIONAL_ID (real email)
#  [ ] backend .env: CORS_ORIGINS = your real web origin(s)
#  [ ] backend running via systemd behind Caddy on HTTPS (§9)
#  [ ] Composio dashboard webhook -> https://<host>/webhooks/composio
#  [ ] mobile/.env EXPO_PUBLIC_API_URL -> https prod URL, then EAS build
#  [ ] DB migrations applied to Supabase (§5)
#  [ ] Secrets rotated / never committed; .env only on the box


# =============================================================================
# 12. OPS / TROUBLESHOOTING
# =============================================================================
# Every request 500s incl. /health  ->  you forgot APP_EAGER_START=1 (app is None).
# Phone can't reach backend         ->  backend must bind 0.0.0.0 AND EXPO_PUBLIC_API_URL
#                                        must be the Mac LAN IP, not localhost.
# 401 on every authed request       ->  AUTH_MODE mismatch (backend own vs mobile dev)
#                                        or AUTH_JWT_SECRET changed (old tokens die).
# OTP never arrives                 ->  Loops not set -> read it from the log (§3).
# Connect never confirms            ->  poll-based; ensure /connections/{p}/status is
#                                        reachable and the toolkit has an auth config (§6).
# See who holds a port:  lsof -iTCP:8000 -sTCP:LISTEN -n -P
# Add 2GB swap (small EC2):
#   sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
#   sudo mkswap /swapfile && sudo swapon /swapfile
#   echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
#   free -m
