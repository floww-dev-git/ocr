# Block Types Reference

Complete reference of all existing block types, enum values, DTO fields, and their relationships.

## Enum Values

### DocumentTemplateBlockType (plugins/constants/dms_enums.py)
Runtime block type identifiers stored in JSON config.

```
HEADER, PARAGRAPH, TABLE, FOOTER, SIGNATURE, SITE_INSPECTION,
OC_SITE_INSPECTION_FINAL_REPORT, OC_SITE_INSPECTION_INTERNAL_REPORT,
PAYMENT, CONDITIONS, BPS_VERIFICATION_REMARKS, GRID, DYNAMIC_TABLE,
REPEATED_TABLE, LIST, PAYMENT_RECEIPT, REMARKS, TDR_REQUESTS,
ENFORCEMENT, ADD_ANOTHER_GOF_TABLE, SHORTFALL_FIELD_REMARKS,
APPLICATION_DETAILS_TAB, TDR_LEDGER
```
(23 values total)

### PDFBlockType (plugins/constants/dms_enums.py)
PDF rendering type identifiers. Fewer than DocumentTemplateBlockType because many DT types reuse the same PDF rendering.

```
HEADER, PARAGRAPH, DUAL_HEADER_PARAGRAPH, GRID, TABLE, LIST,
DYNAMIC_TABLE, IMAGE, DUMMY_SIGN, SIGN
```
(10 values total)

### DataLoadingBlockType (sales_crm_core/populate/blocks_templates/populate_document_template_blocks.py)
CSV-facing display names that map to DocumentTemplateBlockType.

| CSV Display Name | Maps to DocumentTemplateBlockType |
|---|---|
| `"Header 1"` | HEADER (title field) |
| `"Header 2"` | HEADER (subtitle field) |
| `"Header 3"` | HEADER (description field) |
| `"Header Right Corner Text"` | HEADER (right_corner_text) |
| `"Header Logo URL"` | HEADER (header_logo_url) |
| `"Paragraph"` | PARAGRAPH (or GRID if multiple in same row) |
| `"Site inspection"` | SITE_INSPECTION |
| `"Fee Table"` | PAYMENT |
| `"Payment Receipt"` | PAYMENT_RECEIPT |
| `"Proceeding Conditions"` | CONDITIONS |
| `"Shortfall Remarks"` | BPS_VERIFICATION_REMARKS |
| `"Rejection Remarks"` | BPS_VERIFICATION_REMARKS |
| `"Notes"` | REMARKS |
| `"OC Site Inspection Final Report"` | OC_SITE_INSPECTION_FINAL_REPORT |
| `"OC Site Inspection Internal Report"` | OC_SITE_INSPECTION_INTERNAL_REPORT |
| `"Table - Repeated"` | REPEATED_TABLE |
| `"Table"` | DYNAMIC_TABLE |
| `"Signature - Header"` | SIGNATURE (header part) |
| `"Signature - Footer"` | SIGNATURE (footer/description part) |
| `"Ordered List"` | LIST |
| `"Unordered List"` | LIST |
| `"TDR Requests"` | TDR_REQUESTS |
| `"TDR Ledger Table"` | TDR_LEDGER |
| `"Enforcement"` | ENFORCEMENT |
| `"Add Another GoF Table"` | ADD_ANOTHER_GOF_TABLE |
| `"ShortFall Field Remarks"` | SHORTFALL_FIELD_REMARKS |
| `"Application Details Tab"` | APPLICATION_DETAILS_TAB |

### Other Relevant Enums
- `TextAlignment`: `LEFT`, `RIGHT`, `CENTER`
- `DtListBlockPresentationType`: `UNORDERED_LIST`, `ORDERED_LIST`
- `RepeatedTableDataSourceType`: `PIPELINE_ITEM`, `BUILDING`, `PLOT`, `FLOOR`
- `ParagraphStyles`: `INDENT_FIRST_LINE`, `NO_INDENT`, `INDENT_ALL_LINES`
- `AllowedRemarksSectionEnum`: `FIELD_WISE_REMARKS`, `USER_REMARKS`
- `ShowAmountsEnum`: `TOTAL_APPLIED_FEE_HEADS_NET_AMOUNT`, `TOTAL_REMAINING_AMOUNT`, `TOTAL_PAID_AMOUNT`, `TOTAL_CALCULATED_AMOUNT`
- `SigningQRPosition`: `QR_WITH_SIGN`, `QR_AT_TOP`

