import dataclasses
from typing import Any, Optional

from document_extraction.dtos.deed_record_dtos import DeedRecordDTO
from document_scrutiny.constants.deed_edit_constants import (
    DEED_FIELD_TO_RECORD_PATH,
    EXTENT_FIELD_KEY,
    EXTENT_NUMBER_PATH,
)
from document_scrutiny.domain.comparison_rules.extent_tolerance import ExtentTolerance


class DeedRecordEdit:
    """Carries an officer's correction of a flat deed field into the structured record.

    The chain engine reasons over the nested `DeedRecordDTO`, not the flat values the
    officer edits, so a corrected vendor name that never reached the record would still
    trace as the misread one. This applies the edit to both, keeping them in step.

    A field the chain does not read on — a boundaries or consideration edit — changes
    only the flat value and returns the record untouched.
    """

    @classmethod
    def apply(
        cls,
        deed_record: Optional[DeedRecordDTO],
        field_key: str,
        value: str,
    ) -> Optional[DeedRecordDTO]:
        if deed_record is None:
            return None
        path = DEED_FIELD_TO_RECORD_PATH.get(field_key)
        if path is None:
            return deed_record
        updated = cls._set_path(deed_record, path=path, value=value)
        if field_key == EXTENT_FIELD_KEY:
            # The words carry the extent the officer reads; the number carries the one
            # the chain's arithmetic uses. Correcting one without the other would leave
            # the chain still measuring against the misread area.
            updated = cls._set_path(
                updated,
                path=EXTENT_NUMBER_PATH,
                value=ExtentTolerance.read_extent(value),
            )
        return updated

    @classmethod
    def _set_path(cls, root: Any, path: str, value: Any) -> Any:
        """Returns a copy of `root` with the value at `path` replaced.

        Every node on the way is a frozen dataclass or a tuple, so each is rebuilt
        rather than mutated. A path that does not lead anywhere — a vendor edit on a
        deed that was read with no sellers — is left as it was rather than inventing
        a party the deed never had.
        """
        step, _, remainder = path.partition(".")
        if step.isdigit():
            return cls._set_index(root, index=int(step), remainder=remainder, value=value)
        return cls._set_attribute(
            root, attribute=step, remainder=remainder, value=value
        )

    @classmethod
    def _set_attribute(
        cls, node: Any, attribute: str, remainder: str, value: Any
    ) -> Any:
        if not dataclasses.is_dataclass(node) or not hasattr(node, attribute):
            return node
        if not remainder:
            return dataclasses.replace(node, **{attribute: value})
        child = getattr(node, attribute)
        return dataclasses.replace(
            node, **{attribute: cls._set_path(child, path=remainder, value=value)}
        )

    @classmethod
    def _set_index(cls, node: Any, index: int, remainder: str, value: Any) -> Any:
        if not isinstance(node, tuple):
            return node
        if index >= len(node):
            # The deed was read with fewer parties than the path expects. A vendor
            # correction on a deed that named no seller has nowhere to go, and
            # fabricating one would put a name in the chain the paper never carried.
            return node
        replacement = (
            cls._set_path(node[index], path=remainder, value=value)
            if remainder
            else value
        )
        return node[:index] + (replacement,) + node[index + 1 :]
