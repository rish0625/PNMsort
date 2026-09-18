# Fraternity Interview Scheduler

Randomly groups PNMs into groups for 20-minute group interviews,
using only the availability they submitted. Outputs an Excel file with the
groups, their interview times, and five blank Brother columns for you to fill
in by hand.

## Files

| File | What it is |
|---|---|
| `scheduler.py` | The program. This is the only file you need to run. |
| `requirements.txt` | The one library it depends on (`openpyxl`). |
| `PNM_Availability.csv` | Example input with 24 PNMs, in Google Forms export format. |
| `make_examples.py` | Optional. Regenerates the example CSV and test fixtures. |
| `run_tests.py` | Optional. Runs the 40 checks described under "Testing". |

## 1. Installing dependencies

Install Python 3.8 or newer from python.org, then open Terminal (Mac) or
Command Prompt (Windows), move to the folder holding these files, and run:

```
pip install -r requirements.txt
```

If `pip` isn't found, try `python -m pip install -r requirements.txt` or
`pip3 install -r requirements.txt`. The only dependency is `openpyxl`.

## 2. Running the program

Put the CSV exported from Google Forms in the same folder, then run:

```
python scheduler.py
```

It asks six questions. Pressing Enter accepts the default shown in brackets:

```
========================================
FRATERNITY INTERVIEW SCHEDULER
========================================

Enter CSV filename [PNM_Availability.csv]:
> 
Enter output filename [Interview_Schedule.xlsx]:
> 
Group size [4]:
> 
Interview duration (minutes) [20]:
> 
Maximum groups per 20-minute slot [1]:
  (set this to the number of interview rooms you have)
> 
Randomization seed:
  (leave blank for a new random seed)
> 

Processing...

24 PNMs found.
6 groups required.
12 interview slots of 20 minutes are configured.

Generating randomized schedule...

Schedule successfully generated.
Valid grouping found after 8 attempt(s).
Method: Random shuffle

Randomization seed: 948402

Output saved to:
/Users/you/rush/Interview_Schedule.xlsx
```

You can also skip the prompts entirely:

```
python scheduler.py --csv PNM_Availability.csv --output Schedule.xlsx --seed 847293
```

### Before your first real run

Open `scheduler.py` and edit the `INTERVIEW_SLOTS` list near the top so it
matches the checkbox options in your Google Form **exactly**. If a PNM's answer
doesn't match a configured slot, the program stops and shows you which answers
and which slots disagree, rather than silently dropping the answer.

Everything else you'd want to change is in the same configuration block:

```python
GROUP_SIZE = 4
INTERVIEW_DURATION = 20
MAX_GROUPS_PER_SLOT = 1
MAX_ATTEMPTS = 10000

NAME_COLUMN = "Name"
AVAILABILITY_COLUMN = "Interview Availability"
```

## 3. How the randomization algorithm works

The program has two search strategies. The first one handles the normal case;
the second only runs when the first one can't succeed.

**Phase 1 — blind shuffle (the usual path).**

1. Sort all PNMs alphabetically, so the order people submitted the form has no
   effect on anything.
2. Shuffle that list into a random order.
3. Cut the shuffled list into consecutive groups of 4.
4. For each group, intersect the four members' availability to find the slots
   all four share.
5. Try to give every group one of its shared slots without exceeding the
   per-slot capacity (see section 5 below).
6. If any group can't be placed, throw the whole grouping away and go back to
   step 2 with a fresh shuffle.

Groups are formed in step 3 *before* availability is looked at in step 4. At
that point the program knows nothing about a PNM except their position in a
random shuffle, so the grouping itself carries no preferences at all. Step 6 is
plain rejection sampling: it discards groupings that can't be scheduled and
keeps the first one that can, which makes the result uniformly random across
all schedulable groupings.

**Phase 2 — availability-aware draw (rare).**

If availability is very tight, a blind shuffle can fail thousands of times in a
row simply because valid groupings are rare. After `MAX_ATTEMPTS` failed
shuffles, the program switches strategies instead of giving up:

1. Randomly pick which interview slots will actually host a group.
2. Randomly deal every PNM into a seat at a slot they said they were free for,
   using an augmenting-path (bipartite matching) search so that a valid deal is
   found whenever one exists.
3. Reshuffle members among any groups sharing a slot, since those groups are
   interchangeable.

Phase 2 uses exactly the same objective constraints. The difference is only
that it draws from among groupings that work instead of throwing away draws
that were never going to schedule. Which phase produced your schedule is
recorded in the "Grouping Method" row of the Randomization Info sheet.

**What this means for fairness.** In both phases, the only thing that can make
two PNMs more or less likely to end up together is how much their availability
overlaps — which is unavoidable, since four people can only interview together
if they share a free slot. Nothing else about a PNM is visible to the program.
There is no seeding, ranking, balancing, or name-based logic anywhere in it.

## 4. How the 20-minute availability matching works

Each entry in `INTERVIEW_SLOTS` is the *start* of one 20-minute interview. The
end time is computed as start + `INTERVIEW_DURATION`, so `"Monday 6:00 PM"`
becomes the window `Monday 6:00 PM - 6:20 PM`.

Each PNM's availability cell is split on commas and semicolons, and each piece
is matched to a configured slot. Matching ignores capitalization and extra
spaces, and it tolerates a few common Google Forms variations: range-style
options (`Monday 6:00 PM - 6:20 PM`), options with a comma inside them
(`Monday, 6:00 PM`), and 24-hour times (`Monday 18:00`). Anything that still
doesn't match is reported as an error rather than ignored.

