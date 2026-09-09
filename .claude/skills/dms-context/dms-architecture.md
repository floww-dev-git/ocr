# DMS Architecture Details

Deep dive into models, DTOs, storage interfaces, exceptions, adapters, and app interfaces for the DMS domain.

## Models & Relationships

### DocumentTemplate
```
plugins/models/dms.py :: DocumentTemplate(CloneableModel, AbstractDateTimeCacheModel)
```
| Field | Type | Notes |
|-------|------|-------|
| `id` | CharField(PK, UUID) | Auto-generated UUID |
| `name` | CharField(255) | Template display name |
| `description` | TextField(nullable) | Optional description |
| `pipeline_item_template_id` | CharField(255) | Links to CRM pipeline item template |
| `pipeline_id` | CharField(255, nullable) | Optional pipeline association |
| `created_by` | CharField(255) | Creator user ID |
| `template_type` | CharField(255) | `DocumentTemplateType` enum value |
| `is_deleted` | BooleanField(False) | Soft delete flag |
| `variable_ids` | TextField(default="[]") | JSON array of engine variable IDs |
| `border_style` | CharField(250, nullable) | `DocumentBorderStyle` enum value |
| `signing_qr_position` | CharField(20, default="QR_WITH_SIGN") | `SigningQRPosition` enum value |

Supports pipeline cloning via `CloneableModel` (EntityType.DOCUMENT_TEMPLATE).

### DocumentTemplateVersion
```
plugins/models/dms.py :: DocumentTemplateVersion(CloneableModel, AbstractDateTimeCacheModel)
```
| Field | Type | Notes |
|-------|------|-------|
| `id` | CharField(PK, UUID) | Auto-generated UUID |
| `document_template` | FK(DocumentTemplate) | Parent template |
| `published_at` | DateTimeField(auto_now_add) | When this version was published |
| `template_file` | TextField(default="{}") | JSON — uploaded PDF file info (for FORM_FIELDS_TEMPLATE) |
| `custom_document_template_config` | TextField(default="{}") | JSON — blocks configuration (for BLOCKS_TEMPLATE) |
| `created_by` | CharField(255) | Creator user ID |
| `form_fields_mapping` | TextField(nullable) | JSON — form field to CRM field mappings |
| `signature_fields` | TextField(nullable) | JSON — signature field positions and block signature configs |
| `qr_code_config` | TextField(default="{}") | JSON — QR code positions, size, pages |

**JSON Structures:**

`custom_document_template_config`:
```json
{
  "blocks": [
    {
      "block_id": "uuid",
      "order": 1,
      "block_type": "HEADER|PARAGRAPH|TABLE|...",
      // block-type-specific fields
    }
  ]
}
```

`signature_fields`:
```json
{
  "signature_fields": [
    { "field_name": "str", "identification_ids": ["id"], "x_pixel": 182, "y_pixel": 318, "page_number": 1 }
  ],
  "blocks_template_signature_fields": [
    { "field_name": "str", "capture_current_date": true, "capture_current_time": true, "variable_ids": ["id"], "description": ["str"] }
  ]
}
```

`qr_code_config`:
```json
{
  "qr_positions": ["TOP_LEFT", "TOP_RIGHT", "BOTTOM_LEFT", "BOTTOM_RIGHT"],
  "qr_size": "SMALL|MEDIUM|LARGE",
  "pages": [1, 2]
}
```

### Document
```
plugins/models/dms.py :: Document(AbstractDateTimeCacheModel)
```
| Field | Type | Notes |
|-------|------|-------|
| `id` | CharField(PK, UUID) | Auto-generated UUID |
| `name` | TextField | Document name (usually same as doc_name param) |
| `pipeline_item_type` | CharField(255) | `PipelineItemType` enum value |
| `pipeline_item_id` | CharField(255) | The specific pipeline item this doc belongs to |
| `document_template` | FK(DocumentTemplate) | Template used for generation |
| `latest_version_file` | TextField(default="{}") | JSON FileUploaderResponseDTO — latest version S3 URL |
| `latest_published_version_file` | TextField(default="{}") | JSON FileUploaderResponseDTO — latest published version S3 URL |
| `last_published_at` | DateTimeField(nullable) | When last published |
| `signature_fields_status` | TextField(default="{}") | JSON — DocuSign/FlowwSign signing status |
| `is_deleted` | BooleanField(False) | Soft delete flag |
| `is_rejected` | BooleanField(False) | Rejection flag (triggers watermark) |

