# CSV Business Rule Types

Catalog of all business rule patterns found in TDR CSV files, with translation guidance.

## Rule Type 1: Conditional Mandatory

**CSV patterns:**
- `Mandatory If "X" is "Y"`
- `Mandatory if "X" is "Y" or "Z"`
- `Mandatory If "X" is "Y" or "Z" or "W"`

**Translation:**
- Single value: `$.CURRENT.x = "Y" ? $boolean($.CURRENT.target) : true`
- Multiple values: `$x := $.CURRENT.x; $x in ["Y", "Z"] ? $boolean($.CURRENT.target) : true`

**Schema impact:**
- The target field's `"required"` must be `False` (since it's conditionally required)
- If currently `True`, change to `False` as part of rule implementation

## Rule Type 2: Cannot Be Empty If

**CSV patterns:**
- `Cannot be empty if X Selects as Y`
- `Cannot be empty if X Selects as Yes`
- `Cannot be empty if X is Y`

**Translation:** Same as conditional mandatory -- `$.CURRENT.x = "Y" ? $boolean($.CURRENT.target) : true`

**Note:** "Cannot be empty if" and "Mandatory If" are semantically identical for schema purposes. Both produce the same JSONata pattern.

## Rule Type 3: Value Constraint (Absolute)

**CSV patterns:**
- `GT 0` (greater than zero)
- `GTE 0` (greater than or equal to zero)

**Translation:**
- `GT 0`: `$.CURRENT.field > 0`
- `GTE 0`: `$.CURRENT.field >= 0`

**Note:** For required numeric fields, no boolean guard needed. For optional fields, wrap: `$boolean($.CURRENT.field) ? ($.CURRENT.field > 0) : true`

## Rule Type 4: Value Constraint (Relative to Another Field)

**CSV patterns:**
- `LTE to Affected area`
- `Always less than or equal to Eligible Builtup area`
- `LTE Extent of TDR Issued`

**Translation:**
```
$boolean($.CURRENT.field_a) and $boolean($.CURRENT.field_b)
? ($.CURRENT.field_a <= $.CURRENT.field_b)
: true
```

**Key:** Map the CSV field name to the schema property key. "Affected area" might map to one of several fields depending on application type -- check the schema.

## Rule Type 5: Formula Validation

**CSV patterns:**
- `Should be equal to [A - B]`
- `Should be equal to [X - Y]`
- `equals X * Y`

**Translation:**
```
$boolean($.CURRENT.a) and $boolean($.CURRENT.b) and $boolean($.CURRENT.result)
? ($.CURRENT.result = ($.CURRENT.a - $.CURRENT.b))
: true
```

**Key:** The formula describes what the field's value SHOULD be, not a transformation. It's a validation that the value matches the expected calculation.

## Rule Type 6: Cross-Field Uniqueness

**CSV patterns:**
- `Must be unique - Primary holder's Aadhaar number and co-applicant Aadhar numbers cannot be the same`
- `Each co-applicant must provide a unique Aadhar number`
- `Cannot match primary holder's Aadhaar registered mobile number`

**Translation:**
- **If schemas are nested** (child array is a property of the parent): uniqueness CAN be validated at the parent level using count vs distinct:
  `$count($.CURRENT.nested_array) = $count($distinct($.CURRENT.nested_array.field))`
- **If schemas are flat/sibling arrays**: Cannot be validated per-row. Flag for custom checker implementation.

**Action:**
- First check if the arrays are nested (child is a property of parent)
- If nested: implement at parent level (see Rule Types 13-16 below)
- If flat: document in "Cannot Be Schema-Level" section of the gap report

## Rule Type 7: Mapping Rules

**Pre-check:** If the target field already has `allowed_values` in the schema, the dropdown constrains valid values. Skip the mapping rule -- it's descriptive, not validation. Add to "Skipped -- Dropdown Constraint" in the gap report.

**CSV patterns:**
- `Road Widening -> TDR-RW`
- `Nala Widening -> TDR-NW`
- `Lake Development -> TDR-LD`
(multiple lines, one per mapping)

**Translation:** Ternary chain validating that the derived field matches the source field's mapping:
```
$type := $.CURRENT.application_type;
$cn := $.CURRENT.cn_application_type;
($type = "Road Widening" ? $cn = "TDR-RW" :
 $type = "Nala Widening" ? $cn = "TDR-NW" :
 $type = "Lake Development" ? $cn = "TDR-LD" :
 true)
```

## Rule Type 8: Conditional Value Rules

