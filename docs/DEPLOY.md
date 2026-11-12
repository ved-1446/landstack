# Deploying the LandStack demo (Neon + Render + Vercel, all free tiers)

This puts the **fake-data demo** on the internet: the database on **Neon**, the API on **Render**, the website on **Vercel**. Nothing here is for real land records. No secret goes in the repository: you type each one into a dashboard.

```
visitor's browser ──► Vercel (the website, static files)
        │                         │  calls the API at VITE_API_URL
        └────────────────────────►│
                                  ▼
                        Render (the API, Docker) ──► Neon (Postgres + PostGIS)
```

## The two addresses people mix up (read this first)
| Variable | Lives on | Holds | Why |
|---|---|---|---|
| **`PUBLIC_BASE_URL`** | Render | the **Render API address**, e.g. `https://landstack-api.onrender.com` | It is printed into every passport's **QR code** as `{PUBLIC_BASE_URL}/verify/{document id}`. That page is served by the **API**, so a phone that scans the QR code must reach the API. If you leave it at `http://localhost:8000`, every PDF from the live demo has a dead QR code. |
| **`CORS_ORIGINS`** | Render | the **Vercel address**, e.g. `https://landstack.vercel.app` | It lists the websites that may call the API from a browser. Several are allowed, separated by commas (for example your Vercel address and a custom domain). No `*`, no path, no trailing space. |
| **`VITE_API_URL`** | Vercel | the **Render API address** again | The website finds the API only through this. |

So: the **Render address goes in two places** (`PUBLIC_BASE_URL` on Render, `VITE_API_URL` on Vercel) and the **Vercel address goes in one** (`CORS_ORIGINS` on Render).

