"""Risk scoring, carried from sale_deed_poc/build/poc/risk.py.

Every signal is a thing a tired reviewer skims past. The score is a summary of them,
never a substitute: it is display only and moves no verdict.
"""
from typing import Optional, Sequence

from document_extraction.dtos.deed_record_dtos import (
    DeedRecordDTO,
    PartyDTO,
    PropertyInfoDTO,
)
from document_scrutiny.constants.risk_constants import RiskLevel, RiskSignalCode
from document_scrutiny.domain.chain_of_title.chain_of_title import ChainOfTitle
from document_scrutiny.domain.chain_of_title.deed_risk import DeedRisk
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO


def party(
    name: str,
    pan: Optional[str] = None,
    aadhaar: Optional[str] = None,
    relative_name: str = "X",
) -> PartyDTO:
    return PartyDTO(
        name=name,
        relation="s/o",
        relative_name=relative_name,
        address="Kondapur",
        pan=pan,
        aadhaar=aadhaar,
    )


def deed(
    document_id: str,
    doc_no: str,
    registration_date: str = "2010-01-01",
    sellers: Sequence[PartyDTO] = (),
    buyers: Sequence[PartyDTO] = (),
    deed_type: str = "Sale Deed",
    executed_via_gpa: bool = False,
    consideration_inr: Optional[float] = None,
    survey_no: Optional[str] = "9",
    extent_sq_yard: Optional[float] = 100.0,
    prior_deed_refs: Sequence[str] = (),
) -> ChainDeedDTO:
    return ChainDeedDTO(
        document_id=document_id,
        filename="bundle.pdf",
        deed_record=DeedRecordDTO(
            doc_no=doc_no,
            registration_date=registration_date,
            deed_type=deed_type,
            sellers=tuple(sellers) or (party("Seller", pan="AAAPA1111A"),),
            buyers=tuple(buyers) or (party("Buyer", pan="BBBPB2222B"),),
            property_info=PropertyInfoDTO(
                survey_no=survey_no, extent_sq_yard=extent_sq_yard
            ),
            consideration_inr=consideration_inr,
            executed_via_gpa=executed_via_gpa,
            prior_deed_refs=tuple(prior_deed_refs),
        ),
    )


def codes(assessment) -> set:
    return {signal.code for signal in assessment.signals}


def assess(deeds: Sequence[ChainDeedDTO]):
    return DeedRisk.assess(deeds=deeds, chain=ChainOfTitle.validate(deeds=deeds))


class TestSignalsReadOffASingleDeed:
    def test_title_passed_through_a_power_of_attorney_is_flagged(self):
        """Legally weak since the 2011 Suraj Lamp ruling."""
        # Act
        assessment = assess([deed("A", "1/2000", executed_via_gpa=True)])

        # Assert
        assert RiskSignalCode.TITLE_VIA_GPA.value in codes(assessment)

    def test_a_deed_whose_own_type_says_power_of_attorney_is_flagged_too(self):
        # Act
        assessment = assess(
            [deed("A", "1/2000", deed_type="General Power of Attorney")]
        )

        # Assert
        assert RiskSignalCode.TITLE_VIA_GPA.value in codes(assessment)

    def test_an_agreement_to_sell_is_flagged_as_conveying_nothing(self):
        # Act
        assessment = assess([deed("A", "1/2000", deed_type="Agreement to Sell")])

        # Assert
        assert RiskSignalCode.AGREEMENT_ONLY.value in codes(assessment)

    def test_a_deed_naming_no_identifier_for_anybody_is_flagged(self):
        """Without a PAN or Aadhaar nothing about a party can be checked anywhere."""
        # Act
        assessment = assess(
            [deed("A", "1/2000", sellers=(party("Seller"),), buyers=(party("Buyer"),))]
        )

        # Assert
        assert RiskSignalCode.NO_PARTY_IDENTIFIER.value in codes(assessment)

    def test_one_party_carrying_an_identifier_is_enough(self):
        # Act
        assessment = assess(
            [
                deed(
                    "A",
                    "1/2000",
                    sellers=(party("Seller"),),
                    buyers=(party("Buyer", aadhaar="628471039265"),),
                )
            ]
        )

        # Assert
        assert RiskSignalCode.NO_PARTY_IDENTIFIER.value not in codes(assessment)

    def test_a_clean_ordinary_deed_raises_nothing(self):
        # Act
        assessment = assess([deed("A", "1/2000")])

        # Assert
        assert assessment.signals == ()
        assert assessment.score == 0
        assert assessment.level == RiskLevel.LOW.value


