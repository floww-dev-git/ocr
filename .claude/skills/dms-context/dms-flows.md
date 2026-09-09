# DMS Business Flows

Detailed documentation of all DMS business flows including template management, document generation, signing lifecycle, and external integrations.

## A: Template Types & Creation

### FORM_FIELDS_TEMPLATE
1. Admin uploads a PDF file containing fillable form fields
2. System extracts form fields (Text `/Tx`, Choice `/Ch`) and signature fields (`/Sig`, `/ADBE_Sign`)
3. Admin maps each form field to a data source:
   - `FIXED` — Static value entered at config time
   - `LEAD_DETAILS` — CRM field ID, resolved at generation time
4. Admin configures signature field positions (x_pixel, y_pixel, page_number) and identification_ids
5. System creates `DocumentTemplate` + `DocumentTemplateVersion` with form_fields_mapping and signature_fields JSON
6. Optional: Configure QR code (positions, size, pages)

### BLOCKS_TEMPLATE
1. Admin composes template from 23 available block types in JSON config
2. Each block has: `block_id`, `order`, `block_type`, and type-specific fields
3. For signature blocks: configure `field_name`, `capture_current_date/time`, `text_lines` (with `{{variable}}` placeholders)
4. System creates `DocumentTemplate` + `DocumentTemplateVersion` with custom_document_template_config JSON
5. Optional: Configure border_style (TDR_CERTIFICATE, TDR_LETTER_OF_INTENT), signing_qr_position

### Template Type Comparison

| Feature | FORM_FIELDS_TEMPLATE | BLOCKS_TEMPLATE |
|---------|---------------------|-----------------|
| PDF creation | Upload existing PDF | Generate from blocks |
| Field data | Form field mapping (FIXED/LEAD_DETAILS) | Engine variables (placeholder resolution) |
| User signing | FlowwSign (PyHanko OTP) + DocuSign | Not supported for user-initiated |
| System signing | FlowwSign | FlowwSign (sign_document_by_system) |
| Draft state | Not used (always PUBLISHED) | Used for two-stage signing |
| QR code config | qr_positions, qr_size, pages | signing_qr_position (QR_WITH_SIGN or QR_AT_TOP) |
| Preview | Fill form fields with mock values | Full PDF generation with mock data |
| Border styles | Not supported | TDR_CERTIFICATE, TDR_LETTER_OF_INTENT |

## B: Document Generation — Form Fields Template

**Entry:** `GenerateDocumentInteractor.generate_document()` with `template_type == FORM_FIELDS_TEMPLATE`

```
1. Validate document template exists and is not deleted
2. Get latest DocumentTemplateVersion for the template
3. Check if Document already exists for this pipeline_item + template + doc_name
4. Resolve form field values:
   a. Use explicitly provided form_field_value_dtos
   b. For missing fields, check existing document's latest version for carry-over values
   c. For still-missing fields with LEAD_DETAILS source, fetch from CRM via GetDocumentFormatLeadFieldResponseMapInteractor
   d. For FIXED source, use the configured static value
5. Download template PDF from S3
6. Use PyPDF PdfReader/PdfWriter:
   a. Remove signature field annotations from pages
   b. Fill form fields with resolved values via update_page_form_field_values
   c. Update AcroForm /Fields array
7. If QR code configured: overlay QR code on specified pages/positions
8. Upload filled PDF to S3 (document path + published path if PUBLISHED state)
9. Create/update Document record (latest_version_file, latest_published_version_file)
10. Create DocumentVersion record (doc_file, state=PUBLISHED)
11. Return GenerateDocumentResultDTO
```

## C: Document Generation — Blocks Template

**Entry:** `GenerateDocumentInteractor._generate_document_for_blocks_template()` → `GeneratePDFForBlocksTemplateInteractor`

