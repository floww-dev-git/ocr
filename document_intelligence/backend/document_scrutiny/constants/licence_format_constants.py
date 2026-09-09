import enum

# A licence number reads as a two-letter state code, then the issuing RTO, then the
# year of issue, then the serial: TS 09 2015 0012345.
#
# The RTO block is two digits in most states and three in others, so a real licence
# is 15 or 16 characters. Both occur: TS0920150012345 and TS20820220017249 are each
# a genuine Telangana number. The year and serial are therefore counted from the END
# — four digits of year then seven of serial — so the RTO block absorbs the
# difference instead of the year sliding out from under a fixed offset.
LICENCE_LENGTHS = (15, 16)
SHORTEST_LICENCE_LENGTH = min(LICENCE_LENGTHS)
LONGEST_LICENCE_LENGTH = max(LICENCE_LENGTHS)
STATE_CODE_LENGTH = 2
SERIAL_LENGTH = 7
YEAR_LENGTH = 4
# Offsets from the end: the year sits immediately before the serial.
YEAR_START_FROM_END = -(YEAR_LENGTH + SERIAL_LENGTH)
YEAR_END_FROM_END = -SERIAL_LENGTH
EARLIEST_ISSUE_YEAR = 1950
LATEST_ISSUE_YEAR = 2100


class LicenceFormatState(enum.Enum):
    MALFORMED = "malformed"
    IMPLAUSIBLE_YEAR = "implausible_year"
    RECOGNISED = "recognised"
