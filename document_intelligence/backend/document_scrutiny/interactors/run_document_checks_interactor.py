from typing import Dict, List, Optional, Set

from document_catalog.constants.enums import FieldComparisonRule
from document_catalog.dtos.catalog_dtos import FieldSpecDTO
from document_scrutiny.constants.comparable_application_fields import (
    CHECK_KEYS_BY_APPLICATION_FIELD,
)
from document_scrutiny.domain.cleared_field_check import ClearedFieldCheck
from document_scrutiny.domain.document_quality_check import DocumentQualityCheck
from document_scrutiny.domain.field_comparison_checks import FieldComparisonChecks
from document_scrutiny.domain.identifier_format_check import IdentifierFormatCheck
from document_scrutiny.domain.internal_consistency_check import InternalConsistencyCheck
from document_scrutiny.domain.qr_consistency_check import QrConsistencyCheck
from document_scrutiny.domain.structure_checks import StructureChecks
from document_scrutiny.domain.validity_check import ValidityCheck
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.field_comparison_dtos import FieldComparisonDTO
from document_scrutiny.dtos.run_checks_dtos import RunDocumentChecksRequestDTO


class RunDocumentChecksInteractor:
    def run_checks(self, request: RunDocumentChecksRequestDTO) -> List[CheckDTO]:
        read_values = self._read_values_by_field_key(request)
        field_checks = self._build_field_checks(
            request=request,
            read_values=read_values,
            cleared_field_keys=self._cleared_field_keys(request),
        )
        structure_checks = StructureChecks.build(
            document_id=request.document_id,
            structure_specs=request.document_type.structure_specs,
            structure_findings=request.structure_findings,
        )
        integrity_checks = self._build_integrity_checks(
            request=request, read_values=read_values
        )
        return [*field_checks, *structure_checks, *integrity_checks]

    def _build_integrity_checks(
        self, request: RunDocumentChecksRequestDTO, read_values: Dict[str, str]
    ) -> List[CheckDTO]:
        """Checks about the document as an artifact, not about any one field.

        Both are added only when the evidence for them was gathered. A QR check
        appears only when a QR was decoded; a quality check only when the scan was
        assessed. On the mock path neither is present, so nothing is reported rather
        than a false pass.
        """
        checks: List[CheckDTO] = []
        internal_consistency_check = InternalConsistencyCheck.build(
            document_id=request.document_id,
            date_of_birth=read_values.get("dob"),
            scrutiny_today=request.scrutiny_today,
        )
        if internal_consistency_check is not None:
            checks.append(internal_consistency_check)
        if request.qr_fields is not None:
            checks.append(
                QrConsistencyCheck.build(
                    document_id=request.document_id,
                    qr_fields=request.qr_fields,
                    printed_values=read_values,
                )
            )
        quality_check = DocumentQualityCheck.build(
            document_id=request.document_id, quality=request.quality
        )
        if quality_check is not None:
            checks.append(quality_check)
        return checks

    def _build_field_checks(
        self,
        request: RunDocumentChecksRequestDTO,
        read_values: Dict[str, str],
        cleared_field_keys: Set[str],
    ) -> List[CheckDTO]:
        checks: List[CheckDTO] = []
        for field_spec in request.document_type.field_specs:
            read_value = read_values.get(field_spec.key)
            if not read_value:
                if self._was_cleared_by_officer(
                    field_spec=field_spec, cleared_field_keys=cleared_field_keys
                ):
                    checks.append(
                        ClearedFieldCheck.build(
                            document_id=request.document_id, field_spec=field_spec
                        )
                    )
                continue
            checks.extend(
                self._build_checks_for_field(
                    request=request, field_spec=field_spec, read_value=read_value
                )
            )
        return checks

    @staticmethod
    def _was_cleared_by_officer(
        field_spec: FieldSpecDTO, cleared_field_keys: Set[str]
    ) -> bool:
        return (
            field_spec.key in cleared_field_keys
            and field_spec.application_field_key in CHECK_KEYS_BY_APPLICATION_FIELD
        )

    @staticmethod
    def _cleared_field_keys(request: RunDocumentChecksRequestDTO) -> Set[str]:
        return {
            field_value.key
            for field_value in request.field_values
            if field_value.edited and not str(field_value.value or "").strip()
        }

    def _build_checks_for_field(
        self,
        request: RunDocumentChecksRequestDTO,
        field_spec: FieldSpecDTO,
        read_value: str,
    ) -> List[CheckDTO]:
        # Three independent questions about one field: does it agree with the
        # application, does it read as the kind of value it claims to be, and is it
        # still in force. A field can answer more than one of them.
        candidates = [
            self._build_comparison_check(
                request=request, field_spec=field_spec, read_value=read_value
            ),
            IdentifierFormatCheck.build(
                document_id=request.document_id,
                field_key=field_spec.key,
                value=read_value,
                # Verhoeff is enforced only when the document carried a QR we could
                # read — the real-extraction showcase path. Legacy mock reads carry
                # no QR, so their invented numbers keep the structural-only check
                # (ADR-009/ADR-013).
                enforce_checksum=request.qr_fields is not None,
            ),
            self._build_validity_check(
                request=request, field_spec=field_spec, read_value=read_value
            ),
        ]
        return [check for check in candidates if check is not None]

    @staticmethod
    def _build_validity_check(
        request: RunDocumentChecksRequestDTO, field_spec: FieldSpecDTO, read_value: str
    ) -> Optional[CheckDTO]:
        if field_spec.comparison_rule != FieldComparisonRule.VALIDITY_WINDOW.value:
            return None
        return ValidityCheck.build(
            document_id=request.document_id,
            field_key=field_spec.key,
            valid_until=read_value,
            scrutiny_today=request.scrutiny_today,
        )

    @staticmethod
    def _build_comparison_check(
        request: RunDocumentChecksRequestDTO, field_spec: FieldSpecDTO, read_value: str
    ) -> Optional[CheckDTO]:
        application_field_key = field_spec.application_field_key
        if application_field_key not in CHECK_KEYS_BY_APPLICATION_FIELD:
            return None
        comparison = FieldComparisonDTO(
            document_id=request.document_id,
            document_type_label=request.document_type.label,
            field_key=field_spec.key,
            field_label=field_spec.label,
            application_field_key=application_field_key,
            read_value=read_value,
            application_value=request.application.field_values.get(
                application_field_key, ""
            ),
            comparison_rule=field_spec.comparison_rule,
            masked=field_spec.masked,
        )
        return FieldComparisonChecks.build(comparison=comparison)

    @staticmethod
    def _read_values_by_field_key(
        request: RunDocumentChecksRequestDTO,
    ) -> Dict[str, str]:
        return {
            field_value.key: str(field_value.value or "").strip()
            for field_value in request.field_values
        }
