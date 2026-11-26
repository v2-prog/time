# Next steps for Time.vilo.au

Updated 27 Nov 2026.

## Done
- Live fetchers: ASX announcements (BHP, RIO, FMG, LYC, WHC, ARU, NTU) and WA DMPE (announcements and tenement grants), with feed health for all 23 spec feeds and a weekday GitHub Actions schedule.
- Verification pass against primary sources: `data/verification.json` (shown in Rotation → Queues).
- Rotation design fixes in `rotation/logic.js`, with tests.
- Resources, Chips and Rotation pages rebuilt; 404 page; CSP headers.

## Still open
1. **ASX licensing.** Headlines are withheld because ASX's site terms bar republishing without written consent. To show them, get ASX consent or an ASX data licence, or put the site behind Cloudflare Access, then set `TIME_PUBLISH_ASX_HEADLINES=1` in the workflow.
2. **Matching engine:** built (`fetchers/correlator.py`, 27 Nov 2026). Still to do: tune the weights against reviewed matches using the feedback loop (acted / ignored / outcome logging isn't built yet), add value-shift thresholds once a feed carries dollar values, and widen the policy timeline as the new feeds land.
3. **Remaining feeds** (20 never run): Qld NRMMRRD, NSW Resources, NT DME and DLPE, SA DEM, EPBC notices, FIRB orders (Federal Register of Legislation), MOFCOM, China customs, DISR REQ, ABARES, ASIC, port throughput.
4. **Items still flagged** in `data/verification.json` (verify: true): coal restriction dates, CMRG start and 14 Apr easing, the WA DMPE 1 Jul 2025 start date, NSW DPIRD start date, NT DLPE name, the Arafura name-change date, the NTU 18 Jun commencement (section 2 of F2026N00326), the EPBC 20 Feb 2026 tranche, ASX 200 membership of NTU and ARU, JP/CN aliases, port and rail links, and the press-only NVIDIA halt and China Energy order.
5. **Rotation backtest** on the 2020–24 China dispute needs licensed S&P/ASX sector index history.
6. **Direction rules** in `logic.js` are drafts and need Doug's review.
7. Vic and Tas agency names are unchecked.

General information only. Not financial, legal or tax advice.
