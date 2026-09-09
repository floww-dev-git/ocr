from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class DocumentReadSpec:
    """How to read one document type: what to ask for, and what the answer means.

    `response_schema` and `prompt` are the model-facing half — the schema's field
    descriptions are prompt surface, not documentation. The two key maps are the
    translation back to the catalog's own vocabulary, so the model is free to name
    its own attributes without the check engine ever seeing them.

    An attribute name may be a dotted path (`property.survey_no`, `sellers.0.name`)
    for a type whose reading is nested rather than flat.
    """

    document_type_id: str
    response_schema: type
    prompt: str
    field_keys_by_attribute: Mapping[str, str]
    structure_keys_by_attribute: Mapping[str, str]
    # A type whose reading carries more than flat field values supplies its own
    # mapper. None means the shared FieldReadMapper, which is all most types need.
    record_mapper: Optional[Any] = None
    # True for a type that arrives photocopied together with other documents, so a
    # file classified as one is worth an inventory pass. A card is one card.
    bundleable: bool = False
