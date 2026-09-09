from typing import Optional

from rapidfuzz import fuzz, utils

from document_extraction.dtos.deed_record_dtos import DeedRecordDTO
from document_scrutiny.constants.chain_constants import PROPERTY_MATCH_SCORE

_PROCESS = utils.default_process


class PropertyMatch:
    """Whether two deeds are about the same piece of land.

    Deliberately three-answered. `None` means neither deed had a survey or plot number
    read off it, and a link must not be penalised for a value nobody captured — only a
    genuine difference counts against it.
    """

    @classmethod
    def same_property(
        cls, deed: DeedRecordDTO, comparison_deed: DeedRecordDTO
    ) -> Optional[bool]:
        left = deed.property_info
        right = comparison_deed.property_info
        if left.survey_no and right.survey_no:
            return cls._agree(left.survey_no, right.survey_no)
        if left.plot_no and right.plot_no:
            return cls._agree(str(left.plot_no), str(right.plot_no))
        return None

    @staticmethod
    def _agree(value: str, comparison_value: str) -> bool:
        # token_set_ratio catches one survey sitting inside a combined deed
        # ("10" within "Sy. 10, 11 & 12") — the property twin of the name-overlap case.
        return (
            max(
                fuzz.token_sort_ratio(value, comparison_value, processor=_PROCESS),
                fuzz.token_set_ratio(value, comparison_value, processor=_PROCESS),
            )
            >= PROPERTY_MATCH_SCORE
        )
