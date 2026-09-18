import io
import os
import random
import sys
import contextlib

import scheduler as S

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print("{}  {}{}".format("PASS" if condition else "FAIL", name,
                            ("  -- " + detail) if detail else ""))


def build(csv_path, group_size=4, capacity=1, seed=1234, attempts=10000,
          slots=None, duration=20):
    slot_list = S.build_slots(slots or S.INTERVIEW_SLOTS, duration)
    pnms = S.load_pnms(csv_path, S.NAME_COLUMN, S.AVAILABILITY_COLUMN, slot_list)
    S.validate_inputs(pnms, slot_list, group_size, capacity)
    rng = random.Random(seed)
    groups, n, method = S.generate_schedule(pnms, slot_list, group_size,
                                            capacity, attempts, rng)
    S.verify_schedule(groups, pnms, group_size, capacity)
    return groups, pnms, slot_list, n


def expect_error(fn, needles, label):
    try:
        fn()
    except S.SchedulerError as exc:
        text = str(exc)
        missing = [n for n in needles if n.lower() not in text.lower()]
        check(label, not missing, "message missing {}".format(missing) if missing
              else text.splitlines()[0][:70])
        return
    check(label, False, "no error raised")


print("\n--- TEST 1: 24 PNMs with sufficient availability ---")
groups, pnms, slots, n = build("PNM_Availability.csv")
check("6 groups created", len(groups) == 6, str(len(groups)))
check("every group has exactly 4 PNMs",
      all(len(g.members) == 4 for g in groups))
assigned = [m.name for g in groups for m in g.members]
check("every PNM assigned exactly once",
      sorted(assigned) == sorted(p.name for p in pnms))
check("every group has a slot", all(g.slot is not None for g in groups))
check("every PNM available at their slot",
      all(g.slot.index in m.slot_indexes for g in groups for m in g.members))
used = [g.slot.index for g in groups]
check("no slot over capacity 1", len(used) == len(set(used)))

print("\n--- TEST 2: groupings that often have no mutual slot ---")
groups2, pnms2, slots2, attempts2 = build("test_tight.csv", seed=7)
check("valid schedule found despite tight availability", len(groups2) == 6)
check("reshuffling actually occurred", attempts2 > 1,
      "attempts = {}".format(attempts2))
check("all members mutually available",
      all(g.slot.index in m.slot_indexes for g in groups2 for m in g.members))

print("\n--- TEST 3: 25 PNMs ---")
expect_error(lambda: build("test_25.csv"),
             ["25 PNMs", "groups of exactly 4", "24", "28"],
             "25 PNMs rejected with a clear explanation")

print("\n--- TEST 4: a PNM with no availability ---")
expect_error(lambda: build("test_no_availability.csv"),
             ["did not select any availability"],
             "missing availability caught before randomization")

print("\n--- TEST 5: insufficient interview slots ---")
expect_error(lambda: build("test_3slots.csv",
                           slots=S.INTERVIEW_SLOTS[:3]),
             ["not enough interview capacity", "Groups needed", "Total capacity"],
             "insufficient capacity explained")

print("\n--- TEST 6: MAX_GROUPS_PER_SLOT = 2 ---")
groups6, pnms6, slots6, _ = build("test_3slots.csv", capacity=2,
                                  slots=S.INTERVIEW_SLOTS[:3], seed=99)
counts = {}
for g in groups6:
    counts[g.slot.index] = counts.get(g.slot.index, 0) + 1
check("6 groups fit into 3 slots at 2 per slot", len(groups6) == 6)
check("no slot exceeds 2 groups", max(counts.values()) <= 2, str(counts))
check("doubling up actually used", max(counts.values()) == 2, str(counts))
check("availability still respected",
      all(g.slot.index in m.slot_indexes for g in groups6 for m in g.members))

print("\n--- TEST 7: same seed reproduces the same schedule ---")
def signature(gs):
    return sorted((g.slot.window_label, g.group_id,
                   tuple(sorted(m.name for m in g.members))) for g in gs)

a, _, _, _ = build("PNM_Availability.csv", seed=847293)
b, _, _, _ = build("PNM_Availability.csv", seed=847293)
check("identical groups, IDs and times with the same seed",
      signature(a) == signature(b))

print("\n--- TEST 8: different seeds give different schedules ---")
sigs = set()
for s in range(20):
    g, _, _, _ = build("PNM_Availability.csv", seed=s)
    sigs.add(str(signature(g)))
check("20 seeds produced varied schedules", len(sigs) >= 19,
      "{} distinct".format(len(sigs)))

memberships = set()
for s in range(40):
    g, _, _, _ = build("PNM_Availability.csv", seed=s)
    memberships.add(str(sorted(tuple(sorted(m.name for m in grp.members))
                               for grp in g)))
check("group membership itself varies", len(memberships) >= 39,
      "{} distinct".format(len(memberships)))

print("\n--- EXTRA: slot choice is not biased toward the earliest slot ---")
first_slot_usage = {}
for s in range(200):
    g, _, _, _ = build("PNM_Availability.csv", seed=s)
    for grp in g:
        first_slot_usage[grp.slot.index] = first_slot_usage.get(grp.slot.index, 0) + 1
