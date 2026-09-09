# JSONata Rule Patterns

Reference for writing schema validation rules in TDR dataio schemas. All examples are from the actual codebase.

## Rule Location

Rules live in the `"rules"` list at the `"items"` level of a schema array, NOT on individual properties:

```python
SCHEMA_NAME = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "field_a": { ... },
            "field_b": { ... },
        },
        "rules": [    # <-- rules go HERE, after "properties"
            {
                "rule": """...""",
                "error_message": "...",
            },
        ],
    },
}
```

Some schemas (nested sub-schemas like FIELD_CHANGE_LOGS) put rules inside `"items"` -> `"rules"` at the nested level. Follow whichever placement the target schema already uses.

## Rule Entry Structure

```python
{
    "rule": """
            (
                <JSONata expression that returns true if valid, false if invalid>
            )
            """,
    "error_message": "<Human-readable description of what went wrong>",
},
```

## Pattern 1: Conditional Mandatory (single condition)

CSV: `Mandatory If "Application type" is "Lake Development"`

```python
{
    "rule": """
            (
                $.CURRENT.application_type = "Lake Development"
                ? $boolean($.CURRENT.name_of_lake)
                : true
            )
            """,
    "error_message": "Name of the Lake is required for Lake Development",
},
```

## Pattern 2: Conditional Mandatory (multiple trigger values)

CSV: `Mandatory If "Application type" is "Nala Widening (Private Lands)" or "Nala Widening"`

```python
{
    "rule": """
            (
                $type := $.CURRENT.application_type;
                $type in ["Nala Widening (Private Lands)", "Nala Widening"]
                ? $boolean($.CURRENT.name_of_nala)
                : true
            )
            """,
    "error_message": "Name of the Nala is required for Nala Widening",
},
```

## Pattern 3: Conditional Mandatory (group of fields)

CSV: `Mandatory If "Represented by" is "Firm"` (applies to firm_name, firm_pancard_no, upload_firm_pancard, firm_address)

```python
{
    "rule": """
            (
                $.CURRENT.represented_by = "Firm"
                ? (
                    $boolean($.CURRENT.firm_pancard_no) and
                    $boolean($.CURRENT.firm_name) and
                    $boolean($.CURRENT.upload_firm_pancard) and
                    $boolean($.CURRENT.firm_address)
                  )
                : true
            )
            """,
    "error_message": "Firm details are required when Represented by Firm",
},
```

When multiple fields share the SAME condition, combine into ONE rule with `and`. Do not create separate rules per field.

## Pattern 4: Cannot Be Empty If (select-based condition)

CSV: `Cannot be empty if Whether already benefit of relaxations been utilized for the site? Selects as Yes`

```python
{
    "rule": """
            (
                $relax := $.CURRENT.relaxations_utilized;
                $relax = "Yes"
                ? (
                    $boolean($.CURRENT.type_setbacks_availed) and
                    $boolean($.CURRENT.file_name) and
                    $boolean($.CURRENT.building_permit_order) and
                    $boolean($.CURRENT.drawing_plan) and
                    $boolean($.CURRENT.eligible_builtup_area) and
                    $boolean($.CURRENT.builtup_area_availed) and
                    $boolean($.CURRENT.balance_area_eligible)
                  )
                : true
            )
            """,
    "error_message": "Relaxation details required when Relaxations Utilized is Yes",
},
```

## Pattern 5: Value Constraint -- Greater Than / Less Than

CSV: `GT 0`

```python
{
    "rule": """
            $.CURRENT.total_site_area > 0
            """,
    "error_message": "Total Site Area must be greater than 0",
},
```

CSV: `LTE to Affected area` (comparison against another field)

```python
{
    "rule": """
            (
                $boolean($.CURRENT.extent_of_land_considered) and $boolean($.CURRENT.affected_area)
                ? ($.CURRENT.extent_of_land_considered <= $.CURRENT.affected_area)
                : true
            )
            """,
    "error_message": "Extent of Land Considered for TDR must be LTE Affected area",
},
```

Always guard cross-field comparisons with `$boolean()` checks to handle empty values gracefully.

## Pattern 6: Formula Validation

CSV: `Should be equal to [Total Site Area - Extent of Widening Area]`

