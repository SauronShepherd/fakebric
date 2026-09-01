# Fakebrick controlled DAX parser catalog

This catalog describes syntax accepted by the Day 4 parser. Parser acceptance is **not** a claim that the expression is executable yet: evaluation is added incrementally on Days 5–6. Unknown functions fail with `DAX_UNSUPPORTED_FUNCTION`.

## Intrinsics

`TRUE()`, `FALSE()` and `BLANK()` are parsed as immutable literal AST nodes and take no arguments.

## Level 1 — aggregation and logic

`SUM`, `COUNT`, `COUNTA`, `COUNTROWS`, `DISTINCTCOUNT`, `AVERAGE`, `MIN`, `MAX`, `DIVIDE`, `IF`, `SWITCH`, `COALESCE`.

## Level 2 — context and filters

`CALCULATE`, `FILTER`, `ALL`, `ALLEXCEPT`, `REMOVEFILTERS`, `KEEPFILTERS`, `VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE`, `ISFILTERED`.

## Level 3 — date/time syntax catalog

`DATE`, `YEAR`, `MONTH`, `DAY`, `TODAY`, `EOMONTH`, `DATESYTD`, `TOTALYTD`, `DATEADD`, `SAMEPERIODLASTYEAR`.

The lexer recognizes DAX date/datetime literals such as `dt"2026-09-04"` and ISO datetime forms. Evaluation of Level 3 functions is not part of Day 4.

## Controlled grammar and security

- Qualified references use `Table[Member]` or `'Table Name'[Member]`.
- Bare `[Member]` references are rejected as ambiguous in this MVP grammar.
- Strings use doubled quote escaping (`"a""b"`).
- Arithmetic: `+`, `-`, `*`, `/`, `^`.
- Comparisons: `=`, `<>`, `<`, `<=`, `>`, `>=`.
- Boolean operators: `&&`, `||`, unary `!`.
- Chained comparisons are rejected as ambiguous.
- The parser never evaluates Python, JavaScript, SQL, filesystem or network expressions.
- Default limits: 4096 characters, 512 tokens, depth 32 and 256 AST nodes.
