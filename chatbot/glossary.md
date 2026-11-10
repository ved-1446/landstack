# LandStack glossary

This glossary is original text written for LandStack. It explains what the words in a LandStack land passport mean. LandStack is a demo: its plots, owners and records are made up, and nothing in it is an official record or legal advice.

## What is a ULPIN?

A ULPIN is a Unique Land Parcel Identification Number: a short code that identifies one piece of land, so that the same parcel can be found in different records. In India the national scheme describes it as a 14-character alphanumeric code, and it is also called Bhu-Aadhaar. In LandStack every plot has a made-up ULPIN such as MH000100000001, which is used to search for a plot and to print on its passport.

## What is a land passport in LandStack?

A land passport is LandStack's one-page summary of a plot. It shows the plot's facts, its three records (the land record, the registration and the tax record), a risk score and the list of findings that explain the score. LandStack can also print the passport as a PDF with a QR code. Anyone can scan the code to check whether the records still match what was printed.

## What is a finding?

A finding is one problem that LandStack's checks found on a plot. Each kind of finding adds a fixed number of points to the risk score. The checks are plain rules written in code; no AI decides them and no AI can change them. A plot can have several findings, and the points are added together.

## The risk score and the bands

The score is the sum of the points of all findings, and it stops at 100. A plot with no findings scores 0. The score is shown with a band: green for 0 to 24 (low risk), amber for 25 to 59 (watch), and red for 60 and above (high risk). The band is always written in words as well as colour.

## Boundary overlap (40 points)

A boundary overlap means the mapped outline of a plot shares ground with another plot, lies inside another plot, has another plot inside it, or is identical to another plot. Two plots that only touch along an edge do not count. LandStack ignores overlaps smaller than 5 square metres, which is the size of surveying noise. Overlaps usually point to a survey mistake or a boundary dispute.

## Restricted zone clash (30 points)

A restricted zone clash means more than 20 percent of the plot lies inside a restricted zone, such as a forest, a river buffer, a defence area or a flood plain. Building or selling land inside such zones is often limited, so this finding asks a person to look.

## Area mismatch (25 points)

An area mismatch means the area written in the land record differs from the area measured on the map by more than 10 percent. Either the record or the map may be wrong, so the finding does not say which.

## Owner mismatch (25 points)

An owner mismatch means the owner named in the land record and the owner named in the registration do not look like the same person. LandStack compares the two names in a forgiving way, so different spellings, a different word order or a dropped initial still count as the same person. A real owner mismatch can mean the land changed hands without the record being updated.

## Duplicate survey number (20 points)

A duplicate survey number means another plot in the same village uses the same survey number. A survey number is meant to be unique inside a village, so a repeat can point to a data-entry error or a double registration.

## Invalid boundary (15 points)

An invalid boundary means the plot's outline is not a proper shape, for example the line crosses itself like a bow tie. The area and overlaps of such a shape cannot be measured reliably, so LandStack flags it instead of repairing it, and skips its other map checks.

## Tax overdue (15 points)

Tax overdue means the property tax was last paid more than 2 years before LandStack's reference date, 1 January 2026. It is a sign that the record may be neglected or that dues are unpaid.

## Missing record (10 points per record)

A missing record means one of the plot's three records is not on file: the land record, the registration or the tax record. Each missing record adds 10 points.

## Simulated unrecorded construction (15 points)

Unrecorded construction means a new building appears in a later survey snapshot that is not in an earlier one. In LandStack this is simulated: the two snapshots, called T0 (earlier) and T1 (later), are generated demo data and there is no real satellite or aerial imagery behind them. The check subtracts the old buildings from the new ones and flags a plot when at least 30 square metres of new building remain. Small shifts of a building between snapshots are ignored because surveys are never perfectly exact. The word SIMULATED is shown wherever this finding appears.

## What does the Unusual chip mean?

The Unusual chip is a statistical hint, not a finding. A model compared the plot's numbers with other plots and found it rare. It is not a conflict, it adds no points and it never changes the band.

## Can the explanations and the guide be wrong?

Yes. The plain-words explanation only rewrites the findings that already exist, and the Land Guide answers from a small set of public pages and this glossary. Both can be wrong or out of date. Both are general information and not legal advice. For a real land matter, check with the official land-records office or a qualified professional.
