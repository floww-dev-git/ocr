---
name: implement-schema-rules
description: Implement business rules from CSV files into TDR schema definitions as JSONata validation rules. Use when the user says "implement schema rules", "add CSV rules to schema", "sync business rules", or needs to translate CSV Business Rules column into schema JSONata rules.
argument-hint: "<csv_file_path> <schema_file_path> <schema_variable_name>"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

# Implement Schema Rules

Implement business rules from CSV into schema for: $ARGUMENTS

Follow @.claude/rules/clean-architecture.md and @.claude/rules/clean-code.md

## Inputs

Parse from $ARGUMENTS (space-separated):
1. **CSV file path** -- the CSV with the Business Rules column (source of truth)
2. **Schema file path** -- the Python schema file to update
3. **Schema variable name** -- the top-level dict variable in the schema file (e.g., `DIGITALIZATION_APPLICATIONS`)

If any input is missing, ask the user before proceeding.

## Workflow

### Phase 1: Understand Existing Patterns

Before writing any rules, read the existing codebase to understand the exact JSONata conventions.

1. **Read the schema file** to catalog all existing `"rules"` entries -- both at property level and at the `"items"` level. Note:
   - How `$.CURRENT.<property_key>` references are formed (they use the Python dict key, not the csv_column_name)
   - How conditional mandatory rules use `$boolean()` for presence checks
   - How multi-value conditions use `$type in [...]` vs single-value `$type = "..."`
   - How formula rules reference other fields
   - How cross-sheet existence checks use `$.sheet_name[field = $value]`
   - Whether the schema is **nested** (child arrays like co-applicants, manual logs embedded as properties). If nested, cross-sheet rules can be implemented at the parent level using `$.CURRENT.nested_array_name`

2. **Read the CSV file** to extract the Business Rules column for every field. Handle CSV parsing carefully:
   - Multi-line cell values (rules can span multiple lines within a single CSV cell)
   - The "Can be Empty" column: blank/empty means conditionally required, `Y` means optional, `N` means always required
   - Reference ID may be in different columns depending on the CSV (check both "Reference ID" and "Data Format" columns)
   - Column order varies between CSVs -- read the header row to determine positions

3. **Build a field mapping** -- for each CSV row, map:
   - `csv_column_name` -> `schema_property_key` (the Python dict key in the schema)
   - `csv_column_name` -> `business_rules` (the rules text from CSV)
   - `csv_column_name` -> `field_reference_id`

### Phase 2: Categorize Rules

For each field's business rules, categorize into rule types. See [CSV Rule Types](references/csv-rule-types.md) for the full catalog.

| Category | CSV Pattern | Schema Pattern |
|---|---|---|
| Conditional mandatory | `Mandatory If "X" is "Y"` | Ternary with `$boolean()` |
| Cannot be empty if | `Cannot be empty if X Selects as Y` | Ternary with `$boolean()` |
| Value constraint | `GT 0`, `GTE 0`, `LTE to <field>` | Comparison operators |
| Formula | `Should be equal to [A - B]` | Arithmetic expression with `=` |
| Cross-field uniqueness | `Must be unique - ...` | Flag for manual review |
| Mapping | `Road Widening -> TDR-RW` | Value mapping ternary chain |
| Conditional value | `If X = Y then Z` | Nested ternary |
| Cross-sheet existence | `must exist in X sheet` | `$boolean($.sheet[field = $val])` |
| Composite | Multiple rules on one field | Multiple entries in rules list OR compound boolean |

### Phase 3: Identify Gaps

Compare CSV rules against existing schema rules:

1. For each field with business rules in CSV, check if the schema already has a corresponding rule
2. A rule is "covered" if the schema has a JSONata rule that validates the same condition
3. **Before classifying any rule as "Cannot Be Schema-Level":**
   - Check if the referenced sheet is **nested** inside the current schema (a property of type array)
   - If nested, these rule types ARE possible at the parent level:
     - Cross-sheet existence: `$boolean($.CURRENT.nested_array)`
     - Cross-sheet aggregation: `$sum($.CURRENT.nested_array.field)`
     - Cross-array uniqueness: `$count($.CURRENT.nested_array) = $count($distinct($.CURRENT.nested_array.field))`
     - Parent-child field comparison: compare parent field against nested array fields
   - If the target field has `allowed_values` (dropdown), skip mapping validation rules -- the dropdown already constrains the value
   - Only classify as "Cannot Be Schema-Level" when: the rule requires external runtime data not in the schema, OR the referenced field doesn't exist in any accessible schema level
