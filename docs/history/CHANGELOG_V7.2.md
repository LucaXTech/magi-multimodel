# Changelog v7.2

## Reliability reporting

- separates valid accuracy from end-to-end availability;
- excludes provider/API failures from critical reasoning errors;
- excludes missing outputs from Brier score;
- marks incomplete systems as ineligible for ranking;
- uses only jointly evaluable pairs in paired comparisons;
- adds coverage and technical-failure breakdowns.

## New tools

- `python -m benchmark.audit_objective_run <run>`: corrected reanalysis without API calls;
- `python -m benchmark.recover_objective <run>`: reruns only failed rows with identical prompts and seeds;
- recovery stops on a renewed rate limit by default.

## Protocol

- adds reliability addendum to objective v3;
- adds `OBJECTIVE_V4_BLUEPRINT.md` for the product-aligned next benchmark;
- 22 automated tests pass.