**Index:** `(pipeline_item_id, is_deleted)` for fast document lookups.

`signature_fields_status`:
```json
{
  "docusign": { "envelope_id": "str", "recipient_id": "str", "signature_fields": ["field1"] },
  "floww_sign": { "signature_completed_fields": ["field1", "field2"] }
}
```

### DocumentVersion
```
plugins/models/dms.py :: DocumentVersion(AbstractDateTimeCacheModel)
```
| Field | Type | Notes |
|-------|------|-------|
| `id` | CharField(PK, UUID) | Auto-generated UUID |
| `document` | FK(Document) | Parent document |
| `dt_version` | FK(DocumentTemplateVersion) | Template version used |
| `generated_at` | DateTimeField(auto_now_add) | Generation timestamp |
| `generated_by` | CharField(255, nullable) | User ID or null (system-generated) |
| `doc_file` | TextField(default="{}") | JSON FileUploaderResponseDTO — version PDF file |
| `envelope_id` | CharField(255, nullable) | DocuSign envelope ID |
| `digital_signing_data` | TextField(default="{}") | JSON — signing completion data |
| `state` | CharField(250, default="PUBLISHED") | `DocumentVersionState` — DRAFT or PUBLISHED |
| `sign_block_location_data` | TextField(default="{}") | JSON — SignBlockLocationDTO coordinates for DRAFT versions |

`sign_block_location_data`:
```json
{
  "page_number": 1,
  "x_coordinate": 350.5,
  "y_coordinate": 120.3
}
```

`digital_signing_data`:
```json
{
  "docusign": { "signature_fields": ["f1"], "envelop_doc_id": "id", "signing_status": "completed" },
  "floww_sign": { "signature_completed_fields": ["f1", "f2"] }
}
```

### DocusignPluginConfig
```
plugins/models/dms.py :: DocusignPluginConfig(AbstractDateTimeCacheModel)
```
| Field | Type | Notes |
|-------|------|-------|
| `id` | CharField(PK, UUID) | Auto-generated UUID |
| `account_config` | TextField(default="{}") | JSON — full DocuSign API config |
| `private_key` | TextField | DocuSign RSA private key |

`account_config`:
```json
{
  "account_id": "str", "account_base_uri": "str", "client_id": "str",
  "docusign_user_id": "str", "secret_key": "str",
  "oauth_config": { "oauth_host_name": "str", "oauth_origin": "str" },
  "frontend_url": "str", "return_url": "str"
}
```

## DTOs

### Block DTOs (`plugins/interactors/dms/dtos.py`)

All block DTOs inherit from `BaseDocumentTemplateBlockDTO(block_id, order, block_type)`.

| Block DTO | Key Fields |
|-----------|------------|
| `DtHeaderBlockDTO` | header_logo_url, title, subtitle, description, right_corner_text |
| `DtParagraphBlockDTO` | heading, text_lines, style (ParagraphStyles), inline_heading_and_paragraph |
| `DtGridBlockDTO` | heading, grid_unit_dtos (List[DtGridUnitDTO]) |
| `DtTableBlockDTO` | title, field_ids, column_width_percentages |
| `FooterBlockDTO` | signature_field_name, right_corner_text |
| `DtSignatureBlockDTO` | signature_field_name, text_lines, capture_current_date/time, description, sign_block_width/height |
| `DtSiteInspectionBlockDTO` | table_heading, enable_site_inspection_table_grouping |
| `DtEnforcementBlockDTO` | heading, tab_id, section_id, geo_location_field_ids, photograph_field_ids |
| `DtOCSiteInspectionInternalReportBlockDTO` | heading, task_template_id |
| `DtOCSiteInspectionFinalReportBlockDTO` | heading, task_template_id, table_dtos |
| `DtPaymentBlockDTO` | title, column_width_percentages, enable_fee_header_grouping, show_amounts, fee_header_amount_type |
| `DtPaymentReceiptBlockDTO` | title |
| `DtConditionsBlockDTO` | title, body, skip_block_in_empty_conditions, category_ids |
| `DtBpsVerificationRemarksBlockDTO` | table_heading, task_template_id, assignee_field_ids, recommendation_enums, allowed_remarks_sections |
| `DtDynamicTableBlockDTO` | heading, row_dtos (List[DtDynamicTableRowDTO]), enable_table_borders |
| `DtRepeatedTableBlockDTO` | heading, data_source (RepeatedTableDataSourceType), row_dtos |
| `DtListBlockDTO` | heading, description, text_lines, presentation_type |
| `DtRemarksBlockDTO` | show_sign, sign_content |
| `DtTDRRequestsBlockDTO` | heading, tdr_request_statuses |
| `DtTDRLedgerBlockDTO` | heading, tdr_account_no_field_id, tdr_authority_field_id |
| `DtAddAnotherGoFTableBlockDTO` | heading, enable_table_borders, add_another_gof_field_dtos |
| `DtShortFallFieldRemarksBlockDTO` | title |
| `DtApplicationDetailsTabBlockDTO` | title, tab_id |