---

## DT Block DTOs (plugins/interactors/dms/dtos.py)

### Base Class
```python
@dataclass
class BaseDocumentTemplateBlockDTO:
    block_id: str
    order: int
    block_type: DocumentTemplateBlockType
```

### All Block DTOs

| DTO Class | Block Type | Extra Fields |
|---|---|---|
| `DtHeaderBlockDTO` | HEADER | `header_logo_url`, `title`, `subtitle`, `description`, `right_corner_text` |
| `DtParagraphBlockDTO` | PARAGRAPH | `heading`, `text_lines: List[str]`, `style`, `inline_heading_and_paragraph` |
| `DtGridBlockDTO` | GRID | `heading`, `grid_unit_dtos: List[DtGridUnitDTO]` |
| `DtTableBlockDTO` | TABLE | `title`, `field_ids: List[str]`, `column_width_percentages: List[float]` |
| `FooterBlockDTO` | FOOTER | `signature_field_name`, `right_corner_text` |
| `DtSignatureBlockDTO` | SIGNATURE | `signature_field_name`, `text_lines`, `capture_current_date`, `capture_current_time`, `description` |
| `DtSiteInspectionBlockDTO` | SITE_INSPECTION | `table_heading`, `enable_site_inspection_table_grouping` |
| `DtEnforcementBlockDTO` | ENFORCEMENT | `heading`, `tab_id`, `section_id`, `geo_location_field_ids`, `photograph_field_ids` |
| `DtOCSiteInspectionInternalReportBlockDTO` | OC_SITE_INSPECTION_INTERNAL_REPORT | `heading`, `task_template_id` |
| `DtOCSiteInspectionFinalReportBlockDTO` | OC_SITE_INSPECTION_FINAL_REPORT | `heading`, `task_template_id`, `table_dtos: List[DtOCSiteInspectionTableDTO]` |
| `DtPaymentBlockDTO` | PAYMENT | `title`, `column_width_percentages`, `enable_fee_header_grouping`, `show_amounts`, `fee_header_amount_type` |
| `DtPaymentReceiptBlockDTO` | PAYMENT_RECEIPT | `title` |
| `DtConditionsBlockDTO` | CONDITIONS | `title`, `body`, `skip_block_in_empty_conditions`, `category_ids: List[str]` |
| `DtBpsVerificationRemarksBlockDTO` | BPS_VERIFICATION_REMARKS | `table_heading`, `task_template_id`, `assignee_field_ids`, `recommendation_enums`, `allowed_remarks_sections` |
| `DtDynamicTableBlockDTO` | DYNAMIC_TABLE | `heading`, `row_dtos: List[DtDynamicTableRowDTO]`, `enable_table_borders` |
| `DtRemarksBlockDTO` | REMARKS | `show_sign`, `sign_content: List[str]` |
| `DtRepeatedTableBlockDTO` | REPEATED_TABLE | `heading`, `data_source: RepeatedTableDataSourceType`, `row_dtos: List[DtRepeatedTableRowDTO]` |
| `DtListBlockDTO` | LIST | `heading`, `description`, `text_lines`, `presentation_type`, `inline_heading_and_body` |
| `DtTDRRequestsBlockDTO` | TDR_REQUESTS | `heading`, `tdr_request_statuses: List[TDRRequestStatus]` |
| `DtTDRLedgerBlockDTO` | TDR_LEDGER | `heading`, `tdr_account_no_field_id`, `tdr_authority_field_id` |
| `DtAddAnotherGoFTableBlockDTO` | ADD_ANOTHER_GOF_TABLE | `heading`, `enable_table_borders`, `add_another_gof_field_dtos: List[DtAddAnotherGoFFieldDTO]` |
| `DtShortFallFieldRemarksBlockDTO` | SHORTFALL_FIELD_REMARKS | `title` |
| `DtApplicationDetailsTabBlockDTO` | APPLICATION_DETAILS_TAB | `title`, `tab_id` |

