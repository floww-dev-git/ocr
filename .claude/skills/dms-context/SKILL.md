---
name: dms-context
description: Load DMS (Document Management System) domain context including document templates, PDF generation, block types, signing flows, draft/published lifecycle, DocuSign/FlowwSign integration, and pipeline item document workflows. Use when working on DMS features, debugging letter generation issues, or understanding document template architecture.
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write, Bash
---

# DMS Domain Context

Comprehensive reference for the DMS (Document Management System) within the `plugins` Django app. DMS manages document templates and generated PDF documents (called "letters") for pipeline items in the CRM system.

## Domain Overview

DMS enables administrators to define reusable document templates, then generate PDF documents for specific pipeline items (applications). Templates come in two types: uploaded PDF forms with fillable fields, or block-based templates composed from 23 block types that generate PDFs from scratch. Generated documents support digital signatures via FlowwSign (OTP-based) or DocuSign, QR codes, watermarks, and border styles.

## Types of Document Templates

| Aspect | FORM_FIELDS_TEMPLATE | BLOCKS_TEMPLATE |
|--------|---------------------|-----------------|
| **PDF Source** | Admin uploads a PDF file with fillable form fields | PDF generated from scratch using block definitions |
| **Generation Method** | PyPDF fills form fields with CRM data | Block converters + ReportLab Platypus flowables |
| **Data Mapping** | Field-by-field mapping (FIXED value or LEAD_DETAILS field) | Engine variables resolve placeholders in text blocks |
| **Signing Support** | FlowwSign (PyHanko OTP) + DocuSign | FlowwSign only (system auto-sign via `sign_document_by_system`) |
| **Preview Support** | Shows uploaded PDF with mock field values | Generates full PDF preview with mock data |
| **QR Code** | Applied via PdfWriter overlay on form-filled PDF | Rendered as flowable during PDF build, or canvas overlay on sign |
| **Border Style** | Not supported | TDR_CERTIFICATE, TDR_LETTER_OF_INTENT |
| **Draft/Published** | Always PUBLISHED | Supports DRAFT (dummy sign placeholders) then PUBLISHED (actual signatures) |

## Core Entities

| Entity | Model | Purpose |
|--------|-------|---------|
| **DocumentTemplate** | `plugins.models.dms.DocumentTemplate` | Template definition — name, type, pipeline association, border style, QR position |
| **DocumentTemplateVersion** | `plugins.models.dms.DocumentTemplateVersion` | Versioned config — blocks JSON, form fields mapping, signature fields, QR config |
| **Document** | `plugins.models.dms.Document` | Generated document for a pipeline item — latest file URLs, signing status |
| **DocumentVersion** | `plugins.models.dms.DocumentVersion` | Individual version of a generated document — PDF file, state (DRAFT/PUBLISHED), sign locations |
| **DocusignPluginConfig** | `plugins.models.dms.DocusignPluginConfig` | DocuSign API credentials and account configuration |

### Entity Relationships
```
DocumentTemplate (1) ──> (N) DocumentTemplateVersion
DocumentTemplate (1) ──> (N) Document
Document (1) ──> (N) DocumentVersion
DocumentVersion ──> DocumentTemplateVersion (FK: dt_version)
DocumentTemplate ──> pipeline_item_template_id (links to CRM template config)
Document ──> pipeline_item_id (links to specific application)
```

## Key Enums Quick Reference