4. Produce a gap report:

```
## Gap Report

### Already Implemented (X rules)
- [field]: [rule summary] -- covered by existing rule at line N

### Missing Rules to Implement (Y rules)
- [field]: [rule text from CSV]
  -> Proposed JSONata: [rule expression]
  -> Error message: [descriptive message]

### Skipped -- Dropdown Constraint (W rules)
- [field]: [rule text from CSV]
  -> Reason: Field has `allowed_values` constraint; mapping rule is descriptive, not validation

### Cannot Be Schema-Level (Z rules)
- [field]: [rule text from CSV]
  -> Reason: [why this can't be a JSONata schema rule -- e.g., requires external runtime data, referenced field doesn't exist in schema]
```

5. **Present the gap report to the user and wait for approval** before implementing.

### Phase 4: Implement Missing Rules

After user approves the gap report:

1. **Group rules by location** -- rules go in the `"rules"` list at the `"items"` level of the schema (NOT on individual properties). This is the established pattern.

2. **Write JSONata rules** following the exact patterns in [JSONata Rule Patterns](references/jsonata-rule-patterns.md). Key conventions:
   - Always wrap in `( ... )` parentheses
   - Use `$.CURRENT.<property_key>` to reference the current row's fields
   - Use `$boolean()` for presence/non-empty checks
   - Use ternary `condition ? validation : true` for conditional rules
   - Assign intermediate values with `$var := $.CURRENT.<field>;` for readability
   - Use `$type in [...]` for multi-value conditions
   - Error messages should be human-readable and describe what went wrong

3. **Handle `required` flag changes** -- if a field is currently `"required": True` but the CSV shows it's conditionally required (blank "Can be Empty" with a conditional mandatory rule), change to `"required": False` and add the conditional rule.

4. **Preserve existing rules** -- never remove or modify existing rules. Only append new ones.

5. **Order of new rules** -- add new rules after existing ones, grouped logically:
   - Conditional mandatory rules first (same order as fields appear in CSV)
   - Value constraints next
   - Formula rules next
   - Cross-sheet existence checks last

### Phase 5: Verify

After implementation:

1. **Count check** -- verify that every business rule from the CSV is either:
   - Implemented as a JSONata rule in the schema
   - Listed in the "Cannot Be Schema-Level" section
   - Already existed before this change

2. **Syntax check** -- ensure the Python file is valid:
   ```bash
   python -c "import ast; ast.parse(open('<schema_file>').read()); print('Syntax OK')"
   ```

3. **Pattern consistency check** -- verify new rules follow the same indentation and formatting as existing rules in the file

4. **Present summary** to the user:
   ```
   ## Implementation Summary
   - Rules added: X
   - Rules already existed: Y
   - Rules flagged for manual review: Z
   - Rules skipped (dropdown constraint): W
   - Required flag changes: N fields changed from required=True to required=False
   - Schema file syntax: OK/ERROR
   ```

## Important Rules

- **CSV is source of truth** -- every business rule in the CSV must be accounted for
- **Never invent rules** -- only implement what the CSV states. Do not add rules based on assumptions
- **Never change field names, types, or other non-rule properties** -- only modify `"rules"` lists and `"required"` flags
- **Use schema property keys** in JSONata, not csv_column_names -- e.g., `$.CURRENT.application_type` not `$.CURRENT["Application type"]`
- **Read before writing** -- always read the full schema file before making changes to understand the property key naming
- **Multi-condition fields** -- when a CSV field has multiple business rules (separated by newlines), implement each as a separate rule entry with its own error_message
- **Blank "Can be Empty"** -- treat as conditionally required. Look for the condition in the Business Rules column
- **Cross-sheet rules** that reference other CSV sheets (e.g., "must exist in TDR Applications sheet") go in the `"rules"` list using `$boolean($.sheet_name[field = $value])` pattern if the sheet is in the same schema. If the sheet is in a different schema, flag for manual review
- **Check nesting before flagging impossible** -- if schemas are nested, cross-sheet existence, aggregation, uniqueness, and parent-child comparison rules ARE possible at the parent level
- **Skip mapping rules for dropdowns** -- if the target field has `allowed_values`, mapping rules (e.g., "Road Widening -> TDR-RW") are descriptive, not validation. The dropdown already constrains the value
