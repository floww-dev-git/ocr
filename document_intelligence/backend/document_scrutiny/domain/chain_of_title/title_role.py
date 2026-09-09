from document_scrutiny.constants.chain_constants import (
    AGREEMENT_TO_SELL_PHRASE,
    AUTHORITY_DEED_KINDS,
    CONVEYANCE_PHRASE,
    METADATA_DEED_KINDS,
    TITLE_DEED_KINDS,
    TitleRole,
)


class TitleRoleReader:
    """What a document does, read off the deed's own description of itself.

    Only a conveyance forms a chain of title. A power of attorney, a development
    agreement, an agreement to sell or a will grants authority or promises a future
    transfer, and none of them moves ownership — so none belongs in the chain, and an
    absent link between two of them is not a break.

    Carried from sale_deed_poc/build/poc/roles.py.
    """

    @classmethod
    def read(cls, deed_type: str) -> str:
        described = str(deed_type or "").lower()
        if not described:
            # Nothing was read. Treated as a deed, because dropping a document out of
            # the chain in silence is worse than carrying it and reporting the doubt.
            return TitleRole.TITLE.value
        if cls._matches(described, METADATA_DEED_KINDS):
            return TitleRole.METADATA.value
        # Authority is tested before title: "Agreement to Sell" and "Development
        # Agreement cum GPA" contain no title word, and must not fall through to it.
        if cls._matches(described, AUTHORITY_DEED_KINDS) and not cls._conveys_anyway(
            described
        ):
            return TitleRole.AUTHORITY.value
        if cls._matches(described, TITLE_DEED_KINDS):
            return TitleRole.TITLE.value
        return TitleRole.TITLE.value

    @classmethod
    def conveys_title(cls, deed_type: str) -> bool:
        return cls.read(deed_type=deed_type) == TitleRole.TITLE.value

    @staticmethod
    def _matches(described: str, kinds) -> bool:
        return any(kind in described for kind in kinds)

    @staticmethod
    def _conveys_anyway(described: str) -> bool:
        """A genuine "Sale Deed cum ..." still conveys; an agreement to sell does not."""
        return CONVEYANCE_PHRASE in described and AGREEMENT_TO_SELL_PHRASE not in described
