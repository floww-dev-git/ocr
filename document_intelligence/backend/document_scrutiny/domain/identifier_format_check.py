from typing import Callable, Dict, Optional

from document_scrutiny.constants.identifier_fields import IdentifierField
from document_scrutiny.domain.aadhaar_format_check import AadhaarFormatCheck
from document_scrutiny.domain.licence_format_check import LicenceFormatCheck
from document_scrutiny.domain.pan_format_check import PanFormatCheck
from document_scrutiny.dtos.check_dtos import CheckDTO

_Builder = Callable[[str, str, str], CheckDTO]


class IdentifierFormatCheck:
    """Does this number read as the kind of number it claims to be?

    Keyed on the field it was read into, not on what it is compared against: a
    licence number has nothing on the application form to compare with, and its
    shape is still worth checking. Answerable from the document alone, so it is the
    one check that still says something useful when the form is blank.
    """

    @classmethod
    def build(
        cls,
        document_id: str,
        field_key: str,
        value: str,
        enforce_checksum: bool = False,
    ) -> Optional[CheckDTO]:
        build_for_field = cls._builders(enforce_checksum=enforce_checksum).get(
            str(field_key or "")
        )
        if build_for_field is None:
            return None
        return build_for_field(document_id, field_key, value)

    @staticmethod
    def _builders(enforce_checksum: bool) -> Dict[str, _Builder]:
        return {
            IdentifierField.PAN.value: (
                lambda document_id, field_key, value: PanFormatCheck.build(
                    document_id=document_id, field_key=field_key, pan=value
                )
            ),
            IdentifierField.AADHAAR_NUMBER.value: (
                lambda document_id, field_key, value: AadhaarFormatCheck.build(
                    document_id=document_id,
                    field_key=field_key,
                    aadhaar_number=value,
                    enforce_checksum=enforce_checksum,
                )
            ),
            IdentifierField.LICENCE_NUMBER.value: (
                lambda document_id, field_key, value: LicenceFormatCheck.build(
                    document_id=document_id,
                    field_key=field_key,
                    licence_number=value,
                )
            ),
        }
