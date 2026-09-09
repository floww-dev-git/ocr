# DMS Block Types & PDF Generation

Complete reference for all 23 document template block types, the block conversion pipeline, PDF rendering engines, and the two-stage signature rendering system.

## Complete Block Types Reference

### Layout Blocks

| Block Type | Enum | DT DTO | Key Fields | PDF Output | Converter |
|------------|------|--------|------------|------------|-----------|
| **HEADER** | `DocumentTemplateBlockType.HEADER` | `DtHeaderBlockDTO` | header_logo_url, title, subtitle, description, right_corner_text | `PDFHeaderBlockDTO` | `dt_header_block.py` |
| **PARAGRAPH** | `DocumentTemplateBlockType.PARAGRAPH` | `DtParagraphBlockDTO` | heading, text_lines (with `{{variable}}` placeholders), style, inline_heading_and_paragraph | `PDFParagraphBlockDTO` | `dt_paragraph_block.py` |
| **GRID** | `DocumentTemplateBlockType.GRID` | `DtGridBlockDTO` | heading, grid_unit_dtos (List[DtGridUnitDTO]: text_lines, unit_width, alignment) | `PDFGridBlockDTO` | `dt_grid_block.py` |
| **LIST** | `DocumentTemplateBlockType.LIST` | `DtListBlockDTO` | heading, description, text_lines, presentation_type (UNORDERED/ORDERED), inline_heading_and_body | `PDFListBlockDTO` | `dt_list_block.py` |
| **FOOTER** | `DocumentTemplateBlockType.FOOTER` | `FooterBlockDTO` | signature_field_name, right_corner_text | `PDFParagraphBlockDTO` | `dt_footer_block.py` |

### Data Blocks

| Block Type | Enum | DT DTO | Key Fields | Data Source | PDF Output | Special Behavior |
|------------|------|--------|------------|-------------|------------|------------------|
| **TABLE** | `DocumentTemplateBlockType.TABLE` | `DtTableBlockDTO` | title, field_ids, column_width_percentages | Engine variables (field_ids resolved from placeholder_data + internal_obj_response_map) | `PDFTableBlockDTO` | Resolves field_ids to display_name + value pairs |
| **DYNAMIC_TABLE** | `DocumentTemplateBlockType.DYNAMIC_TABLE` | `DtDynamicTableBlockDTO` | heading, row_dtos (List[DtDynamicTableRowDTO]: cell_dtos with text, cell_width, background_color), enable_table_borders | Pre-configured static data in block config | `PDFDynamicTableBlockDTO` | Placeholders in cell text resolved from placeholder_data |
| **REPEATED_TABLE** | `DocumentTemplateBlockType.REPEATED_TABLE` | `DtRepeatedTableBlockDTO` | heading, data_source (PIPELINE_ITEM/BUILDING/PLOT/FLOOR), row_dtos | Engine variables (repeats per entity from computed_engine_variables_dto) | `PDFDynamicTableBlockDTO` | Repeats table for each entity (building, floor, plot) |

### Payment Blocks

| Block Type | Enum | DT DTO | Key Fields | Data Source | PDF Output | Special Behavior |
|------------|------|--------|------------|-------------|------------|------------------|
| **PAYMENT** | `DocumentTemplateBlockType.PAYMENT` | `DtPaymentBlockDTO` | title, column_width_percentages, enable_fee_header_grouping, show_amounts (List[ShowAmountsEnum]), fee_header_amount_type | FeeEngine (fee_breakdown_dto) | `PDFTableBlockDTO` | Groups fee headers, shows configurable amount rows (net, remaining, paid, calculated) |
| **PAYMENT_RECEIPT** | `DocumentTemplateBlockType.PAYMENT_RECEIPT` | `DtPaymentReceiptBlockDTO` | title | FeeEngine (payment_log_dtos) | `PDFTableBlockDTO` | Renders payment receipt table from payment logs |

### BPS Integration Blocks