### Template DTOs

| DTO | Purpose |
|-----|---------|
| `CreateDocumentTemplateParamsDTO` | Input for template creation — id, pipeline_id, name, type, file, border_style, signing_qr_position |
| `DocumentTemplateDTO` | Core template data — id, name, type, pipeline associations, timestamps, border_style |
| `DocumentTemplateVersionDTO` | Full version data — blocks, form fields, signatures, QR config, template file |
| `AdminDocumentTemplateDTO` | Admin view — combines template + version data with form fields and signatures |
| `CustomDocumentTemplateConfigDTO` | dt_version_id + list of block DTOs |
| `UpdateCustomDocumentTemplateConfigDTO` | Block list for version update |

### Document DTOs

| DTO | Purpose |
|-----|---------|
| `GenerateDocumentParamsDTO` | Input for document generation — template ID, doc_name, pipeline_item, form field values, version state |
| `GenerateDocumentResultDTO` | Output — document_id, version_id, file DTOs |
| `DocumentDTO` | Full document data — files, signing status, timestamps, deleted/rejected flags |
| `DocumentVersionDTO` | Version data — file, signing data, state, sign_block_location_dtos |
| `DocumentVersionOverviewDetailsDTO` | Lightweight version info for listings |

### Signing DTOs

| DTO | Purpose |
|-----|---------|
| `SignDocumentParamsDTO` | document_version_id, signature_fields, otp |
| `SignatureFieldDTO` | field_name, identification_ids, page_number, x/y_pixels, dimensions |
| `SignatureFieldDimensionsDTO` | lower_left_x/y_position, width, height |
| `BlocksTemplateSignatureFieldDTO` | field_name, capture_current_date/time, text_lines, description |
| `SignatureFieldUserDTO` | user_id, signature_field, signed_at |
| `SignatureFieldAssigneeMapping` | signature_field, assignee_field_id, signed_at |
| `DocusignSignatureFieldsStatusDTO` | envelop_id, recipient_id, sign_completed_fields |
| `DocusignSignatureFieldsDTO` | signature_fields, envelope_doc_id, signing_status |
| `FlowwSignatureFieldsDTO` | signature_completed_fields |

### QR/Config DTOs

| DTO | Purpose |
|-----|---------|
| `DocumentTemplateQrCodeConfigDTO` | qr_positions, qr_size, pages |
| `DocusignPluginConfigDTO` | Full DocuSign config — account_id, base_uri, client_id, oauth, private_key |
| `DocusignOauthConfigDTO` | oauth_host_name, oauth_origin |

### Form Field DTOs

| DTO | Purpose |
|-----|---------|
| `DocumentTemplateFormFieldDTO` | name, field_type, crm_field_mapping |
| `DocumentTemplateFormFieldMappingDTO` | source (FIXED/LEAD_DETAILS), value |
| `UpdateDocumentTemplateFormFieldParamsDTO` | name, crm_field_mapping |
| `DocumentFormFieldValueDTO` | name, value — runtime form field value |
| `DocumentTemplateFormFieldsDTO` | dt_version_id, form_fields, signature_fields |

### Utility DTOs