## What you need
- A GitHub account with this repository pushed to it (Render and Vercel both deploy from GitHub).
- Free accounts on Neon (<https://neon.tech>), Render (<https://render.com>) and Vercel (<https://vercel.com>).
- On your computer: Docker Desktop running with the `landstack-db` container up (its `psql` program is used to create the tables), and the project's `.venv`.

## The order of the steps
1. Make the database on **Neon**.
2. Create the tables and the fake data in it, **from your computer**.
3. Make the API on **Render**.
4. Make the website on **Vercel**.
5. Go back to Render and fill in the two addresses.
6. Check that everything works.

The reason for this order: Vercel needs the Render address, and Render needs the Vercel address, so each is filled in after the other exists.

---

## 1. Neon (database)
1. Create a project. Pick the region nearest to your Render region (both have Europe, US and Asia options).
2. Choose **PostgreSQL 16 or 17**. PostGIS is available on Neon; `db/schema.sql` runs `CREATE EXTENSION IF NOT EXISTS postgis;` itself.
3. Open **Connection details**. Turn **Connection pooling OFF** (so you get the *direct* address, without `-pooler` in the host name) and copy the string. It looks like
   `postgresql://USER:PASSWORD@ep-something-123456.eu-central-1.aws.neon.tech/neondb?sslmode=require`
   Why direct: the API opens one short connection per request and uses ordinary prepared statements, which a pooled address can interfere with.
4. Treat that string like a password. Do not paste it into a file in the repo, a chat or a screenshot.

### PostGIS 3.3 (Neon) vs 3.4 (your computer and CI)
The code uses only these PostGIS functions, all of which exist in PostGIS 2.x and later, so **none needs 3.4**: `ST_Area`, `ST_IsValid`, `ST_IsValidReason`, `ST_Union`, `ST_Intersects`, `ST_Overlaps`, `ST_Covers`, `ST_Intersection`, `ST_Difference`, `ST_Equals`, `ST_Dump`, `ST_MakeEnvelope`, `ST_SimplifyPreserveTopology`, `ST_GeomFromText`, `ST_GeomFromGeoJSON`, `ST_AsGeoJSON`, plus `geography` casts and GiST indexes. One thing to know: the exact digits of an area or an intersection can differ in the very last decimals between GEOS versions. The check in step 2 compares what the checks flag with `db/planted_truth.json`, which would show it.

## 2. Create the tables and the demo data on Neon (from your computer)
Run these in **PowerShell, in the repository folder**. The Neon address is put in an environment variable **for this one PowerShell window only**; it is never written to a file. Replace the quoted text with your own string from step 1.

```powershell
# 1) the Neon address, for this window only
$env:NEON_URL = "postgresql://USER:PASSWORD@ep-something-123456.eu-central-1.aws.neon.tech/neondb?sslmode=require"

# 2) the tables, using the psql program inside your local Docker database container (it only connects OUT to Neon)
Get-Content db/schema.sql | docker exec -i -e NEON_URL=$env:NEON_URL landstack-db sh -c 'psql "$NEON_URL" -v ON_ERROR_STOP=1 -q'

# 3) the 100 fake plots, then the four demo users (the Python scripts read DATABASE_URL)
$env:DATABASE_URL = $env:NEON_URL
.\.venv\Scripts\python.exe db\seed.py
.\.venv\Scripts\python.exe db\seed_users.py

# 4) proof: every check should flag exactly what was planted
.\.venv\Scripts\python.exe -m backend.app.checks

# 5) forget the address again
Remove-Item Env:DATABASE_URL, Env:NEON_URL
```
Expect: step 2 prints nothing (that is success; `ON_ERROR_STOP` stops at the first error); step 3 finishes without an error message; step 4 shows flagged = planted for all nine checks. If step 4 shows a difference, tell me which check: it would be a GEOS difference.

`db/seed.py` **clears the plots** it is pointed at. Run it only with the address of the database you mean.

> The demo accounts (`admin`, `officer`, `citizen1`, `citizen2`) have **public** passwords (they are in the README on purpose). Anyone on the internet can sign in as the demo admin. That is acceptable only because every record is fake and the admin pages are read-only. Never reuse these passwords anywhere.

## 3. Render (the API)
You can do this by hand, or let `render.yaml` (in the repository root) do most of it.

**With the blueprint:** Render dashboard → **New +** → **Blueprint** → pick the repository. Render reads `render.yaml`, makes the web service, generates `JWT_SECRET` for you and asks for the values marked `sync: false`.

**By hand:** **New +** → **Web Service** → pick the repository → then:
| Setting | Value |
|---|---|
| Language / runtime | **Docker** |
| Dockerfile path | `./backend/Dockerfile` |
| Docker build context | `.` (the repository root) |
| Instance type | **Free** |
| Health check path | `/health` |
| Region | the one nearest your Neon region |

**Environment variables on Render** (names and examples only; never paste real values into the repository):
| Name | Example value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://USER:PASSWORD@ep-…neon.tech/neondb?sslmode=require` | the **direct** Neon string from step 1. Required. If `sslmode` is missing the app adds `sslmode=require`. |
| `JWT_SECRET` | *(a long random string)* | **Required**: the app refuses to start without a real one. The blueprint generates it. By hand, make one with the PowerShell line below. |
| `JWT_EXPIRE_MINUTES` | `60` | how long a login lasts |
| `CORS_ORIGINS` | `https://landstack.vercel.app` | the **Vercel** address(es), comma-separated. Fill in after step 4 (put `http://localhost:5173` there for now if you like). |
| `PUBLIC_BASE_URL` | `https://landstack-api.onrender.com` | the **Render API** address (it goes into the QR codes). No trailing slash. Fill in once you know the address Render gave the service. |
| `TRUSTED_PROXY_HOPS` | `1` | how many proxies sit in front of the app (see below). `0` means "believe nobody". |
| `OPENROUTER_API_KEY` | *(empty)* | **Optional.** With no key the app works fully: explanations are written by code and say so. |
| `OPENROUTER_MODEL` | *(empty)* | optional, only with a key |
| `PORT` | *(set by Render)* | do not set it yourself |

Make a `JWT_SECRET` in PowerShell (prints 64 random characters; copy it into the Render dashboard, nowhere else):
```powershell
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
```

The first build takes several minutes: it installs the packages, **trains the "unusual plot" model** (generated data, fixed seed, same model every time) and **fetches the Land Guide's public pages** (about 7 requests, politely). If the pages cannot be fetched the build still succeeds and the Land Guide answers from the project's own glossary only. Render shows the build log; when it says "Your service is live", open `https://YOUR-SERVICE.onrender.com/health`: it should say `{"status":"ok","database":"ok"}`.

### `TRUSTED_PROXY_HOPS`: so visitors do not share one rate limit
Behind Render every request arrives from Render's proxy. If the app ignored that, **all visitors would share one login limit** (5 a minute) and the demo would lock itself. The proxy writes the visitor's address at the **right-hand end** of the `X-Forwarded-For` header. A visitor can write anything on the *left*, so the app counts from the right: with `TRUSTED_PROXY_HOPS=1` it believes only the last entry. Rules the app follows: `0` ignores the header; if the header is missing, too short or not an address it falls back to the connection address (a shared limit, never a free pass).
- **Never set it higher than the real number of proxies.** Too high would believe a forged entry. Too low is safe (you only get a shared limit).
- Start with `1`. **Check it** from two different networks (for example your home Wi-Fi and your phone's mobile data): make 6 wrong sign-in attempts on one. If the other still gets "wrong password" (not "too many requests"), visitors are told apart. If both are blocked, the proxy chain is longer than 1: try `2`, and repeat the test.
- Leave `FORWARDED_ALLOW_IPS` alone (default `127.0.0.1`). Setting it to `*` makes uvicorn believe the **left-most** entry, which a visitor can forge.

### Free tier: what to expect
- The service **falls asleep after about 15 minutes without a request**. The next visit takes **about a minute** to wake it. The website shows "The demo server is waking up, this can take about a minute" and tries again by itself.
- Neon's database also suspends when idle and wakes in a second or two.
- Memory: the API uses about **250 MB** at rest and about **315 MB** at its highest (measured in the Docker image; see the table below), inside Render's 512 MB.

## 4. Vercel (the website)
1. **Add New → Project** → import the repository.
2. **Root Directory:** `frontend`. Framework preset: **Vite** (Vercel detects it; `frontend/vercel.json` also sets it). Build command `npm run build`, output `dist`.
3. **Environment Variables** (Production, and Preview if you use previews):
| Name | Example value | Notes |
|---|---|---|
| `VITE_API_URL` | `https://landstack-api.onrender.com` | the **Render API** address, no trailing slash. This is the **only** place the website gets the API address from. A production build without it shows "This site was built without an API address" instead of calling a server that is not there. |
| `VITE_DEMO_ACCOUNTS` | `true` | shows the **Try a demo account** cards on the sign-in page. Correct for this public demo (the passwords are public and the data is fake). Use `false` for anything with real data. |
| `VITE_CARTO_KEY` | *(empty)* | optional free CARTO key for the map |
| `VITE_ESRI_KEY` | *(empty)* | optional Esri key for the satellite basemap |
4. **Deploy.** `frontend/vercel.json` rewrites every path to `index.html`, so a deep link such as `/verify` or `/app/plots` still works when you refresh or open it directly. (Files in `/assets` are served first and cached for a year; their names change with every build.)
5. Note the address Vercel gives you, for example `https://landstack.vercel.app`.

Variables starting with `VITE_` are **baked into the website at build time**. After changing one, redeploy.

## 5. Back to Render: the two addresses
Set `CORS_ORIGINS` to the Vercel address and `PUBLIC_BASE_URL` to the Render address (the table above), then let Render restart. Without `CORS_ORIGINS` the browser blocks every call ("CORS error" in the browser console, the website says it cannot reach the API).

## 6. Check it works
- [ ] `https://YOUR-API/health` says `{"status":"ok","database":"ok"}`.
- [ ] Open the Vercel address: the home page shows live counts (100 plots).
- [ ] Open `https://YOUR-SITE/verify` and press refresh: the page loads (deep links work).
- [ ] Sign in with the **Officer** demo card, open a red plot, download the **PDF passport**, scan its QR code with your phone: it opens the **Render** address and shows **MATCHES**.
- [ ] Sign in as `admin` → **System**: API, database, PostGIS "Running", AI explainer "Switched off" if you set no key. **Insights** shows the 12 signals.
- [ ] Sign in as `citizen1`: only 3 plots; the **Map** tab shows only those.
- [ ] Wait 20 minutes, then open the site: you see the "waking up" note, then it works.

## Troubleshooting
| What you see | Most likely cause |
|---|---|
| Browser console: "blocked by CORS policy" | `CORS_ORIGINS` on Render does not contain the exact Vercel address (https, no trailing slash, no path). |
| The website says "built without an API address" | `VITE_API_URL` was not set when Vercel built it. Set it and redeploy. |
| QR code opens `localhost` or a dead page | `PUBLIC_BASE_URL` on Render is still the default. Set it to the Render address. |
| "Too many requests" for everyone at once | `TRUSTED_PROXY_HOPS` is `0` (everyone shares the proxy's address) or too low. |
| `/health` says `database: error` | `DATABASE_URL` wrong, or the Neon project is paused for the month. Check the string; use the direct (non-pooler) one. |
| Render build fails while installing | read the log; the first lines of the failing step say which package. Tell me and I will fix the version. |
| "waking up" for more than 2 minutes | Render is down or the build failed; open the Render logs. |
| Demo cards missing on the sign-in page | `VITE_DEMO_ACCOUNTS` is not exactly `true`, or the site was not redeployed after you set it. |

## Measured numbers (the Docker image, run locally)
Image `landstack-api` built from `backend/Dockerfile`: **869 MB on disk** (uncompressed; Render pulls it compressed). Running with the real database, AI off, as the non-root user `app`:

| Moment | Memory (resident set of the API process) |
|---|---|
| Idle, just started | **248 MB** (Docker's own "working set" figure: 181 MiB) |
| After a sign-in, the plot list and a passport (the sign-in uses ~64 MB briefly for password hashing) | settles at **251 MB**; highest moment **313 MB** |
| After a normal PDF | **251 MB** |
| A PDF with Hindi and Marathi text | adds about **6 MB** (measured in a separate process: 56 MB to 62 MB) |
| After `/admin/insights` (SHAP over 100 plots) | **251 MB**, highest still 316 MB; the SHAP libraries are loaded at start-up, and the answer is cached for 5 minutes |

That is under the 400 MB target and leaves headroom inside Render's 512 MB free instance. Nothing about scoring was changed to get there.

## Rolling back, and costs
- **Render** keeps previous deploys: **Events → Rollback**. **Vercel** keeps every deploy: **Deployments → … → Promote to Production**.
- To take the demo down: delete the Render service and the Vercel project, and delete the Neon project (it holds only fake data).
- All three free tiers have monthly limits (Render's free instance hours, Neon's compute hours, Vercel's bandwidth). A demo with a few visitors stays well inside them; check each dashboard if you expect a crowd.