```
1. Gather required details via GetPDFBlocksGenerationRequiredDetailsInteractor:
   a. Compute engine variables (placeholders) for the pipeline item
   b. Fetch site inspection data (if task_id provided)
   c. Fetch category/checkpoint data (for CONDITIONS blocks)
   d. Fetch BPS verification remarks (for BPS_VERIFICATION_REMARKS blocks)
   e. Fetch OC site inspection reports (internal + final)
   f. Fetch payment logs and fee breakdowns
   g. Fetch pipeline item remarks
   h. Fetch TDR request data + TDR ledger table
   i. Fetch enforcement data, add-another-GoF data, shortfall field remarks
   j. Fetch tab details for APPLICATION_DETAILS_TAB blocks
   k. Compute fixed variables (site inspection datetime)
   l. Get footer line (APPLICATION_ID system field)

2. Convert block DTOs to PDF block DTOs via GetPDFBlocksForBlocksTemplateInteractor:
   - Dispatcher routes each block_type to its converter (dt_header_block, dt_paragraph_block, etc.)
   - Each converter takes (block_dto, required_details_dto) and returns List[PDF_BLOCK_UNION_TYPE]
   - SIGNATURE blocks convert to PDFDummySignBlockDTO (placeholder) or PDFSignBlockDTO (actual)

3. Generate PDF via GeneratePDFWithFlowablesInteractor:
   a. Create CustomizedDocTemplate (ReportLab SimpleDocTemplate with border/watermark support)
   b. Convert PDF block DTOs to ReportLab Flowables (header, paragraph, table, grid, list, etc.)
   c. For DUMMY_SIGN blocks: create DummySignBlock flowable that tracks its rendered position
   d. For signature layout: use QRWithSignatureStrategy or QRAtTopStrategy
   e. Build document (doc.build(flowables))
   f. Extract SignBlockLocationDTO from each DummySignBlock's recorded position
   g. Add disclaimer text

4. Upload PDF to S3, create/update Document + DocumentVersion records
5. Return (pdf_bytes, sign_block_location_dtos)
```

## D: Draft Letter Flow

**When:** `document_version_state=DRAFT` is passed to `GenerateDocumentInteractor.generate_document()`

```
1. Blocks template PDF generation proceeds normally
2. SIGNATURE block DTOs convert to PDFDummySignBlockDTO:
   - DtSignBlockInteractor.get_pdf_blocks() creates PDFDummySignBlockDTO with:
     - signature_field_name (from DtSignatureBlockDTO)
     - sign_block_width, sign_block_height (empty box dimensions)
     - block_type = PDFBlockType.DUMMY_SIGN

3. During PDF rendering (GeneratePDFWithFlowablesInteractor):
   - DummySignBlock flowable renders as an empty bordered rectangle
   - After build(), DummySignBlock.location stores (page_number, x_coordinate, y_coordinate)
   - _prepare_sign_block_locations_list() collects all SignBlockLocationDTOs

4. DocumentVersion saved with:
   - state = DRAFT
   - sign_block_location_dtos = list of SignBlockLocationDTO per signature field
   - No QR code added
   - No actual signatures placed

5. Document.latest_version_file updated but NOT latest_published_version_file
```

**Key data structure — SignBlockLocationDTO:**
```python
@dataclass
class SignBlockLocationDTO:
    page_number: int        # 1-indexed page number where sign block was rendered
    x_coordinate: float     # X position on the page (ReportLab coordinate system)
    y_coordinate: float     # Y position on the page
    signature_field_name: str  # Links back to the signature field config
```

## E: Signing Letter Flow (DRAFT → PUBLISHED)

**Entry:** `SignDocumentInteractor.sign_document_by_system()`

