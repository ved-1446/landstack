"""Build a labelled set of owner-name pairs to measure the name matcher.

    python -m ml.make_name_pairs          # writes ml/data/name_pairs.csv (committed: it is a small test asset)

label 1 = the two names are the same person, label 0 = different people. `kind` says which rule made the pair.
The pairs are made by RULES from a small pool of Maharashtrian names, with a fixed seed. Real-world names will
behave differently (more spellings, other scripts, typing mistakes, nicknames). Treat the numbers as a check
that the matcher does the sensible things, not as a promise about real records.
"""
import csv
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
PAIRS_FILE = DATA_DIR / "name_pairs.csv"
SEED = 9

FIRST_M = ["Ramesh", "Suresh", "Mahesh", "Anil", "Sanjay", "Rahul", "Amit", "Nitin", "Ganesh", "Deepak", "Prakash",
           "Vijay", "Rohit", "Sachin", "Dinesh", "Manoj", "Ajay", "Vikas", "Santosh", "Pradeep"]
FIRST_F = ["Sunita", "Anita", "Meena", "Kavita", "Savita", "Pooja", "Neha", "Swati", "Archana", "Rekha", "Sheela",
           "Vaishali", "Manisha", "Priya", "Asha"]
FIRST = FIRST_M + FIRST_F
SURNAMES = ["Kulkarni", "Deshpande", "Joshi", "Patil", "Shinde", "Jadhav", "Pawar", "Gaikwad", "More", "Bhosale", "Kale",
            "Chavan", "Salunkhe", "Thorat", "Jagtap", "Kamble", "Mane", "Sawant", "Lokhande", "Nikam", "Gore",
            "Ghadge", "Sharma", "Verma", "Gupta", "Naik", "Phadke", "Apte", "Bhide", "Gokhale"]
MIDDLE = ["Shankar", "Dattatray", "Ganpat", "Bhaskar", "Vishnu", "Madhav", "Raghunath", "Balkrishna", "Hari", "Namdev"]
HONORIFIC = ["Shri", "Smt", "Shri.", "Smt.", "Mr", "Mrs", "Dr"]

# The same person, written differently.
SPELLING = {"Kulkarni": ["Kulkarny", "Kulakarni"], "Deshpande": ["Deshpandey", "Deshpanday"], "Joshi": ["Joshee", "Joshy"],
            "Patil": ["Pateel", "Patill"], "Shinde": ["Shindey", "Shinday"], "Jadhav": ["Jadhao", "Jadhaw"],
            "Pawar": ["Powar", "Pavar"], "Gaikwad": ["Gaekwad", "Gayakwad"], "Bhosale": ["Bhosle", "Bhonsle"],
            "Chavan": ["Chavhan", "Chawan"], "Sawant": ["Savant", "Sawanth"], "Salunkhe": ["Salunke", "Salunkey"],
            "Thorat": ["Thorrat", "Thoraat"], "Nikam": ["Nikkam", "Nickam"], "Naik": ["Nayak", "Nayek"],
            "Phadke": ["Phadake", "Phadkay"], "Gokhale": ["Gokhle", "Gokhalay"],
            "Sunita": ["Sunitha", "Suneeta"], "Anita": ["Anitha", "Aneeta"], "Kavita": ["Kavitha", "Kaveeta"],
            "Savita": ["Savitha", "Saveeta"], "Pooja": ["Puja", "Poojaa"], "Mahesh": ["Maheesh", "Mahes"],
            "Rahul": ["Rahool", "Rahull"], "Vijay": ["Vijai", "Vijaye"], "Sanjay": ["Sanjai", "Sanjey"]}
# Different people whose names LOOK alike (hard negatives).
LOOKALIKE_SURNAME = [("Patil", "Patel"), ("Chavan", "Chauhan"), ("Jadhav", "Yadav"), ("Shinde", "Shende"),
                     ("Sharma", "Verma"), ("Naik", "Nair"), ("Deshpande", "Deshmukh"), ("Kulkarni", "Karnik"),
                     ("Sawant", "Sanap"), ("Bhosale", "Bhonde"), ("Salunkhe", "Salvi"), ("Thorat", "Thorve"),
                     ("Gore", "Gole"), ("Kale", "Kele"), ("Mane", "Mene"), ("Pawar", "Panwar"), ("Joshi", "Joshua")]