| Enum | Values | Purpose |
|------|--------|---------|
| `DocumentTemplateType` | FORM_FIELDS_TEMPLATE, BLOCKS_TEMPLATE | Template generation method |
| `DocumentVersionState` | DRAFT, PUBLISHED | Document version lifecycle state |
| `DocumentTemplateBlockType` | HEADER, PARAGRAPH, TABLE, GRID, LIST, FOOTER, SIGNATURE, DYNAMIC_TABLE, REPEATED_TABLE, PAYMENT, PAYMENT_RECEIPT, CONDITIONS, SITE_INSPECTION, OC_SITE_INSPECTION_FINAL_REPORT, OC_SITE_INSPECTION_INTERNAL_REPORT, BPS_VERIFICATION_REMARKS, REMARKS, SHORTFALL_FIELD_REMARKS, TDR_REQUESTS, TDR_LEDGER, ENFORCEMENT, ADD_ANOTHER_GOF_TABLE, APPLICATION_DETAILS_TAB | 23 block types for BLOCKS_TEMPLATE |
| `PDFBlockType` | HEADER, PARAGRAPH, DUAL_HEADER_PARAGRAPH, GRID, TABLE, LIST, DYNAMIC_TABLE, IMAGE, DUMMY_SIGN, SIGN | Output PDF block types (converters map DT blocks to these) |
| `DocumentBorderStyle` | TDR_CERTIFICATE, TDR_LETTER_OF_INTENT | PDF border overlay styles |
| `SigningQRPosition` | QR_WITH_SIGN, QR_AT_TOP | Where QR code appears relative to signatures |
| `QRCodePosition` | TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT | QR placement on form fields template pages |
| `QRCodeSize` | SMALL, MEDIUM, LARGE | QR code dimensions |
| `DigitalSigninStatus` | NOT_COMPLETED, COMPLETED | Signing completion tracking |
| `DmsFormFieldMappingSource` | FIXED, LEAD_DETAILS | Form field data source |
| `DocumentFormFieldTypes` | TEXT (/Tx), CHOICE (/Ch), SIGNATURE (/Sig), ADOBE_SIGNATURE (/ADBE_Sign) | PDF form field types |
| `TextAlignment` | LEFT, RIGHT, CENTER | Grid unit text alignment |
| `ParagraphStyles` | INDENT_FIRST_LINE, NO_INDENT, INDENT_ALL_LINES | Paragraph formatting |
| `RepeatedTableDataSourceType` | PIPELINE_ITEM, BUILDING, PLOT, FLOOR | Data source for repeated tables |

## Document Lifecycle: Draft Letter vs Signing Letter

**DRAFT state** — Document generated with `document_version_state=DRAFT`:
- SIGNATURE blocks render as `PDFDummySignBlockDTO` — empty placeholder boxes (width x height)
- `DummySignBlock` flowable tracks its rendered position and stores `SignBlockLocationDTO` (page_number, x_coordinate, y_coordinate, signature_field_name)
- Sign block locations are saved on the `DocumentVersion.sign_block_location_data` field
- No actual signatures or QR codes are placed

**PUBLISHED state** — When `sign_document_by_system` is called on a DRAFT version:
- Reads the DRAFT version PDF bytes from S3
- For each signature field: retrieves user's signature image from IAM service
- Places actual signature images at the stored `SignBlockLocationDTO` coordinates using canvas overlay
- Adds QR code (positioned based on `signing_qr_position`: at middle signature or top-right)
- Saves as new PUBLISHED DocumentVersion

## Architecture Overview

### App Structure
```
plugins/
  models/dms.py                    # All 5 DMS models + validators
  constants/dms_enums.py           # All DMS enum definitions
  constants/dms_constants.py       # DMS constants
  constants/config.py              # S3 paths, URL formats
  interactors/dms/
    generate_document.py           # GenerateDocumentInteractor (core generation)
    sign_document.py               # SignDocumentInteractor (signing flows)
    dtos.py                        # All DMS interactor DTOs
    core_blocks_converter/         # Block DTO -> PDF Block DTO conversion
      get_pdf_blocks_for_blocks_template.py  # Dispatcher (23 block types)
      get_pdf_blocks_generation_required_details.py  # Data gathering
      dt_sign_block.py             # SIGNATURE -> DUMMY_SIGN conversion
      dt_header_block.py, dt_paragraph_block.py, ...  # Per-block converters
      dtos.py                      # PDFBlocksGenerationRequiredDetailsDTO
    pdf_blocks/dtos.py             # PDF-level block DTOs (output of converters)
    pdf_flowable_blocks/           # ReportLab flowable rendering
      generate_pdf.py              # GeneratePDFWithFlowablesInteractor
      qr_and_sign_flowables.py     # QR + signature layout strategies
      dummy_sign_block.py          # DummySignBlock flowable (tracks location)
    pipeline_item_documents/       # Pipeline-specific document operations
      generate_pipeline_item_document.py  # With auto-signing support
      regenerate_pipeline_item_document.py
    pyhanko/                       # FlowwSign (OTP-based) PDF signing
  storage_interfaces/
    dms_storage_interface.py       # DmsStorageInterface (55+ methods)
  storages/
    dms_storage.py                 # PostgreSQL implementation
  exceptions/
    dms_exceptions.py              # 30+ DMS exceptions
  adapters/
    service_adapter.py             # Central adapter with service properties
  app_interfaces/
    service_interface.py           # Public DMS methods for inter-app use
  interactors/mixins/
    dms_mixin.py                   # Shared DMS validation and utility methods
```