| DTO | Purpose |
|-----|---------|
| `DtVersionIdDTO` | dt_version_id + document_template_id mapping |
| `DtVersionPublishedAtDTO` | dt_version_id + published_at timestamp |
| `DtVersionTemplateFileDTO` | File info for template version |
| `DocumentTemplatePipelineItemTemplateIdDTO` | pipeline_item_template_id + variable_ids |
| `DocumentIdTemplateIdDTO` | document_id + template_id mapping |
| `GetPipelineDocumentTemplatesParamsDTO` | pipeline_id, search_query, pagination |
| `GetPipelineItemDocumentTemplatesParamsDTO` | pipeline_item_id, search_query, pagination |
| `GetPipelineItemDocumentsParamsDTO` | pipeline_item_id, document_template_ids, pagination |
| `DocumentCompletedSignFieldsAndSizeInBytesDTO` | document_id, completed_sign_fields, size |
| `CreateDocumentLogParamsDTO` | document_id, portal_type, log_type |
| `DocumentLogDTO` | Log entry with date/time, user_id, portal_type, log_type |

### PDF Block DTOs (`plugins/interactors/dms/pdf_blocks/dtos.py`)

All inherit from `BasePDFBlockDTO(block_id, block_type)`.

| PDF DTO | Key Fields | Used For |
|---------|------------|----------|
| `PDFHeaderBlockDTO` | logo_url, header_text, sub_header_text, sub_sub_header_text, right_block_text | HEADER block |
| `PDFParagraphBlockDTO` | heading, text_lines, style, inline_heading_and_paragraph | PARAGRAPH block |
| `PDFDualHeaderParagraphBlockDTO` | left_heading, right_heading, body, body_content_type | Dual-column paragraphs |
| `PDFGridBlockDTO` | heading, grid_unit_dtos | GRID block |
| `PDFTableBlockDTO` | heading, column_widths, table_data | TABLE, CONDITIONS, PAYMENT, etc. |
| `PDFListBlockDTO` | heading, description, text_lines, presentation_type | LIST block |
| `PDFDynamicTableBlockDTO` | heading, row_dtos, enable_table_borders | DYNAMIC_TABLE, REPEATED_TABLE |
| `PDFImageBlockDTO` | heading, image_url_dtos | IMAGE (enforcement photos, etc.) |
| `PDFDummySignBlockDTO` | signature_field_name, sign_block_width, sign_block_height | DRAFT signature placeholder |
| `PDFSignBlockDTO` | sign_img_link, text_lines | PUBLISHED actual signature |
| `SignBlockLocationDTO` | page_number, x_coordinate, y_coordinate, signature_field_name | Signature position tracking |

### Required Details DTO (`plugins/interactors/dms/core_blocks_converter/dtos.py`)

`PDFBlocksGenerationRequiredDetailsDTO` — Aggregated data for all block converters:

| Field | Data Source |
|-------|------------|
| `pipeline_item_id` | Input parameter |
| `placeholder_data` | Engine variables (computed via EngineVariables adapter) |
| `placeholder_display_name_map` | Engine variables display names |
| `payment_log_dtos` | FeeEngine adapter |
| `fee_breakdown_dto` | FeeEngine adapter |
| `remark_dtos` | SalesCRM service adapter |
| `tdr_request_dtos` | TDR service adapter |
| `category_dtos` | BPS service adapter |
| `pipeline_item_checkpoint_dtos` | BPS service adapter |
| `site_inspection_dto` | BPS service adapter |
| `enforcement_dto` | BPS/SalesCRM service adapter |
| `add_another_gof_table_dtos` | BPS service adapter |
| `oc_site_inspection_internal_report_dtos` | BPS service adapter |
| `oc_site_inspection_final_report_dtos` | BPS service adapter |
| `bps_verif_task_template_dtos` | BPS service adapter |
| `computed_engine_variables_dto` | Engine variables adapter |
| `internal_obj_response_map` | Field service adapter |
| `pdf_footer_line` | SalesCRM (APPLICATION_ID system field) |
| `shortfall_field_remark_dtos` | BPS service adapter |
| `tdr_ledger_table_dto` | TDR service adapter |
| `tab_details` | BPS service adapter |

## Storage Interface

