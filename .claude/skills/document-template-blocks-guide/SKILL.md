---
name: document-template-blocks-guide
description: Guide for adding or modifying block types in the document template (Letters) system. Use when implementing new PDF block types, modifying existing blocks, or understanding the blocks template pipeline. Covers enums, DTOs, CSV parsing, storage serialization, required details, converters, and dispatcher registration.
user-invocable: false
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

# Document Template Blocks Guide

Guides you through the complete 7-step pipeline for adding or modifying block types in the Letters/document template system. Each block type flows through enums, DTOs, CSV parsing, storage serialization, data gathering, PDF conversion, and dispatcher registration.

## Pipeline Overview

```
Step 1: Enums            -> Define block type identifiers
Step 2: DTOs             -> Define data structure for the block
Step 3: CSV Parsing      -> Parse config CSV rows into block DTOs
Step 4: Storage Layer    -> Serialize (DTO -> JSON) and Deserialize (JSON -> DTO)
Step 5: Required Details -> Gather external data the block needs at render time
Step 6: Converter        -> Convert block DTO -> PDF block DTO(s)
Step 7: Dispatcher       -> Register converter in the block-type routing map
```

## User Confirmation Gates

Before proceeding with implementation, confirm these with the user:

- **Gate A** (before Step 1): Confirm `block_type` enum name and CSV display name
- **Gate B** (before Step 3): Confirm CSV column names, data types, and formats
- **Gate C** (before Step 5): Confirm data source, entity scope, empty-data handling, filtering
- **Gate D** (before Step 6): Confirm PDF presentation type (table/paragraph/list/grid/image/combo)

## File Touchpoints (Complete)

| # | Layer | File | Action |
|---|-------|------|--------|
| 1 | Enum (CSV) | `sales_crm_core/populate/blocks_templates/populate_document_template_blocks.py` | Add `DataLoadingBlockType` member |
| 2 | Enum (Runtime) | `plugins/constants/dms_enums.py` | Add `DocumentTemplateBlockType` member |
| 3 | Enum (PDF) | `plugins/constants/dms_enums.py` | Add `PDFBlockType` member (only if needed) |
| 4 | DTO (Block) | `plugins/interactors/dms/dtos.py` | Add `DtXxxBlockDTO` + add to union |
| 5 | DTO (PDF) | `plugins/interactors/dms/pdf_blocks/dtos.py` | Add `PDFXxxBlockDTO` + add to union (only if needed) |
| 6 | CSV Parsing | `sales_crm_core/populate/blocks_templates/populate_document_template_blocks.py` | Add parsing logic |
| 7 | Storage (Deserialize) | `plugins/storages/dms_storage.py` -> `_get_custom_document_template_block_dtos()` | Add `elif` for JSON -> DTO |
| 8 | Storage (Serialize) | `plugins/storages/dms_storage.py` -> `_get_blocks_dicts_from_block_dtos()` | Add `elif` for DTO -> JSON |
| 9 | Required Details DTO | `plugins/interactors/dms/core_blocks_converter/dtos.py` | Add field to `PDFBlocksGenerationRequiredDetailsDTO` |
| 10 | Required Details | `plugins/interactors/dms/core_blocks_converter/get_pdf_blocks_generation_required_details.py` | Add data fetching |
| 11 | Converter | `plugins/interactors/dms/core_blocks_converter/dt_xxx_block.py` | Create converter |
| 12 | Dispatcher | `plugins/interactors/dms/core_blocks_converter/get_pdf_blocks_for_blocks_template.py` | Register in map |

For detailed reference on existing block types, enum values, DTO fields, and code patterns, see `block-types-reference.md` in this skill directory.

---

## Step 1 - Define Enums

### Files to modify
- `sales_crm_core/populate/blocks_templates/populate_document_template_blocks.py` -> `DataLoadingBlockType`
- `plugins/constants/dms_enums.py` -> `DocumentTemplateBlockType`
- `plugins/constants/dms_enums.py` -> `PDFBlockType` (only if no existing PDF type fits)

### What to do
1. Add a new member to `DataLoadingBlockType` with the CSV-facing display name (e.g. `YOUR_BLOCK = "Your Block"`)
2. Add a matching member to `DocumentTemplateBlockType` with the runtime string value (e.g. `YOUR_BLOCK = "YOUR_BLOCK"`)
3. Only add to `PDFBlockType` if no existing PDF rendering type can be reused