```
1. Receive document_version_id + list of SignatureFieldUserDTO (user_id, signature_field, signed_at)
2. Load DocumentVersion (must be DRAFT state), Document, DocumentTemplate
3. Validate signature field names against template version config
4. Get previous DRAFT version PDF bytes from S3

5. For each user in user_wise_signatures:
   a. Fetch user's signature image URL from IAM service (sales_user.signature_img_link)
   b. Compute engine variables for placeholder resolution
   c. For each signature field assigned to this user:
      i. Look up SignBlockLocationDTO from DRAFT version's sign_block_location_data
      ii. Look up BlocksTemplateSignatureFieldDTO for text_lines and description
      iii. Replace {{variable}} placeholders in text_lines with computed values
      iv. Prepare timestamp string if capture_current_date/time is enabled
      v. Call add_signature_to_pdf():
         - Opens PDF bytes, overlays signature image at (x, y) coordinate
         - Adds resolved text_lines below signature
         - Returns updated pdf_bytes

6. Add QR code to PDF (only if previous state was DRAFT and new state is PUBLISHED):
   - QR_WITH_SIGN: Position QR at middle signature's location (x=100, y=middle_sig.y_coordinate)
   - QR_AT_TOP: Position QR at top-right of page 1

7. Upload signed PDF to S3:
   - new_version_file_key (versioned path with timestamp)
   - document_file_key (latest document path)
   - document_pub_file_key (published path, if PUBLISHED state)

8. Create new DocumentVersion with:
   - state = PUBLISHED
   - digital_signing_data = FlowwSignatureFieldsDTO with completed fields
   - sign_block_location_dtos preserved from DRAFT version

9. Update Document.signature_fields_status with overall completed fields
10. If QR config exists on template: regenerate QR on document file
```

## F: Pipeline Item Document Generation

**Entry:** `GeneratePipelineItemDocumentInteractor.generate_pipeline_item_document()`

Higher-level orchestrator used by BPS automation workflows:

```
1. Validate pipeline item access (user must have WRITE access)
2. Get document template and determine doc_name from pipeline item data
3. Check if auto-signing is configured:
   - If signature_field_user_dtos provided, generate as DRAFT first then auto-sign
   - Otherwise generate as PUBLISHED directly

4. Call GenerateDocumentInteractor.generate_document() with appropriate state
5. If auto-signing:
   a. Get the DRAFT document version
   b. Call SignDocumentInteractor.sign_document_by_system() with signature_field_users
   c. This transitions DRAFT → PUBLISHED

6. Optionally send WhatsApp notification to pipeline item contacts
7. Return DocumentDTO
```

## G: DocuSign Signing Flow

**For FORM_FIELDS_TEMPLATE only:**

```
1. Create DocuSign envelope:
   - Get DocusignPluginConfig from storage
   - Authenticate via JWT grant (private key + OAuth config)
   - Create envelope with document PDF and signer recipients
   - Store envelope_id on DocumentVersion

2. Generate embed URL:
   - Create recipient view URL for in-app signing
   - Return URL to frontend for iframe embedding

3. DocuSign webhook callback:
   - Validate webhook signature (HMAC)
   - On envelope completion:
     a. Download signed document from DocuSign
     b. Update document version digital_signing_data
     c. Mark signing as completed
     d. Update Document.signature_fields_status
```

## H: PyHanko/FlowwSign Signing Flow

**For FORM_FIELDS_TEMPLATE user-initiated signing:**

```
1. User calls sign_document mutation with:
   - document_version_id, signature_fields (field names), otp

2. SignDocumentInteractor.sign_document():
   a. Validate document exists and is not deleted
   b. Validate this is the latest document version
   c. Validate user has WRITE access to pipeline item
   d. Validate signature fields exist in template version
   e. Validate fields are not already signed
   f. Verify OTP via IAM service (entity_type=DOCUMENT_VERSION, purpose=DOCUMENT_SIGNING)

3. Place signatures via PyHanko:
   a. Get user's signature image from IAM
   b. Get user profile (email, name) for signer DTO
   c. For each signature field: create PyhankoSignatureFieldDTO with position rectangle
   d. Call SignPdfThroughAPIInteractor.sign_pdf() — sends to PyHanko signing API
   e. Upload signed PDF to S3 (document path, version path, published path)

4. Create new DocumentVersion with updated digital_signing_data
5. Update Document signature_fields_status
```

## I: Watermarking & Rejection Flow

```
1. Document rejection:
   - Set document.is_rejected = True
   - add_rejection_watermark_to_document.py overlays "REJECTED" watermark on the PDF

2. Document watermark (template-level):
   - CustomizedDocTemplate applies watermark_image_url on every page during build
   - Uses WatermarkCanvas overlay with configurable opacity

3. Border styles:
   - CustomizedDocTemplate applies border_image_url on every page
   - Supported: TDR_CERTIFICATE, TDR_LETTER_OF_INTENT
```

