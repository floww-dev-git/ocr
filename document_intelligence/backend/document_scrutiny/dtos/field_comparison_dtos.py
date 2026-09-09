from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FieldComparisonDTO:
    document_id: str
    document_type_label: str
    field_key: str
    field_label: str
    application_field_key: str
    read_value: str
    application_value: str
    # From the catalog's field spec. Where present it decides how the two values are
    # compared, ahead of the application field's own default.
    comparison_rule: Optional[str] = None
    # Also from the spec: whether this value may be written out in full.
    masked: bool = False