### `DmsStorageInterface` (`plugins/interactors/storage_interfaces/dms_storage_interface.py`)

55+ abstract methods organized by domain:

**Template Operations:**
- `create_document_template`, `get_document_template_dtos`, `update_document_template_name`, `update_document_template_description`, `delete_document_template`
- `is_document_template_name_exists`, `get_valid_document_template_ids`
- `get_document_template_pipeline_item_template_id_bulk`, `set_document_template_variable_ids`
- `get_document_templates_with_pagination`, `get_pipeline_item_template_document_templates`
- `get_document_templates_for_pipeline_item_template_id`

**Version Operations:**
- `create_document_template_version`, `get_dt_version_dtos`, `get_dt_version_form_fields`
- `get_document_template_id_for_version_id_bulk`, `get_document_template_version_files_bulk`
- `get_dt_version_published_dtos_for_doc_templates`, `get_signature_fields_in_dt_versions`
- `update_fields_mapping_in_dt_version`, `update_signature_fields_mapping_in_dt_version`
- `update_document_template_last_updated_at`
- `get_latest_document_template_version`, `get_latest_document_template_version_bulk`
- `get_custom_document_template_configs`, `update_custom_document_template_config`

**Document Operations:**
- `update_or_create_pipeline_item_document`, `get_document`, `get_document_bulk`
- `get_pipeline_item_document_for_doc_name`, `get_pipeline_item_documents`
- `get_all_pipeline_item_documents`, `get_pipeline_item_document_template_ids`
- `delete_document`, `restore_document`, `get_valid_document_ids`
- `get_pipeline_item_documents_with_pagination`, `get_pipeline_item_documents_with_pagination_v2`
- `get_documents_for_doc_templates`
- `get_document_template_ids_for_document_ids`
- `delete_pipeline_item_documents_permanently`, `update_document_rejection_status`
- `get_document_latest_datetime`, `update_document_last_updation_datetime`
- `remove_published_details_for_documents`, `get_application_published_documents`

**Version Operations (Document):**
- `create_document_version_dto`, `create_document_version_bulk`
- `get_document_version`, `get_document_versions`
- `get_document_history_with_pagination`, `get_document_version_overview_details_to_document_ids`
- `get_latest_document_version_id_for_document_id`, `get_latest_document_version_id_for_document_id_and_state`
- `get_latest_draft_document_version_id_for_document_id`
- `get_latest_pipeline_item_document_for_dt`, `get_document_versions_for_document_ids`
- `update_document_versions_generated_at`, `delete_document_versions_on_version_state`

**Signing Operations:**
- `update_docusign_signature_fields_in_document`
- `get_satisfied_document_versions_for_envelope_id`
- `update_document_version_envelope_id_and_signing_fields`
- `update_document_version_digital_signing_as_completed`
- `update_documents_completed_sign_fields`
- `update_flow_sign_completed_fields_and_object_size_in_bytes`
- `update_document_last_published_at`
- `get_docusign_plugin_config`

**Pagination Operations:**
- `get_pipeline_item_template_admin_doc_template_ids_with_pagination`
- `get_pipeline_doc_template_ids_with_pagination`

## Exceptions (`plugins/exceptions/dms_exceptions.py`)

### Template Exceptions
| Exception | Context |
|-----------|---------|
| `InvalidDocumentTemplateId` | Template ID not found |
| `DeletedDocumentTemplateId` | Template is soft-deleted |
| `DocumentTemplateNameAlreadyExists` | Duplicate name in pipeline item template |
| `DocumentTemplateHasEmptyFormFields` | Uploaded PDF has no fillable fields |
| `NotPdfFileUrl` | Uploaded file is not a PDF |
| `DocumentTemplateFileTooLarge` | File exceeds size limit |
| `InvalidDocumentTemplatePages` | Invalid page numbers in QR config |
| `NotSupportedDocumentTemplateType` | Operation not supported for this template type |

### Form Field Exceptions
| Exception | Context |
|-----------|---------|
| `InvalidFormFields` | Form field names not found in PDF |
| `EmptyMappingValueForFormFieldsMapping` | Mapping value is empty |
| `DuplicateFormFieldsMapping` | Duplicate field mappings |
| `DMSFieldsBaseException` | Base for field validation errors |
| `FieldTypesNotSupportedInDocumentTemplateMapping` | Unsupported field types in mapping |
| `FieldsCrmTemplateNotSupportedInDocumentTemplateMapping` | CRM template fields not supported |