### Nested Support DTOs
- `DtGridUnitDTO`: `text_lines`, `unit_width: float`, `alignment: TextAlignment`
- `DtDynamicTableCellDTO`: `text`, `cell_width: float`, `background_color`
- `DtDynamicTableRowDTO`: `cell_dtos: List[DtDynamicTableCellDTO]`
- `DtRepeatedTableCellDTO`: `text`, `cell_width`, `background_color`
- `DtRepeatedTableRowDTO`: `cell_dtos: List[DtRepeatedTableCellDTO]`
- `DtOCSiteInspectionColumnDTO`: `column_id`, `display_name`
- `DtOCSiteInspectionTableDTO`: `table_id`, `display_column_ids`, `column_dtos`
- `DtAddAnotherGoFFieldDTO`: `field_id`, `width: float`

### Union Type
```python
CUSTOM_DOCUMENT_BLOCKS_UNION_TYPE = Union[
    DtHeaderBlockDTO, DtParagraphBlockDTO, DtTableBlockDTO, FooterBlockDTO,
    DtSignatureBlockDTO, DtSiteInspectionBlockDTO,
    DtOCSiteInspectionInternalReportBlockDTO, DtOCSiteInspectionFinalReportBlockDTO,
    DtPaymentBlockDTO, DtConditionsBlockDTO, DtBpsVerificationRemarksBlockDTO,
    DtGridBlockDTO, DtDynamicTableBlockDTO, DtRepeatedTableBlockDTO, DtListBlockDTO,
    DtPaymentReceiptBlockDTO, DtRemarksBlockDTO, DtTDRRequestsBlockDTO,
    DtTDRLedgerBlockDTO, DtEnforcementBlockDTO, DtAddAnotherGoFTableBlockDTO,
    DtShortFallFieldRemarksBlockDTO, DtApplicationDetailsTabBlockDTO,
]
```

---

## PDF Block DTOs (plugins/interactors/dms/pdf_blocks/dtos.py)

### Base Class
```python
@dataclass
class BasePDFBlockDTO:
    block_id: str
    block_type: PDFBlockType
```

### All PDF Block DTOs

| DTO Class | PDF Type | Extra Fields |
|---|---|---|
| `PDFHeaderBlockDTO` | HEADER | `logo_url`, `header_text`, `sub_header_text`, `sub_sub_header_text`, `right_block_text` |
| `PDFParagraphBlockDTO` | PARAGRAPH | `heading`, `text_lines: List[str]`, `style`, `inline_heading_and_paragraph` |
| `PDFDualHeaderParagraphBlockDTO` | DUAL_HEADER_PARAGRAPH | `left_heading`, `right_heading`, `body`, `body_content_type: PDFBodyContentType` |
| `PDFGridBlockDTO` | GRID | `heading`, `grid_unit_dtos: List[PDFGridUnitDTO]` |
| `PDFTableBlockDTO` | TABLE | `heading`, `column_widths: List[float]`, `table_data: List[List[Any]]` |
| `PDFListBlockDTO` | LIST | `heading`, `description`, `text_lines`, `presentation_type: PresentationType`, `inline_heading_and_body` |
| `PDFDynamicTableBlockDTO` | DYNAMIC_TABLE | `heading`, `row_dtos: List[PDFDynamicTableRowDTO]`, `enable_table_borders` |
| `PDFImageBlockDTO` | IMAGE | `heading`, `image_url_dtos: List[PDFImageURLDTO]` |
| `PDFDummySignBlockDTO` | DUMMY_SIGN | `signature_field_name` |
| `PDFSignBlockDTO` | SIGN | `sign_img_link`, `text_lines: List[str]` |

### Nested Support DTOs
- `PDFGridUnitDTO`: `text_lines`, `unit_width`, `alignment: TextAlignment`
- `PDFDynamicTableCellDTO`: `text`, `cell_width`, `background_color`
- `PDFDynamicTableRowDTO`: `cell_dtos: List[PDFDynamicTableCellDTO]`
- `PDFImageURLDTO`: `image_url`, `caption`

### Union Type
```python
PDF_BLOCK_UNION_TYPE = Union[
    PDFHeaderBlockDTO, PDFParagraphBlockDTO, PDFGridBlockDTO,
    PDFTableBlockDTO, PDFListBlockDTO, PDFDynamicTableBlockDTO,
    PDFImageBlockDTO, PDFDualHeaderParagraphBlockDTO,
    PDFDummySignBlockDTO, PDFSignBlockDTO,
]
```