A group's valid slots are the **intersection** of its four members' slots. For
example:

```
PNM A: 6:00, 6:20, 7:00
PNM B: 6:20, 6:40, 7:00
PNM C: 6:20, 7:00, 7:20
PNM D: 6:20, 7:00
--------------------------------
Shared: 6:20, 7:00
```

That group can be placed at either `6:20 PM - 6:40 PM` or `7:00 PM - 7:20 PM`.
If a group has no shared slot at all, the whole grouping is discarded and the
program reshuffles.

Placing groups into slots is a bipartite matching problem, not a first-come
grab: each slot is modelled as `MAX_GROUPS_PER_SLOT` interchangeable seats, and
an augmenting-path search will back up and move an already-placed group to a
different slot if that's what lets a later group fit. Both the order the groups
are considered in and the order each group's shared slots are considered in are
shuffled first, so a group with three valid options genuinely gets a random one
rather than always the earliest.

After a schedule is produced, the program re-verifies it from scratch before
writing the Excel file: exactly 4 PNMs per group, every PNM assigned exactly
once, every PNM available at their assigned slot, and no slot over capacity. If
any check fails, nothing is written.

## 5. How the randomization seed works

Every random decision the program makes — the shuffle, the slot choice, the
group IDs — comes from a single random number generator started from one
number, the seed.

- Leave the seed prompt blank and the program picks a fresh one from the
  operating system's entropy (e.g. `948402`) and prints it.
- Enter a seed you used before, with the same CSV file and the same settings,
  and you get a byte-for-byte identical schedule: same groups, same times, same
  group IDs.

The seed is printed to the screen and written into the **Randomization Info**
sheet of every Excel file, alongside the timestamp, the PNM count, and the
number of attempts. That's your audit trail. If anyone ever claims a group was
arranged deliberately, you can hand them the CSV and the seed and they can
regenerate the identical schedule themselves.

Two things to know: the seed only reproduces a schedule when paired with the
same CSV (adding one PNM changes everything downstream), and choosing a seed
*after* seeing the results it produces would defeat the purpose — so if you
care about the integrity of the process, take the first schedule the program
gives you rather than re-rolling until you like the groups.

## 6. Assigning the five brothers afterward

The program never sees, stores, or asks about brothers. It only knows PNM
names, PNM availability, the slot list, and the scheduling constraints.

After it finishes:

1. Open the output `.xlsx` file.
2. Go to the **Interview Schedule** sheet. Columns `Brother 1` through
   `Brother 5` are blank and shaded pale yellow.
3. Type five brothers' names into each row by hand.
4. Print it (the sheet is already set to landscape and fit-to-width, with the
   header row repeating on every page).

Because the file is written before any brother's name exists anywhere, no
brother can influence which PNMs are grouped together, and the group IDs
(`G-7F3A`, `G-C91D`, ...) are random hex values that encode nothing about the
PNMs in them.

## 7. The output file

**Sheet 1 — Interview Schedule:** Interview Date/Time, End Time, Group ID,
PNM 1-4, Brother 1-5. One row per group, in chronological order.

**Sheet 2 — PNM Details:** PNM Name, Group ID, Interview Start, Interview End,
Available Times. One row per PNM, alphabetical, so you can confirm at a glance
that everyone was scheduled inside the availability they submitted.

**Sheet 3 — Randomization Info:** seed, timestamp, PNM count, group size, group
count, interview duration, slot count, max groups per slot, attempt count,
grouping method, and the source CSV name.

## 8. Error messages

The program never shows a Python traceback. It stops with a plain-English
explanation and what to do about it for: a missing or unreadable CSV, an empty
CSV, a missing or misnamed name/availability column, duplicate PNM names, rows
with availability but no name, PNMs who selected nothing, availability answers
that don't match any configured slot, a PNM count not divisible by the group
size (it tells you the nearest workable counts), not enough interview capacity
(it shows the arithmetic), and an unschedulable situation (it lists the PNMs
with the tightest availability and the slots too empty to ever host a group).

## Testing

`run_tests.py` covers the eight scenarios plus input validation, Excel
structure, and an end-to-end command-line run — 40 checks in total, all
passing. To run them yourself:

```
python make_examples.py    # writes the example CSV and test fixtures
python run_tests.py
```

| Scenario | Result |
|---|---|
| 1. 24 PNMs with good availability | 6 groups of 4, everyone assigned once, everyone available at their slot, one group per slot |
| 2. Groupings that often have no shared slot | Reshuffled 10,000 times, then found a valid schedule via the phase-2 draw |
| 3. 25 PNMs | Stops; explains that 25 leaves 1 left over and that 24 or 28 would work |
| 4. A PNM with no availability | Named and reported before any randomization happens |
| 5. Too few interview slots | Stops; shows groups needed vs. total capacity |
| 6. `MAX_GROUPS_PER_SLOT = 2` | 6 groups fit into 3 slots, 2 per slot, availability still respected |
| 7. Same seed twice | Identical groups, times, and group IDs |
| 8. No seed / different seeds | 40 different seeds produced 40 different groupings |

One extra check worth noting: across 200 runs, groups landed in all 12
configured slots rather than clustering in the earliest ones, and with
unconstrained availability every possible pair of PNMs appeared together at
close to the expected uniform rate.