### Document Exceptions
| Exception | Context |
|-----------|---------|
| `InvalidDocumentId` | Document ID not found |
| `DeletedDocumentId` | Document is soft-deleted |
| `InvalidDocumentVersionId` | Version ID not found |
| `NotLatestDocumentVersion` | Attempting operation on non-latest version |
| `LetterNotFoundForPipelineItem` | No letter found for pipeline item + template + doc name |
| `InvalidDtVersionId` | Template version not found |
| `InvalidDtVersionIds` | Multiple template versions not found |
| `DtVersionIdsAccountAccessDenied` | No access to template versions |

### Signing Exceptions
| Exception | Context |
|-----------|---------|
| `EmptySignatureFields` | No signature fields provided |
| `InvalidDocumentSignatureFields` | Signature field names don't match template |
| `AtLeastOneSignatureFieldIsRequired` | System sign requires at least one field |
| `SigningAlreadyCompletedForFields` | Fields already signed |
| `SigningAlreadyCompleted` | All signing is complete (no sign_block_location_dtos) |
| `YouDontHaveAnyPendingSigns` | User has no pending signatures |
| `CustomDocumenttemplateNotSupported` | User FlowwSign not supported for BLOCKS_TEMPLATE |
| `SignDocumentAPIFailed` | PyHanko API signing failed |
| `InvalidTDRRequestStatuses` | Invalid TDR request statuses in block config |

### DocuSign Exceptions
| Exception | Context |
|-----------|---------|
| `DocusignPluginNotConfigured` | No DocuSign config exists |
| `InvalidDocusignPrivateKey` | Invalid RSA private key |
| `InvalidDocusignGrantSignatureKey` | OAuth grant failed |
| `DocusignEnvelopeAPIFailed` | Envelope creation API failed |
| `DocusignEmbedUrlAPIFailed` | Embed URL generation failed |
| `InvalidDocusignWebhookSignature` | Webhook signature validation failed |

## Adapters

DMS interactors access external services through `plugins/adapters/service_adapter.py`:

| Adapter Property | Service | Used For |
|-----------------|---------|----------|
| `sales_crm_service` | SalesCRMService | Pipeline items, field responses, remarks, user properties |
| `bps_service` | BpsService | Site inspections, conditions, enforcement, OC reports, verification remarks, shortfall fields |
| `tdr_service` | TDRService | TDR requests for PDF, TDR ledger table |
| `fee_engine` | FeeEngine | Payment logs, fee breakdowns |
| `engine_variables` | EngineVariables | Compute engine variables for placeholder resolution |
| `field_service` | FieldService | Field metadata, field filtering |
| `iam_service` | (via IamMixin) | User signatures, OTP verification, permission checks |

## App Interface

DMS methods exposed through `plugins/app_interfaces/service_interface.py` for inter-app consumption:

| Method | Purpose |
|--------|---------|
| `get_document_template_overview_details` | Template overview for other apps |
| `get_document_templates` | List templates for pipeline item template |
| `generate_document` | Generate a document (used by BPS automation) |
| `regenerate_letter_with_timestamp` | Regenerate with updated timestamp |
| `convert_document_format_responses` | Format field responses for document generation |
| `validate_for_latest_document_version_access_to_user` | Check user access to version |
| `get_pipeline_item_latest_document_version_id` | Get latest version for pipeline item + template |
| `sign_document_by_system` | System auto-sign (used by BPS workflows) |
| `generate_pdf_for_document_template` | Generate preview PDF |
| `get_pipeline_item_template_document_template_ids` | Template IDs for pipeline item template |
| `get_pipeline_item_latest_published_document` | Latest published document |
| `get_pipeline_item_latest_published_documents` | Latest published documents bulk |
| `regenerate_published_letter_with_updated_timestamp` | Regenerate published letter |
| `filter_document_template_ids` | Filter valid template IDs |
| `get_document_template_json` | Template JSON for export |
| `get_document_template_blocks_json` | Blocks JSON for export |