LOOKALIKE_FIRST = [("Anita", "Sunita"), ("Rahul", "Rohit"), ("Amit", "Ajit"), ("Suresh", "Ramesh"), ("Mahesh", "Ramesh"),
                   ("Vijay", "Vinay"), ("Nitin", "Nikhil"), ("Anil", "Anand"), ("Neha", "Meena"), ("Savita", "Kavita"),
                   ("Archana", "Aradhana"), ("Swati", "Sweta"), ("Sachin", "Satish"), ("Manoj", "Manish"),
                   ("Ajay", "Abhay"), ("Dinesh", "Mahesh"), ("Rekha", "Reshma"), ("Priya", "Pria")]


def _noise(rng, name):
    """The same name typed carelessly: case, commas, dots, spacing."""
    pick = rng.choice(["upper", "lower", "comma", "dots", "space", "title_lower"])
    words = name.split()
    if pick == "upper":
        return name.upper()
    if pick == "lower":
        return name.lower()
    if pick == "comma" and len(words) >= 2:
        return f"{words[-1]}, {' '.join(words[:-1])}"
    if pick == "dots":
        return ".".join(words) if len(words) == 2 else name.replace(" ", ". ")
    if pick == "space":
        return "  ".join(words)
    return " ".join(w.lower() if i else w for i, w in enumerate(words))


def _person(rng):
    return rng.choice(FIRST), rng.choice(SURNAMES)


class _Builder:
    def __init__(self):
        self.rng = random.Random(SEED)
        self.rows, self._seen = [], set()

    def add(self, a, b, label, kind):
        key = (frozenset((a, b)), label)
        if a == b and kind != "identical":
            return False
        if key in self._seen:
            return False
        self._seen.add(key)
        self.rows.append((a, b, label, kind))
        return True

    def make(self, kind, label, count, factory):
        made, tries = 0, 0
        while made < count and tries < count * 200:
            tries += 1
            pair = factory(self.rng)
            if pair and self.add(pair[0], pair[1], label, kind):
                made += 1
        if made < count:
            raise RuntimeError(f"could only make {made} of {count} '{kind}' pairs")