## J: Letter Regeneration Flow

```
1. RegeneratePipelineItemDocumentInteractor:
   a. Find existing Document for pipeline_item + template + doc_name
   b. If auto-signing configured:
      - Delete existing DRAFT versions
      - Regenerate as DRAFT
      - Auto-sign to produce new PUBLISHED version
   c. If not auto-signing:
      - Regenerate as PUBLISHED directly

2. regenerate_published_letter_with_updated_timestamp (App Interface):
   - Delete existing DRAFT versions
   - Remove published details
   - Regenerate with fresh timestamp
   - Used by BPS automation when pipeline item data changes

3. regenerate_letter_with_timestamp (App Interface):
   - Similar but preserves certain existing version data
```

## K: GraphQL API Reference

### Queries (`sales_crm_graphql/dms/queries.py`)

| Query | Purpose |
|-------|---------|
| `getPipelineDocumentTemplatesForAdmin` | Admin view of templates for a pipeline |
| `getDocumentTemplatesByPipelineItemTemplateForAdmin` | Templates by pipeline item template (admin) |
| `getDocumentTemplatesByVersionForAdmin` | Templates with version details |
| `getPipelineDocumentTemplates` | Non-admin template listing |
| `getDocumentTemplatesForPipelineItemTemplates` | Templates for pipeline item template |
| `getPipelineItemDocumentTemplates` | Templates for specific pipeline item |
| `getDocumentTemplates` | General template listing |
| `getDocumentsForDocumentTemplates` | Documents grouped by templates |
| `getPipelineItemDocumentsForDocumentTemplate` | Documents for a pipeline item + template |
| `getDocumentHistory` | Version history for a document |
| `getPreSignedGetUrlForDocumentTemplate` | Download URL for template PDF |
| `getPreSignedGetUrlForDocument` | Download URL for document PDF |
| `getPreSignedGetUrlForDocumentVersion` | Download URL for specific version |
| `getPreSignedPutUrlForDocumentTemplate` | Upload URL for template PDF |
| `getPreSignedPostUrlForDocumentTemplate` | Upload URL (POST) for template PDF |
| `isDocumentTemplateNameExists` | Name uniqueness check |
| `getPreviewForDocumentTemplate` | Preview PDF for template |
| `getDocumentTemplatePreviewWithMockData` | Preview with mock data |
| `generateDocusignEmbedUrlForPipelineItemDocument` | DocuSign signing URL |

### Mutations (`sales_crm_graphql/dms/mutations/`)

| Mutation | File | Purpose |
|----------|------|---------|
| `createDocumentTemplate` | `create_document_template.py` | Create new template |
| `updateDocumentTemplateName` | `update_document_template_name.py` | Rename template |
| `updateDocumentTemplateDescription` | `update_document_template_description.py` | Update description |
| `deleteDocumentTemplate` | `delete_document_template.py` | Soft delete template |
| `updateDocumentTemplateVersionConfig` | `update_document_template_version_config.py` | Update form fields mapping, signatures, QR |
| `updateCustomDocumentTemplate` | `update_custom_document_template.py` | Update blocks config |
| `generatePipelineItemDocument` | `generate_pipeline_item_document.py` | Generate document for pipeline item |
| `regeneratePipelineItemDocument` | `regenerate_pipeline_item_document.py` | Regenerate existing document |
| `signDocument` | `sign_document.py` | FlowwSign OTP signing |
| `deleteDocument` | `delete_document.py` | Soft delete document |
| `createDocumentLog` | `create_document_log.py` | Log preview/download events |

### DataLoaders (`sales_crm_graphql/dms/dataloaders/`)

| DataLoader | Purpose |
|------------|---------|
| `custom_document_template_config` | Batch load blocks config for versions |
| `document_latest_version_id` | Batch load latest version IDs for documents |
| `document_latest_versions` | Batch load latest version DTOs |
| `document_pending_signs_info` | Batch load pending signing info |
| `document_template_overview_details` | Batch load template overviews |
| `document_variables` | Batch load document variables |
| `pending_signs` | Batch load pending sign status |
