# A one-character token is noise: a stray OCR mark, or a house number broken off
# from what follows it. Neither is agreement between two addresses.
MINIMUM_ADDRESS_TOKEN_LENGTH = 2

# Above this share of the shorter address, the two are taken to describe the same
# place. Below it the officer is told they differ, as advice rather than a finding —
# people move, and the form is often older than the card.
ADDRESS_OVERLAP_PASS_FLOOR = 0.5
