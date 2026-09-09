"""Where an edited flat deed field lands in the structured record.

The officer corrects eleven flat values on a deed. The chain engine reasons over the
nested `DeedRecordDTO`, so a correction has to reach it too, or a fixed name still
traces as the misread one.

This is the inverse of document_extraction's `_SHARED_FIELD_KEYS` (deed_read.py). It
is restated here rather than imported because reading it off the read spec would pull
pydantic and the extractor adapter into the scrutiny domain — and how a correction
flows into the record scrutiny reasons over is scrutiny's own business. A test
(test_deed_record_edit.py) pins this map against the read spec so the two cannot drift.
"""

# Catalog field key -> the DeedRecordDTO attribute path it corrects. Only the fields
# the chain actually reads are here; a boundaries or consideration edit changes the
# flat value the officer sees but nothing the chain traces on.
DEED_FIELD_TO_RECORD_PATH = {
    "docNo": "doc_no",
    "regDate": "registration_date",
    "sro": "sro",
    "vendor": "sellers.0.name",
    "purchaser": "buyers.0.name",
    "surveyNo": "property_info.survey_no",
    "plotNo": "property_info.plot_no",
    "extent": "property_info.extent_text",
    "village": "property_info.locality",
}

# Correcting the extent text should re-derive the square-yard figure the chain's
# arithmetic uses; the flat field carries the words, the record carries the number.
EXTENT_FIELD_KEY = "extent"
EXTENT_NUMBER_PATH = "property_info.extent_sq_yard"