## Deep Dive References

- **[Architecture Details](dms-architecture.md)** — Models, DTOs, storage interfaces, exceptions, adapters
- **[Business Flows](dms-flows.md)** — Template creation, document generation, draft/signing lifecycle, DocuSign, GraphQL API
- **[Block Types & PDF Generation](dms-blocks-and-pdf.md)** — All 23 block types, dispatcher map, PDF rendering pipeline, signature two-stage rendering

## Key File Paths

| Layer | Path |
|-------|------|
| Models | `plugins/models/dms.py` |
| Enums | `plugins/constants/dms_enums.py` |
| Constants | `plugins/constants/dms_constants.py` |
| S3 Config | `plugins/constants/config.py` |
| S3 Mixin | `plugins/constants/s3_mixin.py` |
| Interactor DTOs | `plugins/interactors/dms/dtos.py` |
| Block Converter DTOs | `plugins/interactors/dms/core_blocks_converter/dtos.py` |
| PDF Block DTOs | `plugins/interactors/dms/pdf_blocks/dtos.py` |
| PDF Config | `plugins/interactors/dms/pdf_blocks/pdf_config.py` |
| Storage Interface | `plugins/interactors/storage_interfaces/dms_storage_interface.py` |
| Storage Implementation | `plugins/storages/dms_storage.py` |
| Exceptions | `plugins/exceptions/dms_exceptions.py` |
| Generate Document | `plugins/interactors/dms/generate_document.py` |
| Sign Document | `plugins/interactors/dms/sign_document.py` |
| Blocks Dispatcher | `plugins/interactors/dms/core_blocks_converter/get_pdf_blocks_for_blocks_template.py` |
| Required Details | `plugins/interactors/dms/core_blocks_converter/get_pdf_blocks_generation_required_details.py` |
| Sign Block Converter | `plugins/interactors/dms/core_blocks_converter/dt_sign_block.py` |
| Signature Block Converter | `plugins/interactors/dms/core_blocks_converter/dt_signature_block.py` |
| PDF Generation (flowable) | `plugins/interactors/dms/pdf_flowable_blocks/generate_pdf.py` |
| QR + Sign Flowables | `plugins/interactors/dms/pdf_flowable_blocks/qr_and_sign_flowables.py` |
| Dummy Sign Block | `plugins/interactors/dms/pdf_flowable_blocks/dummy_sign_block.py` |
| QR Code Canvas | `plugins/interactors/dms/pdf_flowable_blocks/add_qr_code.py` |
| Signature Layout Strategies | `plugins/interactors/dms/pdf_flowable_blocks/signature_layout_strategies.py` |
| Pipeline Item Docs | `plugins/interactors/dms/pipeline_item_documents/generate_pipeline_item_document.py` |
| Regenerate Docs | `plugins/interactors/dms/pipeline_item_documents/regenerate_pipeline_item_document.py` |
| Preview Template | `plugins/interactors/dms/pipeline_item_documents/get_preview_for_document_template.py` |
| Rejection Watermark | `plugins/interactors/dms/pipeline_item_documents/add_rejection_watermark_to_document.py` |
| PyHanko Signing | `plugins/interactors/dms/pyhanko/sign_pdf_through_api.py` |
| DMS Mixin | `plugins/interactors/mixins/dms_mixin.py` |
| App Interface | `plugins/app_interfaces/service_interface.py` |
| GraphQL Queries | `sales_crm_graphql/dms/queries.py` |
| GraphQL Mutations | `sales_crm_graphql/dms/mutations/` |
| GraphQL DataLoaders | `sales_crm_graphql/dms/dataloaders/` |
| GraphQL Types | `sales_crm_graphql/dms/types/` |
| GraphQL Resolvers | `sales_crm_graphql/dms/resolvers/` |
