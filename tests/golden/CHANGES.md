# Deliberate changes to English output

`tests/golden/orig/` holds what the original (commit `a2feb21`) prints for each case in
`cases.json`. When this version prints something else on purpose, the new output goes to
`tests/golden/current/` (`python tests/golden/golden.py --accept ID`) and the case is listed here.
`tests/test_golden.py` fails if a case in `current/` is missing from this file.

- `hookscore_strong`, `hookscore_weak`, `hookscore_strong_json`, `hookscore_weak_json`: a dot at
  the end of a word and a standalone "..." no longer change the score (4 of 42 hooks moved; the
  strong-weak gap went from 10.7 to 10.9). The JSON output gained the `lang` field.
- `title_long_thumb`: five meaningful words of thumbnail text are now a hint, not an issue, so the
  score goes from 80 to 94. `title_file_json`, `title_single_json`: new `hints` and `lang` fields.
- `retention_pct`, `retention_pct_duration`, `retention_pct_said`, `retention_pct_json`,
  `retention_seconds`, `retention_seconds_said`, `retention_seconds_json`: cliffs are shown as
  intervals, the hook drop is not repeated as a cliff, the axis comes from the header; the JSON
  output gained `to_seconds`, `axis`, `duration`, `lang` and `source`.
- `chapters_default`, `chapters_target4`, `chapters_flat_target4`, `chapters_json`: words of equal
  frequency in draft titles are ordered by first occurrence, so the output no longer depends on
  Python's hash seed. Chapter boundaries are unchanged.
