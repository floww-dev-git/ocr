from typing import Any, Dict, Optional

from document_scrutiny.dtos.chain_dtos import (
    ChainFindingDTO,
    ChainLinkDTO,
    ChainOfTitleDTO,
    LinkChecksDTO,
)
from document_scrutiny.dtos.ownership_report_dtos import (
    AttentionItemDTO,
    AuthorityDocumentDTO,
    DocumentRoleRowDTO,
    JourneyEntryDTO,
    OwnershipReportDTO,
    PartySummaryDTO,
    PropertySummaryDTO,
    RiskAssessmentDTO,
    RiskSignalDTO,
)


class OwnershipReportPresenter:
    """The ownership report as the browser reads it.

    Verdicts travel as their own vocabulary, never as glyphs: which icon to draw for a
    break is the interface's decision, and a payload carrying one cannot be rendered
    any other way.
    """

    @classmethod
    def get_report_response(cls, report: OwnershipReportDTO) -> Dict[str, Any]:
        return {
            "threadId": report.thread_id,
            "verdict": {
                "level": report.verdict.level,
                "headline": report.verdict.headline,
                "plain": report.verdict.plain,
            },
            "stats": {
                "titleDeedCount": report.stats.title_deed_count,
                "spanFrom": report.stats.span_from,
                "spanTo": report.stats.span_to,
                "needReview": report.stats.need_review,
                "breaks": report.stats.breaks,
            },
            "property": cls._prep_property(report.property_summary),
            "journey": [cls._prep_journey_entry(entry) for entry in report.journey],
            "authority": [
                cls._prep_authority(document) for document in report.authority
            ],
            "documentsByRole": {
                role: [cls._prep_role_row(row) for row in rows]
                for role, rows in report.documents_by_role.items()
            },
            "attention": [cls._prep_attention(item) for item in report.attention],
            "risk": cls._prep_risk(report.risk),
            "chain": cls._prep_chain(report.chain),
        }

    @staticmethod
    def _prep_property(property_summary: PropertySummaryDTO) -> Dict[str, Any]:
        return {
            "surveyNo": property_summary.survey_no,
            "plotNo": property_summary.plot_no,
            "extentText": property_summary.extent_text,
            "locality": property_summary.locality,
            "boundaries": property_summary.boundaries,
        }

    @classmethod
    def _prep_journey_entry(cls, entry: JourneyEntryDTO) -> Dict[str, Any]:
        return {
            "kind": entry.kind,
            "role": entry.role,
            "badge": entry.badge,
            "party": cls._prep_party(entry.party),
            "meta": entry.meta,
            "isCurrent": entry.is_current,
            "verdict": entry.verdict,
            "label": entry.label,
            "reference": entry.reference,
            "note": entry.note,
            "identityScore": entry.identity_score,
        }

    @staticmethod
    def _prep_party(party: Optional[PartySummaryDTO]) -> Optional[Dict[str, Any]]:
        if party is None:
            return None
        return {
            "name": party.name,
            "nameOriginal": party.name_original,
            "relative": party.relative,
            "othersCount": party.others_count,
        }

    @staticmethod
    def _prep_authority(document: AuthorityDocumentDTO) -> Dict[str, Any]:
        return {
            "documentId": document.document_id,
            "deedType": document.deed_type,
            "docNo": document.doc_no,
            "owner": document.owner,
            "holder": document.holder,
        }

    @staticmethod
    def _prep_role_row(row: DocumentRoleRowDTO) -> Dict[str, Any]:
        return {
            "documentId": row.document_id,
            "deedType": row.deed_type,
            "docNo": row.doc_no,
            "date": row.date,
            "isRoot": row.is_root,
        }

    @staticmethod
    def _prep_attention(item: AttentionItemDTO) -> Dict[str, Any]:
        return {
            "severity": item.severity,
            "verb": item.verb,
            "title": item.title,
            "detail": item.detail,
            "action": item.action,
        }

    @classmethod
    def _prep_risk(
        cls, risk: Optional[RiskAssessmentDTO]
    ) -> Optional[Dict[str, Any]]:
        if risk is None:
            return None
        return {
            "score": risk.score,
            "level": risk.level,
            "signals": [cls._prep_risk_signal(signal) for signal in risk.signals],
        }

    @staticmethod
    def _prep_risk_signal(signal: RiskSignalDTO) -> Dict[str, Any]:
        return {
            "severity": signal.severity,
            "code": signal.code,
            "title": signal.title,
            "detail": signal.detail,
        }

    @classmethod
    def _prep_chain(cls, chain: ChainOfTitleDTO) -> Dict[str, Any]:
        return {
            "overall": chain.overall,
            "counts": dict(chain.counts),
            "orderedDocumentIds": list(chain.ordered_document_ids),
            "excludedDocumentIds": list(chain.excluded_document_ids),
            "duplicateDocumentIds": list(chain.duplicate_document_ids),
            "rolesByDocumentId": dict(chain.roles_by_document_id),
            "links": [cls._prep_link(link) for link in chain.links],
            "findings": [cls._prep_finding(finding) for finding in chain.findings],
        }

    @classmethod
    def _prep_link(cls, link: ChainLinkDTO) -> Dict[str, Any]:
        return {
            "fromDocumentId": link.from_document_id,
            "toDocumentId": link.to_document_id,
            "fromDocNo": link.from_doc_no,
            "toDocNo": link.to_doc_no,
            "verdict": link.verdict,
            "identityScore": link.identity_score,
            "checks": cls._prep_checks(link.checks),
            "notes": list(link.notes),
        }

    @staticmethod
    def _prep_checks(checks: LinkChecksDTO) -> Dict[str, Any]:
        # Only the questions this link could be asked. A check the deed never answered
        # must not travel as `false`, which the browser would read as a failure.
        return dict(checks.asked())

    @staticmethod
    def _prep_finding(finding: ChainFindingDTO) -> Dict[str, Any]:
        return {
            "severity": finding.severity,
            "verdict": finding.verdict,
            "title": finding.title,
            "detail": finding.detail,
        }