| Block Type | Enum | DT DTO | Key Fields | Data Source | PDF Output | Special Behavior |
|------------|------|--------|------------|-------------|------------|------------------|
| **CONDITIONS** | `DocumentTemplateBlockType.CONDITIONS` | `DtConditionsBlockDTO` | title, body, skip_block_in_empty_conditions, category_ids | BPS service (category_dtos, checkpoint_dtos) | `PDFTableBlockDTO` / `PDFParagraphBlockDTO` | Skips entire block if no conditions and skip_block_in_empty_conditions=True |
| **SITE_INSPECTION** | `DocumentTemplateBlockType.SITE_INSPECTION` | `DtSiteInspectionBlockDTO` | table_heading, enable_site_inspection_table_grouping | BPS service (site_inspection_dto) | `PDFTableBlockDTO` | Requires task_id in custom_template_inputs |
| **OC_SITE_INSPECTION_INTERNAL_REPORT** | `DocumentTemplateBlockType.OC_SITE_INSPECTION_INTERNAL_REPORT` | `DtOCSiteInspectionInternalReportBlockDTO` | heading, task_template_id | BPS service (oc_site_inspection_internal_report_dtos) | `PDFTableBlockDTO` / `PDFDualHeaderParagraphBlockDTO` | Filters by task_template_id |
| **OC_SITE_INSPECTION_FINAL_REPORT** | `DocumentTemplateBlockType.OC_SITE_INSPECTION_FINAL_REPORT` | `DtOCSiteInspectionFinalReportBlockDTO` | heading, task_template_id, table_dtos (List[DtOCSiteInspectionTableDTO]) | BPS service (oc_site_inspection_final_report_dtos) | `PDFTableBlockDTO` | Custom column display via table_dtos config |
| **BPS_VERIFICATION_REMARKS** | `DocumentTemplateBlockType.BPS_VERIFICATION_REMARKS` | `DtBpsVerificationRemarksBlockDTO` | table_heading, task_template_id, assignee_field_ids, recommendation_enums, allowed_remarks_sections | BPS service (bps_verif_task_template_dtos) | `PDFTableBlockDTO` | Filters by task_template_id, shows field-wise and/or user remarks |
| **ENFORCEMENT** | `DocumentTemplateBlockType.ENFORCEMENT` | `DtEnforcementBlockDTO` | heading, tab_id, section_id, geo_location_field_ids, photograph_field_ids | BPS/SalesCRM (enforcement_dto) | `PDFTableBlockDTO` / `PDFImageBlockDTO` | Renders deviation table + geo photos |
| **ADD_ANOTHER_GOF_TABLE** | `DocumentTemplateBlockType.ADD_ANOTHER_GOF_TABLE` | `DtAddAnotherGoFTableBlockDTO` | heading, enable_table_borders, add_another_gof_field_dtos (List[DtAddAnotherGoFFieldDTO]: field_id, width) | BPS service (add_another_gof_table_dtos) | `PDFDynamicTableBlockDTO` | Renders "add another" group-of-fields data |
| **APPLICATION_DETAILS_TAB** | `DocumentTemplateBlockType.APPLICATION_DETAILS_TAB` | `DtApplicationDetailsTabBlockDTO` | title, tab_id | BPS service (tab_details) | Multiple PDF block types | Renders full tab content as PDF blocks |

### Remarks Blocks

| Block Type | Enum | DT DTO | Key Fields | Data Source | PDF Output | Special Behavior |
|------------|------|--------|------------|-------------|------------|------------------|
| **REMARKS** | `DocumentTemplateBlockType.REMARKS` | `DtRemarksBlockDTO` | show_sign, sign_content | SalesCRM service (remark_dtos) | `PDFParagraphBlockDTO` / `PDFSignBlockDTO` | Renders remarks with optional sign content |
| **SHORTFALL_FIELD_REMARKS** | `DocumentTemplateBlockType.SHORTFALL_FIELD_REMARKS` | `DtShortFallFieldRemarksBlockDTO` | title | BPS service (shortfall_field_remark_dtos) | `PDFTableBlockDTO` | Renders shortfall field-level remarks |