def build():
    b = _Builder()

    def order(rng):
        f, s = _person(rng)
        return f"{f} {s}", rng.choice([f"{s} {f}", f"{s}, {f}", f"{s} {f}"])

    def initial(rng):
        f, s = _person(rng)
        return f"{f} {s}", rng.choice([f"{f[0]}. {s}", f"{s} {f[0]}.", f"{f[0]} {s}", f"{s}, {f[0]}."])

    def middle_initial(rng):
        f, s = _person(rng)
        m = rng.choice(MIDDLE)
        return f"{f} {s}", rng.choice([f"{f} {m[0]}. {s}", f"{s} {f} {m[0]}.", f"{f} {m[0]} {s}"])

    def dropped_middle(rng):
        f, s = _person(rng)
        full = f"{f} {rng.choice(MIDDLE)} {s}"
        return full, rng.choice([f"{f} {s}", f"{s} {f}"])

    def spelling(rng):
        f, s = _person(rng)
        which = rng.random()
        f2 = rng.choice(SPELLING[f]) if f in SPELLING and which < 0.4 else f
        s2 = rng.choice(SPELLING[s]) if s in SPELLING and (which >= 0.4 or f2 == f) else s
        return (f"{f} {s}", f"{f2} {s2}") if (f2, s2) != (f, s) else None

    def honorific(rng):
        f, s = _person(rng)
        h = rng.choice(HONORIFIC)
        return f"{f} {s}", rng.choice([f"{h} {f} {s}", f"{h} {s} {f}", f"{h} {f} {s}"])

    def combined(rng):
        f, s = _person(rng)
        f2 = rng.choice(SPELLING[f]) if f in SPELLING and rng.random() < 0.5 else f
        s2 = rng.choice(SPELLING[s]) if s in SPELLING else s
        if (f2, s2) == (f, s):
            return None
        return f"{f} {s}", f"{rng.choice(HONORIFIC)} {s2} {f2[0] + '.' if rng.random() < 0.3 else f2}"

    def case_noise(rng):
        f, s = _person(rng)
        return f"{f} {s}", _noise(rng, f"{f} {s}")

    def identical(rng):
        f, s = _person(rng)
        return f"{f} {s}", f"{f} {s}"

    b.make("identical", 1, 20, identical)
    b.make("case_punctuation", 1, 30, case_noise)
    b.make("order", 1, 40, order)
    b.make("initial", 1, 40, initial)
    b.make("middle_initial", 1, 20, middle_initial)
    b.make("dropped_middle", 1, 30, dropped_middle)
    b.make("spelling", 1, 60, spelling)
    b.make("honorific", 1, 30, honorific)
    b.make("combined", 1, 30, combined)

    def same_surname(rng):
        s = rng.choice(SURNAMES)
        f1, f2 = rng.sample(FIRST, 2)
        return f"{f1} {s}", f"{f2} {s}"

    def lookalike_surname(rng):
        f = rng.choice(FIRST)
        s1, s2 = rng.choice(LOOKALIKE_SURNAME)
        return (f"{f} {s1}", f"{f} {s2}") if rng.random() < 0.5 else (f"{f} {s2}", f"{f} {s1}")

    def same_first(rng):
        f = rng.choice(FIRST)
        s1, s2 = rng.sample(SURNAMES, 2)
        return f"{f} {s1}", f"{f} {s2}"

    def lookalike_first(rng):
        s = rng.choice(SURNAMES)
        f1, f2 = rng.choice(LOOKALIKE_FIRST)
        return f"{f1} {s}", f"{f2} {s}"

    def different_middle(rng):
        f, s = _person(rng)
        m1, m2 = rng.sample(MIDDLE, 2)
        return f"{f} {m1} {s}", f"{f} {m2} {s}"

    def swapped_other(rng):
        f1, s1 = _person(rng)
        f2, s2 = _person(rng)
        if f1 == f2 or s1 == s2:
            return None
        return f"{f1} {s1}", f"{s2} {f2}"

    def different_honorific(rng):
        f1, s1 = _person(rng)
        f2, s2 = _person(rng)
        if f1 == f2 or s1 == s2:
            return None
        return f"{rng.choice(HONORIFIC)} {f1} {s1}", f"{rng.choice(HONORIFIC)} {f2} {s2}"

    def unrelated(rng):
        f1, s1 = _person(rng)
        f2, s2 = _person(rng)
        if f1 == f2 or s1 == s2:
            return None
        return f"{f1} {s1}", f"{f2} {s2}"

    b.make("same_surname", 0, 60, same_surname)
    b.make("lookalike_surname", 0, 40, lookalike_surname)
    b.make("same_first_name", 0, 50, same_first)
    b.make("lookalike_first_name", 0, 40, lookalike_first)
    b.make("different_middle_name", 0, 30, different_middle)
    b.make("swapped_other_person", 0, 30, swapped_other)
    b.make("different_honorific", 0, 20, different_honorific)
    b.make("unrelated", 0, 30, unrelated)
    return b.rows


def write(rows, path=PAIRS_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name_a", "name_b", "same_person", "kind"])
        w.writerows(rows)


def read(path=PAIRS_FILE):
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["name_a"], r["name_b"], int(r["same_person"]), r["kind"]) for r in csv.DictReader(f)]


def main():
    rows = build()
    write(rows)
    pos = sum(r[2] for r in rows)
    print(f"wrote {len(rows)} pairs to {PAIRS_FILE}: {pos} same person, {len(rows) - pos} different (seed {SEED})")


if __name__ == "__main__":
    main()
