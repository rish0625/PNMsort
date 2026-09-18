import csv
import random

SLOTS = [
    "Monday 6:00 PM", "Monday 6:20 PM", "Monday 6:40 PM",
    "Monday 7:00 PM", "Monday 7:20 PM", "Monday 7:40 PM",
    "Tuesday 6:00 PM", "Tuesday 6:20 PM", "Tuesday 6:40 PM",
    "Tuesday 7:00 PM", "Tuesday 7:20 PM", "Tuesday 7:40 PM",
]

FIRST = ["John", "Sarah", "Mike", "Alex", "Ryan", "David", "Emily", "Josh",
         "Chris", "Daniel", "Nathan", "Kevin", "Brandon", "Tyler", "Jordan",
         "Marcus", "Andrew", "Patrick", "Samuel", "Eric", "Victor", "Omar",
         "Luis", "Peter", "Grant", "Devin", "Aaron", "Caleb"]
LAST = ["Smith", "Doe", "Johnson", "Nguyen", "Patel", "Garcia", "Brown",
        "Lee", "Martinez", "Davis", "Clark", "Rivera", "Hall", "Walsh",
        "Kim", "Osei", "Reed", "Stone", "Foster", "Ibrahim", "Cole",
        "Barnes", "Ortiz", "Dunn", "Vega", "Hayes", "Pike", "Ward"]


def names(n, rng):
    out = []
    for i in range(n):
        out.append("{} {}".format(FIRST[i % len(FIRST)], LAST[i % len(LAST)]))
    assert len(set(out)) == n
    return out


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Timestamp", "Name", "Interview Availability"])
        for i, (name, avail) in enumerate(rows):
            writer.writerow(["9/17/2026 14:{:02d}".format(i % 60), name,
                             ", ".join(avail)])


def generous(n, rng, pool=SLOTS, low=4, high=7):
    rows = []
    for name in names(n, rng):
        k = rng.randint(low, high)
        rows.append((name, sorted(rng.sample(pool, k), key=SLOTS.index)))
    return rows


rng = random.Random(11)

# Example / Test 1: 24 PNMs, plenty of availability
write("PNM_Availability.csv", generous(24, rng))

# Test 2: 24 PNMs, tight availability -> most random groupings fail
tight_rng = random.Random(5)
tight = []
for i, name in enumerate(names(24, tight_rng)):
    home = SLOTS[i % 6]
    extra = tight_rng.choice([s for s in SLOTS if s != home])
    tight.append((name, sorted({home, extra}, key=SLOTS.index)))
write("test_tight.csv", tight)

# Tests 5 and 6: 24 PNMs who only ever selected the first three slots
three_rng = random.Random(3)
three = SLOTS[:3]
write("test_3slots.csv", [
    (name, sorted(three_rng.sample(three, three_rng.randint(2, 3)),
                  key=SLOTS.index))
    for name in names(24, three_rng)
])

# Test 3: 25 PNMs
write("test_25.csv", generous(25, rng))

# Test 4: a PNM with no availability
rows = generous(24, rng)
rows[7] = (rows[7][0], [])
write("test_no_availability.csv", rows)

# Test 5: not enough slots (handled by overriding INTERVIEW_SLOTS in the test)
write("test_28.csv", generous(28, rng))

# Test: bad availability value
rows = generous(24, rng)
rows[3] = (rows[3][0], ["Monday 6:00 PM", "Wednesday 9:00 PM"])
write("test_bad_value.csv", rows)

# Test: duplicate names
rows = generous(24, rng)
rows[5] = (rows[4][0], rows[5][1])
write("test_duplicate.csv", rows)

# Test: comma inside the option text, and range-style options
rows = []
for name, avail in generous(24, rng):
    rows.append((name, ["{} - 6:20 PM".format(a) for a in avail]))
write("test_ranges.csv", rows)

print("example files written")
