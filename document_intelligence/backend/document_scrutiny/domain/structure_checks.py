from typing import Mapping, Sequence, Tuple

from document_catalog.dtos.catalog_dtos import StructureSpecDTO
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.check_dtos import CheckDTO


class StructureChecks:
    @classmethod
    def build(
        cls,
        document_id: str,
        structure_specs: Sequence[StructureSpecDTO],
        structure_findings: Mapping[str, bool],
    ) -> Tuple[CheckDTO, ...]:
        """One check per template element the document could carry.

        An element the read left out altogether does not apply to this variant of the
        document and produces no check: an e-PAN is issued without a hologram, so the
        officer is told nothing about its hologram rather than being shown one present
        that is not there, or a warning about one that was never expected.
        """
        return tuple(
            cls._build_check(
                document_id=document_id,
                structure_spec=structure_spec,
                detected=structure_findings[structure_spec.key],
            )
            for structure_spec in structure_specs
            if structure_spec.key in structure_findings
        )

    @staticmethod
    def _build_check(
        document_id: str, structure_spec: StructureSpecDTO, detected: bool
    ) -> CheckDTO:
        label = structure_spec.label
        if detected:
            title = f"{label} present"
            detail = f"{label} found where the standard template expects it."
        else:
            title = f"{label} not detected"
            detail = (
                f"{label} was not detected where the standard template expects it. "
                "Check the original before relying on this copy."
            )
        return CheckDTO(
            check_id=f"{document_id}:structure:{structure_spec.key}",
            document_id=document_id,
            group=CheckGroup.STRUCTURE.value,
            title=title,
            status=CheckStatus.PASS.value if detected else CheckStatus.WARN.value,
            detail=detail,
        )
