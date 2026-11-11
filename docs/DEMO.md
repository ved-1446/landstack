# A 3-minute tour (8 clicks)

Everything here is **fake demo data**. Set it up with the quick start in the README first (`scripts/setup.ps1` or `scripts/setup.sh`),
start the API and the web app, and open <http://localhost:5173>.

The login screen shows the four demo accounts as buttons only when `frontend/.env` has `VITE_DEMO_ACCOUNTS=true` (the setup script writes it).
Without it, type the username and password from the table in the README. **These passwords are public. Never use them anywhere real.**

| Account | Role | Sees |
|---|---|---|
| `officer` | officer | all 100 plots and passports |
| `citizen1` | citizen | only its own 3 plots |

## The tour

1. **Sign in as `officer`.** Click the `officer` button, then **Sign in**. The map shows 100 plots coloured by risk, and the bar at the bottom counts them:
   green 58, amber 29, red 13.
2. **Open a red plot.** Type `MH000100000006` in the search box and press the orange arrow. The map flies there and the **land passport** opens:
   a score of 100 with the words "High risk, red band", the note **"Score is capped at 100"** (the four findings add up to 110) and the findings, each with its evidence and rule.
3. **Download the printable passport.** Scroll the drawer down and press **Download PDF passport**. A one-page A4 PDF is saved, and the toast shows its **Document id**.
4. **Check the paper.** Press **Verify** in the drawer (or open `http://localhost:8000/verify/<Document id>` in a browser). A small page says **MATCHES**:
   the records are still what was printed. (Any change to the records would turn it into **HAS CHANGED**.)
5. **Switch on the simulated construction layer.** Click the **Map layers** icon (the stack of squares, just under the logo in the left rail), turn on **Unrecorded construction (simulated)**, close the popover and search `MH000200000021`.
   A light-blue outline labelled **SIMULATED** shows a "new building" that is not in the records, and the passport lists it with a **Simulated** chip. (There is no real satellite imagery in this project: see the README.)
6. **Ask for a plain-words explanation, in another language.** In the same drawer pick **हिन्दी** or **मराठी**, then press **Explain in plain words**. With no AI key set in `.env` you get an explanation written by code, labelled as such.
   With a key, the English explanation is checked and then machine-translated.
7. **Ask the Land Guide.** Press **Ask the Land Guide** (bottom right) and ask "What is a ULPIN?". It answers only from its small list of public pages (with links) or says "I don't know from my sources."
8. **See what a citizen sees.** Sign out (account icon, bottom of the left rail), sign in as `citizen1`. The dock says "Showing 3 plots". Open `MH000100000001`: the overlapping plot is not named or drawn, because it is not theirs.
   Now search `MH000100000006` (a plot that is not theirs): "not found", the same answer as for a plot that does not exist.

## Things to try next
- **Filters** (the sliders icon in the rail) show how many plots have each kind of problem.
- The **Passports** list (staff only) lets you search and sort every plot.
- Switch the basemap between Light, Dark and Satellite in the layers popover.
- Open `http://localhost:8000/docs` for the API, and `docs/samples/` for ready-made PDFs.
