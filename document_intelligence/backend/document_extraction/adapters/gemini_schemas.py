from typing import List

from pydantic import BaseModel, Field


class FieldBoxRead(BaseModel):
    """Where on the page a value was read from — for click-to-verify provenance.

    Shared by every document type's read schema. `label` is validated against the
    reading type's own field keys when the box is mapped, so a box naming a field
    the type does not have is discarded rather than trusted.
    """

    label: str = Field(
        description="Which field this locates, using the field labels named in the prompt"
    )
    value: str = Field(description="The value as read at this location")
    page: int = Field(default=0, description="0-based page index the value appears on")
    box: List[int] = Field(
        default_factory=list,
        description="[ymin, xmin, ymax, xmax] normalised to 0-1000 on that page",
    )


class DocumentIdentification(BaseModel):
    document_type_id: str = Field(
        description="The id of the document type, chosen from the supplied list"
    )
    confidence: float = Field(default=0.0, description="Confidence in the choice, 0..1")
