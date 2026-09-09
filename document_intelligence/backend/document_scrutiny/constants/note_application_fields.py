import enum


class NoteApplicationField(enum.Enum):
    """Application fields the scrutiny note describes.

    Restated here rather than imported from the catalog's internals, on the same
    terms as `ComparableApplicationField` (ADR-002 D6): the vocabulary is part of
    this app's contract with the catalog, and a contract test pins it so the two
    sides cannot drift silently.
    """

    APPLICANT_NAME = "applicantName"
    PROPOSED_USE = "proposedUse"
    FLOORS = "floors"
    HEIGHT_M = "heightM"
    SURVEY_NO = "surveyNo"
    PLOT_NO = "plotNo"
    VILLAGE = "village"
