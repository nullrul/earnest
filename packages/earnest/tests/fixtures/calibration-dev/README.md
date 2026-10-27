# Calibration development fixture (SYNTHETIC)

This fixture is SYNTHETIC. An agent wrote it on 2026-10-27 at the user's
decision. It is NOT the SC4 calibration set and must never be used to claim
SC4. The maintainer's hand-written fixture belongs in tests/fixtures/calibration/.

## Files

- requirements.md: ten requirements, alphabetical, default needs (impl and utest).
- src/meter.py: one tagged function per requirement, in the same order.
- tests/test_meter.py: one tagged test per requirement, in the same order.
- verdicts.json: the maintainer's twenty answers (implemented and tested for each requirement).
- stub-pass.json: verdicts with two answers flipped; eight requirements match.
- stub-fail.json: stub-pass.json with one more flip; seven requirements match.

The two stub files are left out of the fixture's commit.

## Deliberate faults

Three answers are not-satisfied on purpose: the daily cap code allows 25
dollars, the electric discount takes 5 percent, and the lost ticket test never
checks the cap. An always-satisfied judge therefore matches only seven.
