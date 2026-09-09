from typing import Dict, Optional, Set, Tuple

from document_extraction.constants.extraction_constants import (
    BOX_COORDINATE_COUNT,
    BOX_COORDINATE_SCALE,
    UNCERTAIN_FIELD_CONFIDENCE,
)
from document_extraction.domain.read_confidence import ReadConfidence
from document_extraction.dtos.document_record_dtos import (
    DocumentRecordDTO,
    FieldBoxDTO,
    FieldReadDTO,
)
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class FieldReadMapper:
    """Turns one model read into a DocumentRecordDTO, driven by the type's key maps.

    Everything here is the same for every document type: drop what was not read,
    honour the model's own doubts, discard boxes that name a field the type does not
    have, and clamp coordinates. Only the maps differ, and they arrive on the spec.
    """

    @classmethod
    def to_document_record(
        cls,
        model_read: object,
        read_spec: DocumentReadSpec,
        source: str,
        page_count: int,
    ) -> DocumentRecordDTO:
        doubted_keys = cls._doubted_catalog_keys(
            low_confidence_fields=getattr(model_read, "low_confidence_fields", None),
            read_spec=read_spec,
        )
        field_reads = cls._build_field_reads(
            model_read=model_read,
            read_spec=read_spec,
            source=source,
            doubted_keys=doubted_keys,
        )
        read_keys = {field_read.key for field_read in field_reads}
        return DocumentRecordDTO(
            field_reads=field_reads,
            structure_findings=cls._build_structure_findings(
                model_read=model_read, read_spec=read_spec
            ),
            overall_confidence=ReadConfidence.overall(field_reads=field_reads),
            low_confidence_fields=ReadConfidence.collect_low_confidence_field_keys(
                field_reads=field_reads
            ),
            boxes=cls._build_boxes(
                boxes=getattr(model_read, "boxes", None),
                read_keys=read_keys,
                read_spec=read_spec,
            ),
            page_count=page_count,
        )

    @classmethod
    def _build_field_reads(
        cls,
        model_read: object,
        read_spec: DocumentReadSpec,
        source: str,
        doubted_keys: Set[str],
    ) -> Tuple[FieldReadDTO, ...]:
        reported_confidence = float(getattr(model_read, "confidence", 0.0) or 0.0)
        field_reads = []
        for model_attribute, catalog_key in read_spec.field_keys_by_attribute.items():
            value = cls._clean(cls._resolve(model_read, model_attribute))
            if value is None:
                continue
            field_reads.append(
                FieldReadDTO(
                    key=catalog_key,
                    value=value,
                    confidence=ReadConfidence.for_source(
                        confidence=cls._field_confidence(
                            reported_confidence=reported_confidence,
                            doubted=catalog_key in doubted_keys,
                        ),
                        source=source,
                    ),
                )
            )
        return tuple(field_reads)

    @staticmethod
    def _field_confidence(reported_confidence: float, doubted: bool) -> float:
        if doubted:
            return min(reported_confidence, UNCERTAIN_FIELD_CONFIDENCE)
        return reported_confidence

    @staticmethod
    def _doubted_catalog_keys(
        low_confidence_fields, read_spec: DocumentReadSpec
    ) -> Set[str]:
        # The model may echo back either its own attribute name or the catalog key
        # it was told to use, so both spellings are accepted.
        catalog_keys = set(read_spec.field_keys_by_attribute.values())
        doubted: Set[str] = set()
        for reported_field in low_confidence_fields or []:
            if reported_field in catalog_keys:
                doubted.add(reported_field)
            elif reported_field in read_spec.field_keys_by_attribute:
                doubted.add(read_spec.field_keys_by_attribute[reported_field])
        return doubted

    @staticmethod
    def _build_structure_findings(
        model_read: object, read_spec: DocumentReadSpec
    ) -> Dict[str, bool]:
        """Which template elements were found.

        A `None` from the model means the element does not apply to this variant of
        the document — an e-PAN carries no hologram, so asking whether its hologram
        is visible has no true answer. Such an element is left out of the findings
        entirely rather than recorded as absent, because the check engine reports an
        absent element as a warning the officer must clear, and a warning about a
        feature the document was never issued with is noise.
        """
        findings = {}
        for model_attribute, structure_key in (
            read_spec.structure_keys_by_attribute.items()
        ):
            finding = getattr(model_read, model_attribute, True)
            if finding is None:
                continue
            findings[structure_key] = bool(finding)
        return findings

    @classmethod
    def _build_boxes(
        cls, boxes, read_keys: Set[str], read_spec: DocumentReadSpec
    ) -> Tuple[FieldBoxDTO, ...]:
        mapped = []
        for box_read in boxes or []:
            catalog_key = cls._box_catalog_key(box_read=box_read, read_spec=read_spec)
            coordinates = cls._clamp_coordinates(box_read.box)
            if catalog_key is None or coordinates is None:
                continue
            if catalog_key not in read_keys:
                continue
            mapped.append(
                FieldBoxDTO(
                    field_key=catalog_key,
                    value=str(box_read.value or ""),
                    page=max(0, int(box_read.page or 0)),
                    box=coordinates,
                )
            )
        return tuple(mapped)

    @staticmethod
    def _box_catalog_key(box_read, read_spec: DocumentReadSpec) -> Optional[str]:
        label = str(box_read.label or "")
        if label in set(read_spec.field_keys_by_attribute.values()):
            return label
        return read_spec.field_keys_by_attribute.get(label)

    @staticmethod
    def _clamp_coordinates(box) -> Optional[Tuple[int, int, int, int]]:
        if box is None or len(box) != BOX_COORDINATE_COUNT:
            return None
        return tuple(
            max(0, min(BOX_COORDINATE_SCALE, int(coordinate))) for coordinate in box
        )

    @classmethod
    def _resolve(cls, model_read: object, attribute_path: str):
        """Reads a value that may sit under a nested path, e.g. `sellers.0.name`.

        A path that runs out part way yields nothing rather than raising: a deed
        with no seller read is a deed with no vendor value, not a crash.
        """
        current = model_read
        for step in str(attribute_path).split("."):
            if current is None:
                return None
            current = cls._step(current, step)
        return current

    @staticmethod
    def _step(current, step: str):
        if step.isdigit():
            index = int(step)
            if not isinstance(current, (list, tuple)) or index >= len(current):
                return None
            return current[index]
        return getattr(current, step, None)

    @staticmethod
    def _clean(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None