```python
{
    "rule": """
            (
                $boolean($.CURRENT.total_site_area) and
                $boolean($.CURRENT.extent_area) and
                $boolean($.CURRENT.net_plot_area)
                ? ($.CURRENT.net_plot_area = ($.CURRENT.total_site_area - $.CURRENT.extent_area))
                : true
            )
            """,
    "error_message": "Net Plot Area must equal Total Site Area minus Extent of Widening Area",
},
```

## Pattern 7: Comparison Constraint (field vs field)

CSV: `Always less than or equal to Eligible Builtup area`

```python
{
    "rule": """
            (
                $boolean($.CURRENT.eligible_builtup_area) and
                $boolean($.CURRENT.builtup_area_availed)
                ? ($.CURRENT.builtup_area_availed <= $.CURRENT.eligible_builtup_area)
                : true
            )
            """,
    "error_message": "Builtup area availed must be LTE Eligible Builtup area",
},
```

## Pattern 8: Cross-Sheet Existence Check

CSV: `Application ID should be present in TDR Applications Sheet`

```python
{
    "rule": """
            (
                $app_id := $.CURRENT.application_id;
                $boolean($.digitalization_applications[application_id = $app_id])
            )
            """,
    "error_message": "Application ID must exist in Digitalization Application sheet",
},
```

The `$.sheet_name` references the sibling schema array by its Python variable name (lowercased, underscored). This only works when both schemas are part of the same parent schema.

## Pattern 9: Conditional Value Constraint

CSV: `Can be Yes only if Extent of TDR Already Utilized > 0`

```python
{
    "rule": """
            (
                $proc := $.CURRENT.requests_processed;
                $utilized := $.CURRENT.extent_tdr_utilized;
                $proc = "Yes" ? ($utilized > 0) : true
            )
            """,
    "error_message": "Requests Processed can be Yes only if Extent of TDR Utilized > 0",
},
```

## Pattern 10: Direct Equality Constraint

CSV: `Total Extent of the Site should be Equal to Total Site Area`

```python
{
    "rule": """
            $.CURRENT.total_extent_site = $.CURRENT.total_site_area
            """,
    "error_message": "Total Extent of the Site must equal Total Site Area",
},
```

## Pattern 11: Conditional Formula (branching by condition)

CSV: `If relaxations = Yes -> % * Balance; If No -> % * Extent`

```python
{
    "rule": """
            (
                $relax := $.CURRENT.relaxations_utilized;
                $pct := $.CURRENT.percentage_tdr_recommended;
                $balance := $.CURRENT.balance_area_eligible;
                $extent := $.CURRENT.extent_of_land_considered;
                $permissible := $.CURRENT.permissible_tdr_value;
                ($relax = "Yes" and $pct and $balance and $permissible)
                ? ($permissible = ($pct / 100) * $balance)
                : ($relax = "No" and $pct and $extent and $permissible)
                ? ($permissible = ($pct / 100) * $extent)
                : true
            )
            """,
    "error_message": "Permissible TDR Value calculation depends on relaxation status",
},
```

## Pattern 12: Net Plot Area with Application-Type-Dependent Affected Area

CSV: `Net Plot Area = Total Site Area - Affected Area` (where affected area field varies by application type)

```python
{
    "rule": """
            (
                $gross := $.CURRENT.total_site_area;
                $app_type := $.CURRENT.application_type;
                $affected := (
                    $app_type = "Road Widening" ? $.CURRENT.extent_of_road_widening_area :
                    $app_type = "Master Plan Road Widening" ? $.CURRENT.affected_master_plan_road_area :
                    $app_type = "Lake Development" ? $.CURRENT.extent_of_lake_development_area :
                    $app_type in ["Nala Widening (Private Lands)", "Nala Widening"] ? $.CURRENT.nala_widening_area :
                    $.CURRENT.extent_of_widening_area
                );
                $net := $.CURRENT.net_plot_area;
                ($gross and $affected and $net)
                ? ($net = $gross - $affected)
                : true
            )
            """,
    "error_message": "Net Plot Area must equal Total Site Area minus Affected Area",
},
```

## Pattern 13: Whatsapp Number Validation (Cannot-Be-Same-As)