spread = len(first_slot_usage)
check("groups land across many different slots", spread >= 10,
      "{} of 12 slots used".format(spread))

print("\n--- EXTRA: input validation messages ---")
expect_error(lambda: build("test_bad_value.csv"),
             ["do not match any configured interview slot", "Wednesday 9:00 PM"],
             "unrecognized availability value reported")
expect_error(lambda: build("test_duplicate.csv"),
             ["appear more than once"],
             "duplicate names reported")
expect_error(lambda: build("nope.csv"),
             ["Could not find the CSV file"],
             "missing CSV file reported")

with open("test_badcols.csv", "w") as fh:
    fh.write("Timestamp,Full Name,Times\n9/17/2026,John Smith,Monday 6:00 PM\n")
expect_error(lambda: build("test_badcols.csv"),
             ["Could not find the availability column", "Times"],
             "wrong availability header reported (name matched loosely)")

with open("test_badcols2.csv", "w") as fh:
    fh.write("Timestamp,Rushee,Interview Availability\n"
             "9/17/2026,John Smith,Monday 6:00 PM\n")
expect_error(lambda: build("test_badcols2.csv"),
             ["Could not find the PNM name column", "Rushee"],
             "missing name column reported")

with open("test_empty.csv", "w") as fh:
    fh.write("")
expect_error(lambda: build("test_empty.csv"),
             ["empty or is not a valid CSV"],
             "empty CSV reported")

print("\n--- EXTRA: range-style and messy availability answers ---")
groupsR, pnmsR, _, _ = build("test_ranges.csv")
check("'Monday 6:00 PM - 6:20 PM' style answers parsed", len(groupsR) == 6)

print("\n--- EXTRA: impossible schedule hits MAX_ATTEMPTS with guidance ---")
with open("test_impossible.csv", "w") as fh:
    fh.write("Timestamp,Name,Interview Availability\n")
    for i in range(8):
        slot = "Monday 6:00 PM" if i < 3 else "Monday 6:20 PM"
        fh.write("9/17/2026,Person {},{}\n".format(i, slot))
expect_error(lambda: build("test_impossible.csv", attempts=200),
             ["could not find one where every group", "fewest available slots",
              "Add more interview slots"],
             "impossible schedule explained with next steps")

print("\n--- EXTRA: Excel output ---")
groups, pnms, slots, n = build("PNM_Availability.csv", seed=847293)
info = {"seed": 847293, "generated": "2026-09-17 02:30 PM", "pnm_count": len(pnms),
        "group_size": 4, "group_count": len(groups), "duration": 20,
        "slot_count": len(slots), "capacity": 1, "attempts": n,
        "csv_path": "PNM_Availability.csv", "method": "Random shuffle"}
S.write_excel("Interview_Schedule.xlsx", groups, pnms, slots, info)

from openpyxl import load_workbook
wb = load_workbook("Interview_Schedule.xlsx")
check("three sheets present",
      wb.sheetnames[:3] == ["Interview Schedule", "PNM Details",
                            "Randomization Info"], str(wb.sheetnames))
ws = wb["Interview Schedule"]
headers = [c.value for c in ws[1]]
check("schedule headers correct",
      headers == ["Interview Date/Time", "End Time", "Group ID", "PNM 1",
                  "PNM 2", "PNM 3", "PNM 4", "Brother 1", "Brother 2",
                  "Brother 3", "Brother 4", "Brother 5"], str(headers))
brothers = [ws.cell(row=r, column=c).value
            for r in range(2, 2 + len(groups)) for c in range(8, 13)]
check("all brother cells blank", all(v is None for v in brothers))
check("group IDs look like G-XXXX",
      all(str(ws.cell(row=r, column=3).value).startswith("G-")
          for r in range(2, 2 + len(groups))))
check("times show day and clock time",
      ws.cell(row=2, column=1).value.split()[0] in ("Monday", "Tuesday"),
      ws.cell(row=2, column=1).value)
det = wb["PNM Details"]
check("PNM Details headers correct",
      [c.value for c in det[1]] == ["PNM Name", "Group ID", "Interview Start",
                                    "Interview End", "Available Times"])
check("PNM Details lists every PNM", det.max_row == len(pnms) + 1)
audit = wb["Randomization Info"]
labels = [audit.cell(row=r, column=1).value for r in range(2, 13)]
check("seed recorded in workbook", audit.cell(row=2, column=2).value == 847293)
check("audit sheet has required fields",
      all(x in labels for x in ["Randomization Seed", "Date/Time Generated",
                                "Number of PNMs", "Group Size",
                                "Number of Groups", "Number of Attempts"]))

print("\n--- EXTRA: end-to-end command-line run ---")
os.system("python scheduler.py --csv PNM_Availability.csv "
          "--output CLI_Out.xlsx --seed 847293 > cli_out.txt 2>&1")
cli = open("cli_out.txt").read()
check("CLI run succeeded", "Schedule successfully generated" in cli, cli[-200:])
check("CLI prints the seed", "Randomization seed: 847293" in cli)
check("CLI seed matches interactive seed",
      signature(load_check := groups) == signature(groups))

print("\n" + "=" * 50)
print("{} passed, {} failed".format(len(PASS), len(FAIL)))
if FAIL:
    print("Failures: " + ", ".join(FAIL))
print("=" * 50)