---

## Storage Serialization Keys (plugins/storages/dms_storage.py)

JSON key names used in storage (may differ from DTO field names):

| Block Type | JSON Keys |
|---|---|
| HEADER | `header_logo_url`, `title`, `subtitle`, `description`, `right_corner_text` |
| PARAGRAPH | `heading`, `text_lines`, `style`, `inline_heading_and_paragraph` |
| REMARKS | `show_sign`, `sign_content` |
| LIST | `heading`, `text_lines`, `description`, `presentation_type`, `inline_heading_and_body` |
| FOOTER | `signature_field_name`, `right_corner_text` |
| TABLE | `title`, `field_ids`, `column_width_percentages` |
| SIGNATURE | `capture_current_date`, `capture_current_time`, `signature_field_name`, `description`, `text_lines` |
| SITE_INSPECTION | `table_heading`, `enable_site_inspection_table_grouping` |
| OC_SI_FINAL_REPORT | `heading`, `task_template_id`, `tables` (nested: `table_id`, `column_ids`, `columns`) |
| OC_SI_INTERNAL_REPORT | `heading`, `task_template_id` |
| PAYMENT | `title`, `column_width_percentages`, `enable_fee_header_grouping`, `show_amounts`, `fee_header_amount_type` |
| PAYMENT_RECEIPT | `title` |
| CONDITIONS | `title`, `body`, `skip_block_in_empty_conditions`, `category_ids` |
| BPS_VERIFICATION_REMARKS | `task_template_id`, `table_heading`, `assignee_field_ids`, `recommendation_enums`, `allowed_remarks_sections` |
| GRID | `heading`, `grid_units` (nested: `text_lines`, `unit_width`, `alignment`) |
| DYNAMIC_TABLE | `heading`, `rows` (nested: `cells` -> `text`, `cell_width`, `background_color`), `enable_table_borders` |
| REPEATED_TABLE | `heading`, `data_source`, `rows` (same cell structure) |
| TDR_REQUESTS | `heading`, `tdr_request_statuses` |
| ENFORCEMENT | `heading`, `tab_id`, `section_id`, `geolocation_field_ids`, `photograph_field_ids` |
| ADD_ANOTHER_GOF_TABLE | `heading`, `enable_table_borders`, `add_another_gof_fields` (nested: `field_id`, `width`) |
| SHORTFALL_FIELD_REMARKS | `title` |
| APPLICATION_DETAILS_TAB | `title`, `tab_id` |
| TDR_LEDGER | `heading`, `tdr_account_no_field_id`, `tdr_authority_field_id` |

**Key asymmetry**: Enforcement block uses `geolocation_field_ids` in JSON but `geo_location_field_ids` in the DTO.

---

## CSV Column Keys (DataKeys enum)

```
DOCUMENT_TEMPLATE_ID, HEADING, BODY, BLOCK_TYPE, VARIABLE_IDS,
REPEATED_TABLE_DATA_SOURCE, TABLE_ID, ENABLE_TABLE_BORDERS,
ROW_NUMBER, ROW_POSITION, WIDTH_WITHIN_ROW, TASK_TEMPLATE_ID,
CATEGORY_IDS, ALLOWED_REMARKS_SECTIONS, STYLE,
INLINE_HEADING_AND_PARAGRAPH, TDR_REQUEST_STATUSES,
TDR_ACCOUNT_NO_FIELD_REFERENCE_ID, TDR_AUTHORITY_FIELD_REFERENCE_ID,
TAB_ID, APPLICATION_SECTION_TAB_ID, SECTION_ID,
PHOTOGRAPH_FIELD_REF_IDS, GEO_COORDINATES_FIELD_REF_IDS,
OC_SITE_INSPECTION_TABLE_COLUMNS, ADD_ANOTHER_GOF_FIELD_REFERENCES,
SIGNATURE_FIELD_NAME, CAPTURE_CURRENT_DATE, CAPTURE_CURRENT_TIME,
ENABLE_FEE_HEADER_GROUPING, ENABLE_SITE_INSPECTION_TABLE_GROUPING,
ASSIGNEE_FIELD_REF_IDS, SHOW_AMOUNTS, FEE_HEADER_AMOUNT_TYPE,
SHOW_SIGN
```