CSV: `Cannot be same as Aadhar Registered Mobile No. if Is Whatsapp same is No`

```python
{
    "rule": """
            (
                $.CURRENT.is_whatsapp_same = "No"
                ? ($.CURRENT.whatsapp_mobile_number != $.CURRENT.aadhaar_registered_mobile_no)
                : true
            )
            """,
    "error_message": "Whatsapp number cannot be same as Aadhaar mobile when marked different",
},
```

## Pattern 14: Cross-Array Aggregation (Nested Schema)

CSV: `Sum of all manual log TDR areas should equal extent_tdr_utilized`

```python
{
    "rule": """
            (
                $boolean($.CURRENT.digitalization_manual_logs)
                ? ($sum($.CURRENT.digitalization_manual_logs.tdr_area) = $.CURRENT.extent_tdr_utilized)
                : true
            )
            """,
    "error_message": "Sum of manual log TDR areas must equal Extent of TDR Already Utilized",
},
```

## Pattern 15: Cross-Array Uniqueness (Nested Schema)

CSV: `Each co-applicant must provide a unique Aadhaar number`

```python
{
    "rule": """
            (
                $boolean($.CURRENT.digitalization_co_applicants)
                ? (
                    $count($.CURRENT.digitalization_co_applicants) =
                    $count($distinct($.CURRENT.digitalization_co_applicants.aadhaar_no))
                  )
                : true
            )
            """,
    "error_message": "Each co-applicant must have a unique Aadhaar number",
},
```

## Pattern 16: Cross-Level Comparison (Parent vs Child)

CSV: `Co-applicant Aadhaar cannot match primary holder's Aadhaar`

```python
{
    "rule": """
            (
                $boolean($.CURRENT.digitalization_co_applicants)
                ? ($count($.CURRENT.digitalization_co_applicants[aadhaar_no = $.CURRENT.aadhaar_no]) = 0)
                : true
            )
            """,
    "error_message": "Co-applicant Aadhaar cannot be same as primary holder's Aadhaar",
},
```

## Pattern 17: Nested Array Existence (Conditional)

CSV: `If requests_processed = Yes, manual logs must exist`

```python
{
    "rule": """
            (
                $.CURRENT.requests_processed = "Yes"
                ? $boolean($.CURRENT.digitalization_manual_logs)
                : true
            )
            """,
    "error_message": "Manual logs are required when Utilization/Sale Requests have been processed",
},
```

## Nested Schema Architecture

When schemas are nested (child arrays are properties of the parent object), the parent-level rules have access to both parent fields and child arrays:

```
PARENT_SCHEMA (array)
  └── items (object)
       ├── properties:
       │    ├── child_array_a: CHILD_SCHEMA_A   ← accessible as $.CURRENT.child_array_a
       │    ├── child_array_b: CHILD_SCHEMA_B   ← accessible as $.CURRENT.child_array_b
       │    └── parent_field: { ... }            ← accessible as $.CURRENT.parent_field
       └── rules: [ ... ]   ← can reference both parent fields AND child arrays
```

This enables rules that would be impossible in flat/sibling schemas:
- **Existence**: `$boolean($.CURRENT.child_array)` -- check if child records exist
- **Aggregation**: `$sum($.CURRENT.child_array.field)` -- sum across child records
- **Uniqueness**: `$count($.CURRENT.child_array) = $count($distinct($.CURRENT.child_array.field))`
- **Cross-level comparison**: `$.CURRENT.child_array[field = $.CURRENT.parent_field]` -- find children matching parent value

Always check schema nesting structure before classifying cross-sheet rules as impossible.

## Formatting Conventions

1. **Indentation**: 8 spaces before `(`, inner content indented 12 spaces. Match the existing file's indentation.
2. **Triple-quoted strings**: Always use `"""..."""` for rule expressions
3. **Trailing comma**: Always include trailing comma after `}` in the rules list
4. **Variable naming**: Use descriptive short names -- `$relax`, `$type`, `$occ`, `$proc`, `$pct`
5. **Boolean guards**: Always wrap field references in `$boolean()` or truthiness check before arithmetic/comparison when the field might be empty
6. **Error messages**: Present tense, describe the constraint -- "X must be Y" or "X is required when Y"
