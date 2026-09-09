INTERNAL_CONSISTENCY_CHECK_KEY = "internal-consistency"

# A human date of birth cannot be in the future, and a person older than this is
# implausible on any document a citizen files — so a date beyond either bound is the
# document contradicting itself, not a mismatch with anything else.
MAX_PLAUSIBLE_AGE_YEARS = 120

# The Aadhaar read normalises a year-only date of birth to the first of January, and
# the prompt flags it. A date landing exactly on 01-01 is therefore treated as
# possibly year-only and worth the officer confirming the full date — a soft signal,
# not a failure.
YEAR_ONLY_MONTH_DAY = (1, 1)