### Reusable PDF block types
| PDF Type | Reuse for |
|----------|-----------|
| `PDFParagraphBlockDTO` | Any text-with-heading block |
| `PDFDynamicTableBlockDTO` | Any tabular data |
| `PDFListBlockDTO` | Bullet/numbered lists |
| `PDFGridBlockDTO` | Multi-column side-by-side layouts |
| `PDFHeaderBlockDTO` | Document headers |
| `PDFImageBlockDTO` | Image galleries with captions |
| `PDFDualHeaderParagraphBlockDTO` | Left/right header with body text |
| `PDFTableBlockDTO` | Simple S.No / field-name / value tables |
| `PDFDummySignBlockDTO` | Signature placeholders |
| `PDFSignBlockDTO` | Actual signatures with image |

---

## Step 2 - Define DTOs

### Files to modify
- `plugins/interactors/dms/dtos.py` -> New `DtXxxBlockDTO` + add to `CUSTOM_DOCUMENT_BLOCKS_UNION_TYPE`
- `plugins/interactors/dms/pdf_blocks/dtos.py` -> New `PDFXxxBlockDTO` + add to `PDF_BLOCK_UNION_TYPE` (only if new PDF type needed)

### What to do
1. Create `DtXxxBlockDTO` extending `BaseDocumentTemplateBlockDTO`
2. Add all block-specific fields (no optional attributes per project convention)
3. Add the new DTO to `CUSTOM_DOCUMENT_BLOCKS_UNION_TYPE`
4. If new PDF block type needed, create `PDFXxxBlockDTO` extending `BasePDFBlockDTO` and add to `PDF_BLOCK_UNION_TYPE`

### Pattern
```python
@dataclass
class DtXxxBlockDTO(BaseDocumentTemplateBlockDTO):
    your_field: str
    another_field: List[str]
    # No optional attributes - all fields required per convention
```

---

## Step 3 - CSV Parsing (Data Loading)

### File to modify
- `sales_crm_core/populate/blocks_templates/populate_document_template_blocks.py`

### What to do
1. Add CSV column key(s) to `DataKeys` enum if new columns needed
2. Add parsing logic in `_populate_blocks()` / `_prepare_block_dto()` to convert CSV rows -> `DtXxxBlockDTO`
3. Handle variable placeholder conversion: CSV uses `{{variable_id}}`, storage uses `<<variable_id>>`
4. Add validation rules (field reference checks, required fields)

### CSV parsing patterns
- Single row -> single block: direct DTO construction
- Multiple rows same `ROW_NUMBER` with positions (Left/Center/Right) -> `DtGridBlockDTO`
- `TABLE_HEADER` + `TABLE_CELL` accumulated until `TABLE_BREAK` -> `DtDynamicTableBlockDTO`
- Signature Header + Signature Footer merged by `SIGNATURE_FIELD_NAME` -> `DtSignatureBlockDTO`

---

## Step 4 - Storage Layer (Serialize / Deserialize)

### File to modify
- `plugins/storages/dms_storage.py`

### 4a. Deserialization (JSON -> DTO) in `_get_custom_document_template_block_dtos()`
Add an `elif` branch matching `DocumentTemplateBlockType.YOUR_TYPE.value`:
```python
elif block_type == DocumentTemplateBlockType.YOUR_TYPE.value:
    block_config = DtYourTypeBlockDTO(
        block_id=block_id,
        block_type=block_type,
        order=order,
        your_field=block_data.get("your_field"),
    )
```

### 4b. Serialization (DTO -> JSON) in `_get_blocks_dicts_from_block_dtos()`
Add an `elif` branch:
```python
elif dto.block_type == DocumentTemplateBlockType.YOUR_TYPE.value:
    your_type_block = {
        "your_field": dto.your_field,
    }
    block_dict.update(your_type_block)
```

### Key rules
- Always handle nested structures (rows/cells/columns) by constructing sub-DTOs during deserialization
- Always flatten nested DTOs back to plain dicts during serialization
- Missing block type raises `NotImplementedError` during serialization (strict enforcement)
- Use `.get()` for all JSON field access during deserialization

---

## Step 5 - Required Details (Data Sourcing)

### Files to modify
- `plugins/interactors/dms/core_blocks_converter/dtos.py` -> Add field to `PDFBlocksGenerationRequiredDetailsDTO`
- `plugins/interactors/dms/core_blocks_converter/get_pdf_blocks_generation_required_details.py` -> Add data fetching