class TestSignalsThatOnlyAppearAcrossDeeds:
    def test_one_pan_standing_for_two_different_people_is_flagged(self):
        """The shape of an impersonation."""
        # Arrange
        deeds = [
            deed("A", "1/2000", buyers=(party("Ravi Kumar", pan="AAAPA1111A"),)),
            deed(
                "B",
                "2/2010",
                sellers=(party("Zainab Sheikh", pan="AAAPA1111A"),),
                prior_deed_refs=("1/2000",),
            ),
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert RiskSignalCode.SAME_IDENTIFIER_DIFFERENT_NAMES.value in codes(assessment)
        signal = next(
            signal
            for signal in assessment.signals
            if signal.code == RiskSignalCode.SAME_IDENTIFIER_DIFFERENT_NAMES.value
        )
        assert "AAAPA1111A" in signal.detail

    def test_one_pan_spelled_two_nearly_identical_ways_is_not_flagged(self):
        """A transliteration is not two people, and saying so would be noise."""
        # Arrange
        deeds = [
            deed("A", "1/2000", buyers=(party("Lakshmi Narayanan", pan="AAAPA1111A"),)),
            deed(
                "B",
                "2/2010",
                sellers=(party("Laxmi Narayanan", pan="AAAPA1111A"),),
                prior_deed_refs=("1/2000",),
            ),
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert RiskSignalCode.SAME_IDENTIFIER_DIFFERENT_NAMES.value not in codes(
            assessment
        )

    def test_a_consideration_that_collapses_between_deeds_is_flagged(self):
        """A price should climb over the years; a fall can be distress, benami or
        under-valuation, and the officer is the one who can tell which."""
        # Arrange
        owner = party("Ravi Kumar", pan="AAAPA1111A")
        deeds = [
            deed("A", "1/2000", buyers=(owner,), consideration_inr=5000000.0),
            deed(
                "B",
                "2/2010",
                sellers=(owner,),
                consideration_inr=500000.0,
                prior_deed_refs=("1/2000",),
            ),
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert RiskSignalCode.PRICE_DROP.value in codes(assessment)

    def test_a_price_that_rises_is_not_flagged(self):
        # Arrange
        owner = party("Ravi Kumar", pan="AAAPA1111A")
        deeds = [
            deed("A", "1/2000", buyers=(owner,), consideration_inr=500000.0),
            deed(
                "B",
                "2/2010",
                sellers=(owner,),
                consideration_inr=5000000.0,
                prior_deed_refs=("1/2000",),
            ),
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert RiskSignalCode.PRICE_DROP.value not in codes(assessment)


class TestSignalsTheChainProduces:
    def test_a_broken_chain_is_carried_into_the_risk_picture(self):
        # Arrange
        deeds = [
            deed("A", "1/2000", buyers=(party("Alice", pan="AAAPA1111A"),)),
            deed(
                "B",
                "2/2010",
                sellers=(party("Completely Different", pan="CCCPC3333C"),),
                prior_deed_refs=("1/2000",),
            ),
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert RiskSignalCode.BROKEN_CHAIN.value in codes(assessment)
        assert assessment.level == RiskLevel.HIGH.value

    def test_an_unsourced_extent_is_carried_in_as_a_missing_deed(self):
        # Arrange
        owner = party("Ravi Kumar", pan="AAAPA1111A")
        deeds = [
            deed("A", "1/2000", buyers=(owner,), extent_sq_yard=200.0),
            deed(
                "B",
                "2/2010",
                sellers=(owner,),
                extent_sq_yard=600.0,
                prior_deed_refs=("1/2000",),
            ),
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert RiskSignalCode.MISSING_DEED.value in codes(assessment)


class TestTurningSignalsIntoAScore:
    def test_the_worst_signals_are_put_first(self):
        # Arrange
        deeds = [
            deed("A", "1/2000", executed_via_gpa=True, sellers=(party("Seller"),), buyers=(party("Buyer"),)),
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert [signal.severity for signal in assessment.signals] == ["high", "low"]

    def test_the_score_never_runs_past_a_hundred(self):
        # Arrange — three high signals would total 120 unweighted
        deeds = [
            deed(
                f"D{index}",
                f"{index}/2000",
                registration_date=f"200{index}-01-01",
                deed_type="General Power of Attorney",
                sellers=(party("Seller"),),
                buyers=(party("Buyer"),),
            )
            for index in range(1, 4)
        ]

        # Act
        assessment = assess(deeds)

        # Assert
        assert assessment.score == 100
        assert assessment.level == RiskLevel.HIGH.value

    def test_every_signal_says_why_it_was_raised(self):
        """A score an officer cannot argue with is not evidence."""
        # Act
        assessment = assess([deed("A", "1/2000", executed_via_gpa=True)])

        # Assert
        assert all(signal.title and signal.detail for signal in assessment.signals)