### Variable Placeholder Pattern
- CSV uses `{{variable_id}}` syntax
- `_update_variables_format()` converts to `<<variable_id>>` for storage
- Regex: `r"\{\{([^}]+)\}\}"`

---

## PDFBlocksGenerationRequiredDetailsDTO (core_blocks_converter/dtos.py)

All pre-fetched data available to converters:

```python
pipeline_item_id: str
placeholder_data: Dict[str, Any]                    # variable_id -> resolved value
placeholder_display_name_map: Dict[str, str]        # variable_id -> display name
payment_log_dtos: List[PaymentLogDTO]
fee_breakdown_dto: Optional[EntityFeeBreakdownForLettersDTO]
remark_dtos: List[PDFPipelineItemRemarksDTO]
tdr_request_dtos: List[PDFTDRRequestPipelineItemDTO]
category_dtos: List[CategoryDTO]
pipeline_item_checkpoint_dtos: List[EntityCategoryCheckpointResponseDTO]
site_inspection_dto: Optional[SiteInspectionTaskDataDTO]
enforcement_dto: Optional[EnforcementDataDTO]
add_another_gof_table_dtos: List[AddAnotherGoFTableBlockDTO]
oc_site_inspection_internal_report_dtos: List[OCSiteInspectionTaskDataDTO]
oc_site_inspection_final_report_dtos: List[OCSiteInspectionTaskDataDTO]
bps_verif_task_template_dtos: List[DtBpsVerificationTaskTemplateDataDTO]
computed_engine_variables_dto: ComputedEngineVariablesDTO
internal_obj_response_map: Dict[str, FIELD_RESPONSE_TYPE]
pdf_footer_line: Optional[str]
shortfall_field_remark_dtos: List[ShortFallFieldDataForLettersDTO]
tdr_ledger_table_dto: Optional[TDRLedgerTableDTO]
tab_details: List[PDFTabDetailsDTO]
```

---

## Dispatcher Map (get_pdf_blocks_for_blocks_template.py)

Current routing map entries (22 entries - FOOTER is not in the map, it is skipped):

```python
pdf_block_generator_map = {
    BlockType.HEADER.value:                          _get_pdf_blocks_for_header_block,
    BlockType.PARAGRAPH.value:                       _get_pdf_blocks_for_paragraph_block,
    BlockType.TABLE.value:                           _get_pdf_blocks_for_table_block,
    BlockType.GRID.value:                            _get_pdf_blocks_for_grid_block,
    BlockType.PAYMENT.value:                         _get_pdf_blocks_for_payment_block,
    BlockType.CONDITIONS.value:                      _get_pdf_blocks_for_conditions_block,
    BlockType.DYNAMIC_TABLE.value:                   _get_pdf_blocks_for_dynamic_table_block,
    BlockType.BPS_VERIFICATION_REMARKS.value:        _get_pdf_blocks_for_bps_verification_block,
    BlockType.SITE_INSPECTION.value:                 _get_pdf_blocks_for_site_inspection_block,
    BlockType.REPEATED_TABLE.value:                  _get_pdf_blocks_for_repeated_table_block,
    BlockType.LIST.value:                            _get_pdf_blocks_for_list_block,
    BlockType.PAYMENT_RECEIPT.value:                 _get_pdf_blocks_for_payment_receipt_block,
    BlockType.REMARKS.value:                         _get_pdf_blocks_for_remarks_block,
    BlockType.SIGNATURE.value:                       _get_pdf_blocks_for_sign_block,
    BlockType.OC_SITE_INSPECTION_FINAL_REPORT.value: _get_pdf_blocks_for_oc_site_inspection_final_report_block,
    BlockType.OC_SITE_INSPECTION_INTERNAL_REPORT.value: _get_pdf_blocks_for_oc_site_inspection_internal_report_block,
    BlockType.TDR_REQUESTS.value:                    _get_pdf_blocks_for_tdr_requests_block,
    BlockType.TDR_LEDGER.value:                      _get_pdf_blocks_for_tdr_ledger_block,
    BlockType.ENFORCEMENT.value:                     _get_pdf_blocks_for_enforcement_block,
    BlockType.ADD_ANOTHER_GOF_TABLE.value:           _get_pdf_blocks_for_add_another_gof_block,
    BlockType.SHORTFALL_FIELD_REMARKS.value:         _get_pdf_blocks_for_shortfall_field_remarks_block,
    BlockType.APPLICATION_DETAILS_TAB.value:         _get_pdf_blocks_for_application_tab_details,
}
```