### TDR Blocks

| Block Type | Enum | DT DTO | Key Fields | Data Source | PDF Output | Special Behavior |
|------------|------|--------|------------|-------------|------------|------------------|
| **TDR_REQUESTS** | `DocumentTemplateBlockType.TDR_REQUESTS` | `DtTDRRequestsBlockDTO` | heading, tdr_request_statuses (List[TDRRequestStatus]) | TDR service (tdr_request_dtos) | `PDFTableBlockDTO` | Filters TDR requests by status |
| **TDR_LEDGER** | `DocumentTemplateBlockType.TDR_LEDGER` | `DtTDRLedgerBlockDTO` | heading, tdr_account_no_field_id, tdr_authority_field_id | TDR service (tdr_ledger_table_dto) | `PDFTableBlockDTO` | Resolves TDR account from field responses, fetches ledger |

### Signing Block

| Block Type | Enum | DT DTO | Key Fields | PDF Output (DRAFT) | PDF Output (PUBLISHED) | Special Behavior |
|------------|------|--------|------------|--------------------|-----------------------|------------------|
| **SIGNATURE** | `DocumentTemplateBlockType.SIGNATURE` | `DtSignatureBlockDTO` | signature_field_name, text_lines (placeholders), capture_current_date/time, description, sign_block_width/height | `PDFDummySignBlockDTO` (empty rectangle) | `PDFSignBlockDTO` (actual signature image) | Two-stage rendering; see Signature Block Two-Stage Rendering below |

## Block System Architecture

```
JSON Config (custom_document_template_config)
  │
  ▼
Block DTOs (DtHeaderBlockDTO, DtParagraphBlockDTO, ...)
  │  ← Parsed from JSON by storage layer
  ▼
GetPDFBlocksGenerationRequiredDetailsInteractor
  │  ← Gathers all data needed by all block types
  │  ← Returns PDFBlocksGenerationRequiredDetailsDTO
  ▼
GetPDFBlocksForBlocksTemplateInteractor (DISPATCHER)
  │  ← Routes each block_type to its converter
  │  ← Each converter: (block_dto, required_details_dto) → List[PDF_BLOCK_UNION_TYPE]
  ▼
PDF Block DTOs (PDFHeaderBlockDTO, PDFTableBlockDTO, PDFDummySignBlockDTO, ...)
  │
  ▼
GeneratePDFWithFlowablesInteractor
  │  ← Converts PDF block DTOs to ReportLab Flowables
  │  ← Builds PDF document
  ▼
PDF bytes + List[SignBlockLocationDTO]
```

## Dispatcher Map

The `GetPDFBlocksForBlocksTemplateInteractor` routes each `DocumentTemplateBlockType` to its converter:

| Block Type | Converter File | Interactor Class |
|------------|----------------|-----------------|
| `HEADER` | `dt_header_block.py` | `DtHeaderBlockInteractor` |
| `PARAGRAPH` | `dt_paragraph_block.py` | `DtParagraphBlockInteractor` |
| `TABLE` | `dt_table_block.py` | `DtTableBlockInteractor` |
| `GRID` | `dt_grid_block.py` | `DtGridBlockInteractor` |
| `LIST` | `dt_list_block.py` | `DtListBlockInteractor` |
| `DYNAMIC_TABLE` | `dt_dynamic_table_block.py` | `DtDynamicTableBlockInteractor` |
| `REPEATED_TABLE` | `dt_repeated_table_block.py` | `DtRepeatedTableBlockInteractor` |
| `PAYMENT` | `dt_payment_block.py` | `DtPaymentBlockInteractor` |
| `PAYMENT_RECEIPT` | `dt_payment_receipt_block.py` | `DtPaymentReceiptBlockInteractor` |
| `CONDITIONS` | `dt_conditions_block.py` | `DtConditionsBlockInteractor` |
| `SITE_INSPECTION` | `dt_site_inspection_block.py` | `DtSiteInspectionBlockInteractor` |
| `OC_SITE_INSPECTION_INTERNAL_REPORT` | `dt_oc_site_inspection_internal_report_block.py` | `DtOCSiteInspectionInternalReportBlockInteractor` |
| `OC_SITE_INSPECTION_FINAL_REPORT` | `dt_oc_site_inspection_final_report_block.py` | `DtOCSiteInspectionFinalReportBlockInteractor` |
| `BPS_VERIFICATION_REMARKS` | `dt_bps_verification_block.py` | `DtBpsVerificationBlockInteractor` |
| `REMARKS` | `dt_remarks_block.py` | `DtRemarksBlockInteractor` |
| `SIGNATURE` | `dt_sign_block.py` | `DtSignBlockInteractor` |
| `TDR_REQUESTS` | `dt_tdr_requests_block.py` | `DtTDRRequestsBlockInteractor` |
| `TDR_LEDGER` | `dt_tdr_ledger_block.py` | `DtTDRLedgerBlockInteractor` |
| `ENFORCEMENT` | `dt_enforcement_deviation_table_block.py` | `DtEnforcementDeviationTableBlockInteractor` |
| `ADD_ANOTHER_GOF_TABLE` | `dt_add_another_gof_table_block.py` | `DtAddAnotherGofTypeBlockInteractor` |
| `SHORTFALL_FIELD_REMARKS` | `dt_shortfall_field_remarks_block.py` | `DtShortFallFieldRemarksBlockInteractor` |
| `APPLICATION_DETAILS_TAB` | `dt_application_details_tab_block.py` | `DtApplicationDetailsTabBlockInteractor` |

All converters are in `plugins/interactors/dms/core_blocks_converter/`.

## Required Details DTO

`PDFBlocksGenerationRequiredDetailsDTO` aggregates all external data needed by block converters:

| Field | Type | Source Adapter | Populated When |
|-------|------|---------------|----------------|
| `pipeline_item_id` | str | Input | Always |
| `placeholder_data` | Dict[str, Any] | EngineVariables | Always — resolved variable values |
| `placeholder_display_name_map` | Dict[str, str] | EngineVariables | Always — variable display names |
| `payment_log_dtos` | List[PaymentLogDTO] | FeeEngine | Always |
| `fee_breakdown_dto` | EntityFeeBreakdownForLettersDTO | FeeEngine | Always |
| `remark_dtos` | List[PDFPipelineItemRemarksDTO] | SalesCRM | When REMARKS block present |
| `tdr_request_dtos` | List[PDFTDRRequestPipelineItemDTO] | TDRService | When TDR_REQUESTS block present |
| `category_dtos` | List[CategoryDTO] | BpsService | When CONDITIONS block present |
| `pipeline_item_checkpoint_dtos` | List[EntityCategoryCheckpointResponseDTO] | BpsService | When CONDITIONS block present |
| `site_inspection_dto` | SiteInspectionTaskDataDTO | BpsService | When task_id provided |
| `enforcement_dto` | EnforcementDataDTO | BpsService | When ENFORCEMENT block present |
| `add_another_gof_table_dtos` | List[AddAnotherGoFTableBlockDTO] | BpsService | When ADD_ANOTHER_GOF_TABLE present |
| `oc_site_inspection_internal_report_dtos` | List[OCSiteInspectionTaskDataDTO] | BpsService | When OC_SI_INTERNAL block present |
| `oc_site_inspection_final_report_dtos` | List[OCSiteInspectionTaskDataDTO] | BpsService | When OC_SI_FINAL block present |
| `bps_verif_task_template_dtos` | List[DtBpsVerificationTaskTemplateDataDTO] | BpsService | When BPS_VERIFICATION_REMARKS present |
| `computed_engine_variables_dto` | ComputedEngineVariablesDTO | EngineVariables | Always — raw computed variables |
| `internal_obj_response_map` | Dict[str, FIELD_RESPONSE_TYPE] | FieldService | When TABLE blocks with internal fields |
| `pdf_footer_line` | str | SalesCRM | Always — APPLICATION_ID field value |
| `shortfall_field_remark_dtos` | List[ShortFallFieldDataForLettersDTO] | BpsService | When SHORTFALL_FIELD_REMARKS present |
| `tdr_ledger_table_dto` | TDRLedgerTableDTO | TDRService | When TDR_LEDGER block present |
| `tab_details` | List[PDFTabDetailsDTO] | BpsService | When APPLICATION_DETAILS_TAB present |