**CSV patterns:**
- `If "X" is "Y" then value should be Z`
- `For all application types 100`
- `If relaxations utilized = Yes -> ...`

**Translation:** Ternary with value comparison:
```
$.CURRENT.condition_field = "Y"
? ($.CURRENT.target_field = expected_value)
: true
```

## Rule Type 9: Cross-Sheet Existence

**CSV patterns:**
- `Application ID should be present in TDR Applications Sheet`
- `TDR Bank Master Data 2026 - TDR Applications`
- `must exist in Officers sheet`

**Translation:**
```
$val := $.CURRENT.field;
$boolean($.sheet_name[field = $val])
```

**Key:** The `$.sheet_name` reference must match the schema's sibling array key. Only works within the same parent schema. If the reference is to a completely different schema file, flag for manual review.

## Rule Type 10: Validity Rules

**CSV patterns:**
- `Should be valid phone number`
- `Should be a valid email`

**Translation:** These are typically handled by `"pattern"` on the property definition, NOT by JSONata rules. Check if the field already has a `"pattern"` (PHONE_PATTERN, EMAIL_PATTERN). If yes, no rule needed. If no, add the pattern.

## Rule Type 11: Application-Type-Dependent Affected Area

**CSV patterns:**
- Multiple `Mandatory if "Application type" is "X"` rules on different "Extent of..." fields
- Each application type maps to a specific affected area field

**Translation:** These are individual conditional mandatory rules, one per field. But when validating Net Plot Area, you need Pattern 12 (branching affected area by type).

## Rule Type 12: Composite Rules

**CSV patterns:** Multiple rules in one cell, separated by newlines:
```
Cannot be empty if X is Yes
Always less than or equal to Eligible Builtup area
```

**Translation:** Implement as SEPARATE rule entries, each with its own error_message. Do not combine unrelated validations into one rule.

## Handling "Can be Empty" Column

| Can be Empty | Business Rules | Schema `required` | Action |
|---|---|---|---|
| N | (none) | True | No change needed |
| Y | (none) | False | No change needed |
| (blank) | Conditional rule exists | False | Ensure required=False + add conditional rule |
| (blank) | No rule | True | Keep as True (assume always required if no condition stated) |
| N | Conditional rule | Keep True + add rule | The conditional rule adds extra validation on top of required |

## Field Name to Property Key Mapping

The CSV `Field` column uses human-readable names. The schema uses snake_case property keys. To find the mapping:

1. Read the schema file and match by `"csv_column_name"` attribute
2. The dict key IS the property key used in `$.CURRENT.<key>`
3. Example: CSV field "Application type" -> schema key `application_type` -> JSONata: `$.CURRENT.application_type`

Never guess the property key. Always look it up in the schema file by matching `csv_column_name`.

## Rule Type 13: Cross-Array Aggregation (Nested Schema)

**CSV patterns:**
- `Sum of all manual log TDR areas should equal extent_tdr_utilized`
- `Total of child records must match parent field`

**Pre-condition:** The child array must be a nested property of the parent schema.

**Translation:**
```
$boolean($.CURRENT.nested_array)
? ($sum($.CURRENT.nested_array.field) = $.CURRENT.parent_field)
: true
```

## Rule Type 14: Cross-Array Uniqueness (Nested Schema)

**CSV patterns:**
- `Each co-applicant must provide a unique Aadhaar number`
- `Mobile numbers must be unique across child records`

**Pre-condition:** The child array must be a nested property of the parent schema.

**Translation:**
```
$boolean($.CURRENT.nested_array)
? ($count($.CURRENT.nested_array) = $count($distinct($.CURRENT.nested_array.field)))
: true
```

## Rule Type 15: Cross-Level Comparison (Parent vs Child Field)

**CSV patterns:**
- `Co-applicant Aadhaar cannot match primary holder's Aadhaar`
- `Child record value cannot equal parent record value`

**Pre-condition:** The child array must be a nested property of the parent schema.

**Translation:** At the parent level, check that no child record matches the parent's value:
```
$boolean($.CURRENT.nested_array)
? $count($.CURRENT.nested_array[field = $.CURRENT.parent_field]) = 0
: true
```

## Rule Type 16: Nested Array Existence (Conditional)

**CSV patterns:**
- `If requests_processed = Yes, manual logs must exist`
- `If has_co_applicants = Yes, co-applicant records must exist`

**Pre-condition:** The child array must be a nested property of the parent schema.

**Translation:**
```
$.CURRENT.condition_field = "Yes"
? $boolean($.CURRENT.nested_array)
: true
```
