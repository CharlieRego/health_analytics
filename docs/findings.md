# Findings

_Source: AIHW MyHospitals, data version 2026081901 (financial years 2011-12 to 2024-25). Draft from SQL on the marts; check each against the dashboard before publishing._

## Finding 1 — 44% of Toowoomba Hospital ED patients left within 4 hours in 2024-25, down from 66% in 2020-21 and now 6 points below its peer group

**What the data shows:** The share of all ED patients leaving within four hours of arrival (MYH0005, "All patients") fell every year at Toowoomba: 66% → 63% → 58% → 50% → 44% (2020-21 to 2024-25). Toowoomba was 5 points *above* its peer group (Large regional hospitals) in 2021-22 and is 6 points *below* it in 2024-25 (peers: 50%). Queensland fell from 69% to 50% and the national figure from 67% to 53% over the same period, so the decline is system-wide, but Toowoomba's is steeper.
**Why it matters:** Time in ED is a key measure of patient flow; long stays are linked to crowding and delays for new arrivals. A steeper-than-peer decline suggests local flow pressures worth investigating (for example access block, bed availability, demand growth).
**Caveat:** Annual aggregates, not causes. Toowoomba is the only Darling Downs hospital reporting this measure, so the Darling Downs network figure equals Toowoomba's and says nothing about the smaller hospitals.

## Finding 2 — Median time in Toowoomba's ED rose to 272 minutes (4 h 32 min) in 2024-25, up 83 minutes (+44%) since 2020-21 and longer than Queensland (241) and Australia (228)

**What the data shows:** Median time patients spent in ED (MYH0036, "All patients"): Toowoomba 189 → 195 → 213 → 241 → 272 minutes from 2020-21 to 2024-25. Queensland rose from 172 to 241 and the national median from 181 to 228. Toowoomba started below Queensland and is now 31 minutes above it.
**Why it matters:** It's the same story as Finding 1 from a different angle: the typical patient now stays well past the 4-hour mark. In the triage breakdown, "Emergency" category patients were seen on time 53% of the time vs 69% for peers (-16 points), the largest gap of any triage category.
**The longest stays (nuance):** For the slowest 10% of patients (MYH0013, 90th percentile, "All patients"), Toowoomba is still slightly *better* than its peers in 2024-25: 802 vs 811 minutes. But that lead has almost gone. It was 104 minutes better in 2020-21 (423 vs 527), and its own 90th-percentile time has nearly doubled since (423 to 802, +90%). So Toowoomba once handled its longest stays well compared with peers and is now only level with them, even though its 4-hour share is 6 points worse.
**Caveat:** No peer-group value is published for this measure, so the comparison is with the state and national figures. A median hides the tail; the 90th-percentile measure (MYH0013) shows the longest stays.

## Finding 3 — Toowoomba's elective surgery tells a better story: 98% of urgent patients were treated on time (peers 91%), and non-urgent on-time rates recovered from 30% to 62% in one year

**What the data shows:** Patients receiving elective surgery within the clinically recommended time (MYH0008), Toowoomba vs Large regional peers, 2023-24 → 2024-25: Urgent 97% → 98% (peers 91%); Semi-urgent 65% → 74% (peers 69%, now above); Non-urgent 30% → 62% (peers 74%, still 12 points below).
**Why it matters:** Urgent patients are consistently prioritised above the peer level, and the big jump in non-urgent on-time rates points to a backlog being worked down. Non-urgent is still the gap to watch.
**Caveat:** One year of improvement isn't a trend. The "all patients" total isn't published for this measure, so results are by urgency category only. Values flagged "*" (X42) should be read with caution.

## Finding 4 — In 2024-25, 11 of 26 Queensland hospitals beat their peer group on the 4-hour ED measure, 14 fell short and 1 matched; the gap runs from +17 points (Mount Isa) to -18 (Caboolture)

**What the data shows:** Share of all ED patients leaving within 4 hours (MYH0005, "All patients"), each hospital vs its AIHW peer value, 2024-25. Best: Mount Isa Base 82% vs 65% (+17), The Prince Charles 60% vs 46% (+14), Nambour General 56% vs 46% (+10). Worst: Caboolture 38% vs 56% (-18), Princess Alexandra 33% vs 46% (-13), Ipswich 39% vs 46% (-7), Toowoomba 44% vs 50% (-6). Cairns matched its peers (50%).
**Year on year:** 19 of the 26 hospitals did worse than in 2023-24, 1 was unchanged (Cairns) and 6 improved. The biggest falls were Logan (50% to 42%, -8 points) and Toowoomba (50% to 44%, -6). The biggest gains were Robina (53% to 58%, +5) and Redland (57% to 61%, +4).
**Why it matters:** The state-wide fall (Finding 1) isn't spread evenly. Several large South East Queensland hospitals (PA, Ipswich, Logan, Caboolture) sit well below their peers, so they're where the state average is being pulled down.
**Caveat:** A gap to peer compares one hospital with a group average, not with a target. Peer groups differ in size and casemix (see the data note below).

## Data notes

- **Peer group label vs peer value.** `dim_reporting_unit.peer_group_name` is the hospital's general AIHW peer group. 15 Queensland hospitals (including Princess Alexandra and Royal Brisbane & Women's) are labelled "Not peered" there, yet AIHW still publishes a peer value for them on the ED measures (46% or 65% in 2024-25, matching the Major hospitals and Medium regional values). So AIHW uses a measure-specific peer group for the peer value. The gaps (value minus peer value) are correct; the peer group *name* shouldn't be shown next to them. The dashboard's hospital table leaves the peer group column out for this reason. Possible fix: take the measure-specific peer group from the API if it's published.