## PDF Rendering Engines

### Primary: pdf_flowable_blocks (ReportLab Platypus)

**Location:** `plugins/interactors/dms/pdf_flowable_blocks/`

Uses ReportLab's Platypus flowable system for layout:

| File | Purpose |
|------|---------|
| `generate_pdf.py` | `GeneratePDFWithFlowablesInteractor` — Main PDF builder |
| `customized_doc_template.py` | `CustomizedDocTemplate` — SimpleDocTemplate with border/watermark |
| `header_block.py` | `HeaderBlockV2` — Logo + title + subtitle flowables |
| `paragraph_block.py` | `ParagraphBlockV2` — Styled paragraphs with headings |
| `grid_block.py` | `GridBlockV2` — Multi-column grid layouts |
| `generic_table_block.py` | `GenericTableBlockV2` — Universal table with CellConfig/RowConfig |
| `list_block.py` | `ListBlockV2` — Ordered/unordered lists |
| `image_block.py` | `ImageBlock` — Image embedding with captions |
| `dual_header_paragraph_block.py` | `DualHeaderParagraphBlock` — Two-column heading + body |
| `sign_block.py` | `SignBlockV2` — Actual signature image + text lines |
| `dummy_sign_block.py` | `DummySignBlock` — Empty placeholder rectangle (tracks position) |
| `qr_code_block.py` | `QRCodeBlock` — QR code flowable |
| `qr_and_sign_flowables.py` | `QRAndSignFlowables` — QR + signature layout strategies |
| `signature_layout_strategies.py` | `QRWithSignatureStrategy`, `QRAtTopStrategy` |
| `add_qr_code.py` | `QRCodeBlockCanvas` — Add QR to existing PDF via canvas |
| `disclaimer_block.py` | `DisclaimerBlock` — "Computer generated" disclaimer |
| `footer_block.py` | `FooterBlock` — Page footer |
| `utils.py` | `PDFUtils` — Page width calculations |

**PDF Config** (`plugins/interactors/dms/pdf_blocks/pdf_config.py`):
- `PAGE_SIZE` — Letter size
- `MARGIN` — Page margins
- `BLOCK_SPACING` — Spacing between blocks
- `get_page_width()` — Computed available width

### Canvas-based: pdf_canvas_blocks

Used for overlay operations on existing PDFs (signatures on DRAFT versions, QR codes on signed documents).

### Legacy: pdf_blocks

Older rendering approach, still referenced but primary rendering uses pdf_flowable_blocks.

## Signature Block Two-Stage Rendering

### Stage 1: DRAFT — DummySignBlock

When document is generated with `state=DRAFT`:

```python
# In dt_sign_block.py :: DtSignBlockInteractor.get_pdf_blocks()
DtSignatureBlockDTO → PDFDummySignBlockDTO(
    block_type=PDFBlockType.DUMMY_SIGN,
    signature_field_name=block_dto.signature_field_name,
    sign_block_width=block_dto.sign_block_width,    # e.g., 150
    sign_block_height=block_dto.sign_block_height,   # e.g., 270
)
```

During PDF rendering:
```python
# In dummy_sign_block.py :: DummySignBlock(Flowable)
class DummySignBlock(Flowable):
    # Renders an empty bordered rectangle at (sign_block_width x sign_block_height)
    # After rendering, stores its position:
    self.location = (page_number, x_coordinate, y_coordinate)
    # page_number is 1-indexed
    # x, y are in ReportLab coordinate system (origin at bottom-left)
```