### Discovery questions (ask user before implementing)
1. **Data source**: Existing placeholders? External service (BPS, TDR, Fee Engine)? New storage query? Static config?
2. **Entity scope**: Pipeline Item level? Building/Plot/Floor level (repeated)? Task level?
3. **Empty data handling**: Skip block? Show placeholder? Show "No data" row?
4. **Filtering**: By status? By category? By task template?

### Pattern
```python
# In dtos.py - add field to PDFBlocksGenerationRequiredDetailsDTO
your_data_dtos: List[YourDataDTO]

# In get_pdf_blocks_generation_required_details.py
def _get_your_data(self, block_dtos, pipeline_item_id):
    has_your_block = any(
        dto.block_type == DocumentTemplateBlockType.YOUR_TYPE.value
        for dto in block_dtos
    )
    if not has_your_block:
        return []
    return self.service_adapter.your_service.get_data(pipeline_item_id)
```

---

## Step 6 - Converter (Block DTO -> PDF Block DTOs)

### File to create
- `plugins/interactors/dms/core_blocks_converter/dt_xxx_block.py`

### Discovery questions (ask user before implementing)
1. **PDF presentation**: Table? Paragraph? List? Grid? Image? Combination?
2. **Table details** (if applicable): Column count, headers, borders, background colors, cell merging
3. **Placeholder usage**: Does it use `<<variable_id>>` replacement?
4. **Multiple outputs**: Does one input block produce multiple PDF blocks?
5. **Repeated per entity**: Does block repeat per building/floor/plot?

### Converter class pattern
```python
from typing import List
from plugins.interactors.dms.core_blocks_converter.blocks_util import BlocksUtil
from plugins.interactors.dms.core_blocks_converter.dtos import PDFBlocksGenerationRequiredDetailsDTO
from plugins.interactors.dms.dtos import DtXxxBlockDTO
from plugins.interactors.dms.pdf_blocks.dtos import PDF_BLOCK_UNION_TYPE, PDFDynamicTableBlockDTO


class DtXxxBlockInteractor:

    @property
    def blocks_util(self) -> BlocksUtil:
        return BlocksUtil()

    def get_pdf_blocks(
        self,
        block_dto: DtXxxBlockDTO,
        required_details_dto: PDFBlocksGenerationRequiredDetailsDTO,
    ) -> List[PDF_BLOCK_UNION_TYPE]:
        block_dto = self._replace_placeholder_with_response(
            block_dto=block_dto,
            placeholder_data=required_details_dto.placeholder_data,
        )
        # Build and return PDF block DTOs
        return [...]

    def get_placeholder_ids(self, block_dto: DtXxxBlockDTO) -> List[str]:
        placeholder_ids = []
        # Extract <<variable_id>> from all text fields
        placeholder_ids += self.blocks_util.extract_placeholders_from_text(block_dto.heading)
        return placeholder_ids

    def _replace_placeholder_with_response(
        self,
        block_dto: DtXxxBlockDTO,
        placeholder_data: dict,
    ) -> DtXxxBlockDTO:
        placeholder_ids = self.get_placeholder_ids(block_dto)
        heading = self.blocks_util.replace_placeholder_with_response_in_text(
            text=block_dto.heading,
            placeholder_ids=placeholder_ids,
            placeholder_data=placeholder_data,
        )
        return DtXxxBlockDTO(
            block_id=block_dto.block_id,
            block_type=block_dto.block_type,
            order=block_dto.order,
            heading=heading,
        )
```

---

## Step 7 - Register in Dispatcher

### File to modify
- `plugins/interactors/dms/core_blocks_converter/get_pdf_blocks_for_blocks_template.py`

### What to do
1. Add entry to `pdf_block_generator_map`:
```python
BlockType.YOUR_TYPE.value: _get_pdf_blocks_for_xxx_block,
```

2. Add the private static method:
```python
@staticmethod
def _get_pdf_blocks_for_xxx_block(block_dto, required_details_dto):
    from plugins.interactors.dms.core_blocks_converter.dt_xxx_block import DtXxxBlockInteractor
    interactor = DtXxxBlockInteractor()
    return interactor.get_pdf_blocks(
        block_dto=block_dto,
        required_details_dto=required_details_dto,
    )
```

---

## Verification Checklist

1. **Data Loading**: Upload test CSV with new block type -> verify block DTOs created correctly
2. **Storage Round-trip**: Serialize block DTOs -> JSON -> deserialize back -> verify all fields preserved
3. **PDF Generation**: Generate a PDF with the new block -> verify visual output
4. **Edge Cases**: Test with empty data, missing fields, multiple entities (if repeated)
