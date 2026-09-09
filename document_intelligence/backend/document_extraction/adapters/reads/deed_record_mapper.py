import dataclasses
from typing import Mapping, Optional, Tuple

from document_extraction.adapters.reads.field_read_mapper import FieldReadMapper
from document_extraction.dtos.deed_record_dtos import (
    DeedRecordDTO,
    PartyDTO,
    PropertyInfoDTO,
)
from document_extraction.dtos.document_record_dtos import DocumentRecordDTO
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec

# What the POC's prompt asks the model to label its provenance boxes with, against
# the catalog field keys those values land in.
_BOX_LABELS_TO_FIELD_KEYS: Mapping[str, str] = {
    "doc_no": "docNo",
    "registration_date": "regDate",
    "seller": "vendor",
    "buyer": "purchaser",
    "survey_no": "surveyNo",
    "consideration": "consideration",
}


class DeedRecordMapper(FieldReadMapper):
    """A deed read into both the flat values and the structured record.

    The flat values are the officer's surface: eleven fields they can read and
    correct. The structured record is what the chain engine reasons over, because
    tracing title needs the full party lists and the deed numbers a recital cites,
    and neither survives being flattened into one name and one string.
    """

    @classmethod
    def to_document_record(
        cls,
        model_read: object,
        read_spec: DocumentReadSpec,
        source: str,
        page_count: int,
    ) -> DocumentRecordDTO:
        flat_record = super().to_document_record(
            model_read=model_read,
            read_spec=read_spec,
            source=source,
            page_count=page_count,
        )
        return dataclasses.replace(
            flat_record, deed_record=cls.build_deed_record(model_read=model_read)
        )

    @classmethod
    def build_deed_record(cls, model_read: object) -> DeedRecordDTO:
        return DeedRecordDTO(
            doc_no=cls._clean(getattr(model_read, "doc_no", None)),
            sro=cls._clean(getattr(model_read, "sro", None)),
            registration_date=cls._clean(
                getattr(model_read, "registration_date", None)
            ),
            execution_date=cls._clean(getattr(model_read, "execution_date", None)),
            deed_type=cls._clean(getattr(model_read, "deed_type", None)),
            sellers=cls._build_parties(getattr(model_read, "sellers", None)),
            buyers=cls._build_parties(getattr(model_read, "buyers", None)),
            property_info=cls._build_property(getattr(model_read, "property", None)),
            consideration_text=cls._clean(
                getattr(model_read, "consideration_text", None)
            ),
            consideration_inr=cls._number(
                getattr(model_read, "consideration_inr", None)
            ),
            stamp_duty_text=cls._clean(getattr(model_read, "stamp_duty_text", None)),
            estamp_no=cls._clean(getattr(model_read, "estamp_no", None)),
            prior_deed_refs=cls._build_prior_deed_refs(
                getattr(model_read, "prior_deed_refs", None)
            ),
            executed_via_gpa=bool(getattr(model_read, "executed_via_gpa", False)),
        )

    @classmethod
    def _build_parties(cls, parties) -> Tuple[PartyDTO, ...]:
        built = []
        for party in parties or []:
            name = cls._clean(getattr(party, "name", None))
            if name is None:
                # A party with no name cannot be matched against anything, and
                # carrying it would inflate the party count the chain reasons over.
                continue
            built.append(
                PartyDTO(
                    name=name,
                    name_original=cls._clean(getattr(party, "name_original", None)),
                    relation=cls._clean(getattr(party, "relation", None)),
                    relative_name=cls._clean(getattr(party, "relative_name", None)),
                    address=cls._clean(getattr(party, "address", None)),
                    pan=cls._clean(getattr(party, "pan", None)),
                    aadhaar=cls._clean(getattr(party, "aadhaar", None)),
                )
            )
        return tuple(built)

    @classmethod
    def _build_property(cls, property_read) -> PropertyInfoDTO:
        if property_read is None:
            return PropertyInfoDTO()
        return PropertyInfoDTO(
            survey_no=cls._clean(getattr(property_read, "survey_no", None)),
            plot_no=cls._clean(getattr(property_read, "plot_no", None)),
            extent_text=cls._clean(getattr(property_read, "extent_text", None)),
            extent_sq_yard=cls._number(getattr(property_read, "extent_sqyd", None)),
            boundaries=cls._clean(getattr(property_read, "boundaries", None)),
            locality=cls._clean(getattr(property_read, "locality", None)),
            ulpin=cls._clean(getattr(property_read, "ulpin", None)),
        )

    @classmethod
    def _build_prior_deed_refs(cls, prior_deed_refs) -> Tuple[str, ...]:
        cleaned = (cls._clean(reference) for reference in prior_deed_refs or [])
        return tuple(reference for reference in cleaned if reference is not None)

    @staticmethod
    def _number(value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _box_catalog_key(box_read, read_spec: DocumentReadSpec) -> Optional[str]:
        # The deed prompt labels its boxes with its own field names rather than the
        # catalog's, so the label map is its own rather than the attribute paths.
        field_key = _BOX_LABELS_TO_FIELD_KEYS.get(str(box_read.label or ""))
        if field_key is None:
            return None
        if field_key not in set(read_spec.field_keys_by_attribute.values()):
            return None
        return field_key