After `doc.build()`:
```python
# In generate_pdf.py :: _prepare_sign_block_locations_list()
SignBlockLocationDTO(
    page_number=sign_block.location[0],
    x_coordinate=sign_block.location[1],
    y_coordinate=sign_block.location[2],
    signature_field_name=sign_block.signature_field_name,
)
```

Stored on `DocumentVersion.sign_block_location_data` as JSON.

### Stage 2: PUBLISHED — Actual Signatures

When `sign_document_by_system()` transitions DRAFT → PUBLISHED:

```python
# In sign_document.py :: _update_signatures_in_custom_document_pdf()
for user_id, field_names in user_signatures_map.items():
    # 1. Get user's signature image URL from IAM
    signature_img_link = iam_service.get_sales_user(user_id).signature_img_link

    # 2. Compute engine variables for placeholder resolution
    placeholder_data = _compute_engine_variables(pipeline_item_dto, user_id)

    for field_name in field_names:
        # 3. Look up stored coordinates
        matching_location = location_map[field_name]  # SignBlockLocationDTO

        # 4. Look up signature config
        signature_field_dto = sig_field_config_map[field_name]  # BlocksTemplateSignatureFieldDTO

        # 5. Resolve {{variable}} placeholders in text_lines
        text_lines, description = replace_placeholder_with_response(
            text_lines=signature_field_dto.text_lines,
            placeholder_data=placeholder_data,
        )

        # 6. Add timestamp if configured
        if signature_field_dto.capture_current_date:
            text_lines.append(date_str)

        # 7. Overlay signature at stored coordinates
        pdf_bytes = add_signature_to_pdf(
            input_pdf_bytes=pdf_bytes,
            signature_lines=text_lines,
            x=matching_location.x_coordinate,
            y=matching_location.y_coordinate,
            page_number=matching_location.page_number,
            signature_img_link=signature_img_link,
            description=description,
        )
```

### QR Code Positioning During Sign

After all signatures are placed, QR code is added (only when transitioning DRAFT → PUBLISHED):

```python
# In sign_document.py :: _add_qr_to_pdf()
if signing_qr_position == SigningQRPosition.QR_AT_TOP:
    # Top-right of page 1
    page_number = 1
    x = page_width - qr_size - margin  # ~55px margin
    y = 755
    qr_width = qr_height = 100

elif signing_qr_position == SigningQRPosition.QR_WITH_SIGN:
    # At middle signature location
    middle_index = len(sign_block_location_dtos) // 2
    middle_location = sign_block_location_dtos[middle_index]
    page_number = middle_location.page_number
    x = 100  # Fixed left position
    y = middle_location.y_coordinate
    qr_width = QRCodeBlockStyles.DEFAULT_QRCODE_WIDTH
    qr_height = QRCodeBlockStyles.DEFAULT_QRCODE_HEIGHT
```

## PDF Post-Processing

### Border Styles

Applied via `CustomizedDocTemplate.border_image_url`:
- `TDR_CERTIFICATE` — Certificate border overlay on every page
- `TDR_LETTER_OF_INTENT` — Letter of intent border overlay

### QR Codes (Form Fields Template)

Configured via `DocumentTemplateQrCodeConfigDTO`:
- `qr_positions`: List of page corners (TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT)
- `qr_size`: SMALL, MEDIUM, LARGE
- `pages`: List of 1-indexed page numbers

Applied via `DmsMixin.generate_qr_code_for_document()` → `GenerateQRCodeForDocumentInteractor`.

### Watermarking

- Template watermark: `CustomizedDocTemplate.watermark_image_url` — applied during Platypus build
- Rejection watermark: `add_rejection_watermark_to_document.py` — overlays "REJECTED" stamp

### Disclaimer

Every blocks-template PDF includes a footer disclaimer:
> "NOTE: This is computer generated letter, doesn't require any manual signatures"

## Cross-Reference

For the step-by-step guide on **adding a new block type** to the system (7-step pipeline: enum → DT DTO → storage serialization → required details → converter → dispatcher → PDF rendering), see the [`document-template-blocks-guide`](../../skills/document-template-blocks-guide/SKILL.md) skill.
