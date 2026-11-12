# A 3-minute tour (8 clicks)

Everything here is **fake demo data**. Set it up with the quick start in the README first (`scripts/setup.ps1` or `scripts/setup.sh`),
start the API and the web app, and open <http://localhost:5173>.

On the **live demo** (<https://landstack-one.vercel.app>) the first visit after a quiet spell can take about a minute while the free server wakes up.

The login screen shows two role cards (Citizen, Officer) only when `frontend/.env` has `VITE_DEMO_ACCOUNTS=true` (the setup script writes it; the live demo has it on).
Without it, type the username and password from the README. **These passwords are public. Never use them anywhere real.** The admin console is available when you run the project locally (its local-only login is in the README's local-setup section), or with credentials the owner shares.

| Account | Role | Sees |
|---|---|---|
| `officer` | officer | all 100 plots and passports |
| `citizen1` | citizen | only its own 3 plots |

## The tour
1. **Check a plot without signing in.** On the home page click an example chip, or type `MH000100000006`, in the **Check a plot** card. You get its village (Hinjewadi) and its band, **HIGH RISK · RED**, and nothing else: that is all the public may see.
2. **Sign in as `officer`.** Click **Sign in**, then the Officer card (or type `officer` and its password). You land on the **dashboard**: counts (green 58, amber 29, red 13), the problems found by each of the nine checks, a map preview and the ten riskiest plots.
3. **Open a red plot.** Click the first plot in the priority queue (or open **Plots** and search `MH000100000006`). The **land passport** shows a score of 100, the note **"Score is capped at 100"** (the findings add up to 110), and each finding with its evidence and rule.
4. **Download the printable passport.** Press **Download PDF passport**. A one-page A4 PDF is saved and the toast shows its **Document id**.
5. **Check the paper.** Press **Verify** (or open **Verify a passport** from the home page) and enter the document id. A small page says **MATCHES**: the records are still what was printed. Any change to the records would turn it into **HAS CHANGED**.
6. **See it on the map.** Open **Map**, search `MH000200000021`, open **Layers** and switch on **Unrecorded construction (simulated)**. A lavender outline labelled **SIMULATED** shows a "new building" that is not in the records. (There is no real satellite imagery in this project: see the README.)
7. **Ask for a plain-words explanation in another language.** On a passport pick **हिन्दी** or **मराठी**, then press **Explain in plain words**. With no AI key set you get an explanation written by code, labelled as such. Then press the **Land Guide** button at the bottom right and ask "What is a ULPIN?". Try the **sun/moon** button in the top bar to switch between the dark and the light theme.
8. **See what a citizen sees.** Sign out (the account button, top right), sign in as `citizen1`: only 3 plots, in plain words. Open a plot that is not theirs, `MH000100000006`, and you get "not found", the same as for a plot that does not exist. If you run the project locally you can also sign in as the local admin (see the README) and open the **Audit log** and **System**.

## Things to try next
- **Plots** (officer) has search, a filter for any mix of bands, a village filter and sortable columns.
- **Conflicts**, **Construction** and **Zones** show the data behind the dashboard.
- The admin's **Insights** page (local runs) explains what the "unusual plot" model pays attention to (explanation only: scores are set by code).
- Switch the basemap between Light, Dark and Satellite in the map's **Layers** panel.
- Open `http://localhost:8000/docs` for the API, and `docs/samples/` for ready-made PDFs.
