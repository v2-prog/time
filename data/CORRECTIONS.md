# Corrections to the build prompt, and decisions on its open items

Checked 26 Nov 2026.

## Corrections to the prompt

1. **The barley duties were removed in 2023, not 2024.** The prompt calls this "China's barley tariff suspension in 2024". China removed the 80.5% duties from 5 August 2023, announcing it on 4 August. The 2024 thaw step was **wine**, whose duties were removed from 29 March 2024. Both dates are in the seed and covered by a regression test.
2. **比利顿 is not BHP's Chinese name.** It means "Billiton" only. BHP is **必和必拓**. The seed uses 必和必拓, and a test checks that 比利顿 on its own does *not* auto-resolve to BHP.
3. **ABARES doesn't cover minerals.** Its remit is agriculture, which is still useful for the barley and wine precedents. Mineral and energy production, export and outlook data comes from DISR's Office of the Chief Economist in the *Resources and Energy Quarterly*. Both are now separate feeds.
4. **Some state agency names have changed:**
   - **WA:** DMIRS became DEMIRS in 2023. Since 1 Jul 2025 the mining regulator has been the **Department of Mines, Petroleum and Exploration (DMPE)**. Royalty administration moved to RevenueWA on 1 Sep 2025.
   - **Qld:** the regulator is now the **Department of Natural Resources and Mines, Manufacturing and Regional and Rural Development (NRMMRRD)**, not "Department of Resources".
   - **NSW:** mining sits with **NSW Resources** within the Dept of Primary Industries and Regional Development, not "Department of Regional NSW".
   - **NT:** mineral titles sit with the **Department of Mining and Energy**. Mining *environmental licences* sit with the **Department of Lands, Planning and Environment**. That makes two NT feeds.
   - **Vic and Tas:** the agency names (Earth Resources Regulation, Mineral Resources Tasmania) haven't been checked yet.
5. **The company is likely now called Arafura Rare Earths.** "Arafura Resources" is kept as an alias. Confirm the current registered name.
6. **The brief's example match is illustrative, not real.** It describes a Northern Minerals offtake with a Japanese offtaker, +40% within 14 days of a downstream incentive. It's reproduced only as a synthetic fixture.

## Events since the brief's 2020–2024 window that the seed now covers

- **China's expanded rare earth export controls of 9 Oct 2025 are still suspended, but only until 10 Jan 2027.** MOFCOM/GACC Ann. 58 of 2026 extended the suspension on 9 Nov 2026. The April 2025 licensing regime for seven medium and heavy rare earths (Sm, Gd, Tb, Dy, Lu, Sc, Y) stays in force. This is the most time-sensitive item in the timeline: watch for 10 Jan 2027.
- **CMRG and BHP, Sep 2025 – Apr 2026.** CMRG halted purchases of Jimblebar fines, then all new USD-denominated cargoes, then Jingbao fines. It eased on 14 Apr 2026, and BHP said negotiations had concluded on 22 Apr 2026. This is the best iron ore test case available, better than anything in 2020–24.
- **Northern Minerals FIRB orders.** Disposal orders in June 2024, and a second set commencing 18 Jun 2026.
- **The Critical Minerals Production Tax Incentive passed on 11 Feb 2025.** It applies to production from 1 Jul 2027 to 30 Jun 2040.
- **The EPBC reforms passed on 28 Nov 2025.** Royal Assent was on 1 Dec 2025. They commence in tranches: 20 Feb 2026, then NEPA on 1 Jul 2026, with the balance later.

## Decisions on the open items

| Open item | Decision taken in this build | How to reverse |
|---|---|---|
| Seed dataset | **Kept BHP/RIO/FMG + the China dispute timeline, and added the 2025–26 CMRG and rare earth events.** In practice the dispute period has well-documented *policy* events but few verified *company-level* commercial events. The two real commercial events found are both from 2023 and 2026. | Feed 2020–24 ASX announcements in with `--items` |
| Shared infrastructure with ChipCorrelator | **Shared code, separate deployment.** `correlator_core` holds no domain knowledge and can become a shared package. Each variant gets its own database, because the CHECK lists and seeds differ. I couldn't find the ChipCorrelator code (iterations/037) to reconcile against, so check that its record schema matches `NormalisedRecord`. | Vendor-copy `correlator_core` instead |
| Feed-health delivery channel | **Both, from the same source.** `feed_health.md` can be emailed by a scheduled task, and the same table sits at the top of the dashboard. | — |
| No advice | A banner on every page. Matches are worded as timing plus shared scope, never as cause or recommendation. | — |
| FIRB: policy or commercial? | **Policy event with `boundary_class: true`.** A FIRB decision is a government act, so it belongs on the policy timeline and gets a lifecycle. Every match against it carries the `boundary_event_policy_or_commercial` flag. A company's *own* announcement of FIRB approval comes in through the ASX adapter as the commercial event `firb_approval_received`, so the two sides can still be matched against each other. CMRG directives get the same treatment, because a state buyer's instruction is the same kind of boundary case. | Set `boundary_class` per policy, or filter on the flag |

## Verification pass, 27 Nov 2026

Every item below and every date above was rechecked against primary sources. Results, with source URLs, are in `data/verification.json`. The main corrections were: Qld NRMMRRD dates from 1 Nov 2024, NT DME from Sep 2024 and NSW DPIRD from 1 Jul 2024, so only the WA change is 1 Jul 2025; the coal easing was reported on 5 Jan 2023, not 3 Jan; wine provisional measures applied from 28 Nov 2020; and the CMRG halt was first reported on 19 Sep 2025. CMPTI received Royal Assent on 14 Feb 2025.

## Items still marked `verify: true` (as of 26 Nov; see verification.json for current state)

- The coal restriction dates: May 2020 verbal notice, October 2020 start, 3 Jan 2023 easing, 14 Mar 2023 full removal. These come from reporting only, because the measure was never announced.
- The provisional wine deposits from late Nov 2020. This date came from memory.
- The release date of the Critical Minerals Strategy 2023–2030 (20 Jun 2023, from memory) and its URL.
- The CMPTI announcement date (14 May 2024 Budget, from memory).
- The CMRG start date (week of 22 Sep 2025, inferred) and the Jingbao date (report date).
- The registration date of the 2026 Northern Minerals orders (inferred).
- The Japanese aliases for BHP and Rio, and the Chinese aliases for Fortescue.
- The port and rail relationships for Pilbara Ports and Aurizon.
- Both real commercial seed events, which need confirming against company releases.
