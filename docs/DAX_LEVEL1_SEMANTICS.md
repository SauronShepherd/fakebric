# DAX Level 1 evaluation semantics

Day 5 executes only the published Level 1 subset. Parsing a Level 2/3 function does not make it executable.

## Context

- `FilterContext` stores visible row indices per table. A table absent from the context exposes all rows.
- `RowContext` resolves `Table[Column]` to the current row during row-wise evaluation.
- Relationship propagation and filter precedence are not applied yet; they are Day 6 scope.

## BLANK

The evaluator represents BLANK internally as `None`, distinct from numeric zero. Controlled coercions are explicit:

- arithmetic treats BLANK as zero;
- boolean context treats BLANK as false;
- comparison to numeric zero treats BLANK as zero;
- aggregate functions ignore BLANK where their documented behavior requires it;
- an empty filtered table returns BLANK for the Day 5 aggregate golden cases.

## Level 1 functions

Implemented: `SUM`, `COUNT`, `COUNTA`, `COUNTROWS`, `DISTINCTCOUNT`, `AVERAGE`, `MIN`, `MAX`, `DIVIDE`, `IF`, `SWITCH`, `COALESCE`.

`DIVIDE(numerator, denominator[, alternate])` returns BLANK for zero/BLANK denominator unless a literal alternate is supplied. Raw `/` division by zero fails with `DAX_EVAL_DIVIDE_BY_ZERO` so callers must choose explicit safe semantics.

All arithmetic results are normalized through Python `Decimal` rather than binary floating point for deterministic local behavior.

## Unsupported in Day 5

`CALCULATE`, `FILTER`, `ALL`, `ALLEXCEPT`, `REMOVEFILTERS`, `KEEPFILTERS`, `VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE`, `ISFILTERED`, relationship propagation, filter-layer precedence and context transition are reserved for Day 6.