---

## Existing Converter Files

All in `plugins/interactors/dms/core_blocks_converter/`:

| File | Class |
|---|---|
| `dt_header_block.py` | `DtHeaderBlockInteractor` |
| `dt_paragraph_block.py` | `DtParagraphBlockInteractor` |
| `dt_table_block.py` | `DtTableBlockInteractor` |
| `dt_grid_block.py` | `DtGridBlockInteractor` |
| `dt_dynamic_table_block.py` | `DtDynamicTableBlockInteractor` |
| `dt_repeated_table_block.py` | `DtRepeatedTableBlockInteractor` |
| `dt_list_block.py` | `DtListBlockInteractor` |
| `dt_conditions_block.py` | `DtConditionsBlockInteractor` |
| `dt_payment_block.py` | `DtPaymentBlockInteractor` |
| `dt_payment_receipt_block.py` | `DtPaymentReceiptBlockInteractor` |
| `dt_remarks_block.py` | `DtRemarksBlockInteractor` |
| `dt_sign_block.py` | `DtSignBlockInteractor` |
| `dt_signature_block.py` | `DtSignatureBlockInteractor` |
| `dt_site_inspection_block.py` | `DtSiteInspectionBlockInteractor` |
| `dt_bps_verification_block.py` | `DtBpsVerificationBlockInteractor` |
| `dt_oc_site_inspection_final_report_block.py` | `DtOCSiteInspectionFinalReportBlockInteractor` |
| `dt_oc_site_inspection_internal_report_block.py` | `DtOCSiteInspectionInternalReportBlockInteractor` |
| `dt_tdr_requests_block.py` | `DtTDRRequestsBlockInteractor` |
| `dt_tdr_ledger_block.py` | `DtTDRLedgerBlockInteractor` |
| `dt_enforcement_deviation_table_block.py` | `DtEnforcementDeviationTableBlockInteractor` |
| `dt_add_another_gof_table_block.py` | `DtAddAnotherGofTypeBlockInteractor` |
| `dt_shortfall_field_remarks_block.py` | `DtShortFallFieldRemarksBlockInteractor` |
| `dt_application_details_tab_block.py` | `DtApplicationDetailsTabBlockInteractor` |

---

## Required Details Data Sources

Service calls made in `get_pdf_blocks_generation_required_details.py`:

| Data | Block Type | Service Call |
|---|---|---|
| Placeholder data | ALL | `engine_variables.compute_engine_variables()` |
| Payment logs | PAYMENT, PAYMENT_RECEIPT | `fee_engine.get_payment_logs_for_entity()` |
| Fee breakdown | PAYMENT | `fee_engine.get_entity_fee_breakdown_for_letters()` |
| Site inspection | SITE_INSPECTION | `bps_service.get_site_inspection_task_data_dto()` |
| Checkpoints | CONDITIONS | `bps_service.get_checked_checkpoints_for_pipeline_item()` |
| BPS verification | BPS_VERIFICATION_REMARKS | `bps_service.get_bps_verification_task_template_data()` |
| OC inspection | OC_SI_FINAL/INTERNAL | `bps_service.get_oc_site_inspection_data_for_pdf()` |
| Enforcement | ENFORCEMENT | `bps_service.get_enforcement_data()` |
| Shortfall | SHORTFALL_FIELD_REMARKS | `bps_service.get_shortfall_fields_data()` |
| Add another GoF | ADD_ANOTHER_GOF_TABLE | `bps_service.get_add_another_gof_data()` |
| Tab details | APPLICATION_DETAILS_TAB | `bps_service.get_application_tab_details_for_letters()` |
| TDR requests | TDR_REQUESTS | `tdr_service.get_entity_tdr_requests_for_pdf()` |
| TDR ledger | TDR_LEDGER | `tdr_service.get_tdr_ledger_table_for_pdf()` |
| Remarks | REMARKS | `sales_crm.get_pipeline_item_remarks_for_pdf()` |
| Footer line | ALL (if footer present) | `sales_crm.get_pipeline_items()` |
