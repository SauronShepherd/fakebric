# DAX Level 2 filter-context semantics

Day 6 implements the controlled filter/context subset required by the 13-day plan. It is not a claim of complete Power BI DAX compatibility.

## Direct filter context

`FilterContext` can carry direct filters tagged as `report`, `page`, `visual` or `user`. They are applied deterministically in that order and intersect. Legacy row-index constraints from Day 5 remain accepted.

`ISFILTERED(Table[Column])` reports direct filters only. Cross-filtering through relationships can change the visible values used by `HASONEVALUE` and `SELECTEDVALUE` without making `ISFILTERED` true for the downstream column.

## CALCULATE and modifiers

`CALCULATE` performs context transition from the active row context, then applies its filter arguments from left to right. A boolean filter replaces existing direct filters on the same column. `KEEPFILTERS` changes that operation to intersection.

`REMOVEFILTERS()` clears all filters. Table/column forms of `REMOVEFILTERS` and `ALL`, plus `ALLEXCEPT`, remove the corresponding filters before evaluating the expression. `FILTER(ALL(Table), predicate)` can therefore replace the current base-table filter with the filtered full-table result.

The controlled boolean-filter form accepts one referenced base column. More complex arbitrary-table expressions remain intentionally outside this subset.

## Table/value functions

`FILTER` evaluates its predicate in row context. `VALUES` and `DISTINCT` expose visible values/rows, `SELECTEDVALUE` returns a scalar only when exactly one value is visible, and `HASONEVALUE` reports that condition.

## Relationships

Active relationships propagate visible key values iteratively. For one-to-many relationships the default single direction is one-side to many-side, matching the Day 3 relationship convention. `both` adds the reverse direction. Controlled many-to-many propagation follows the declared direction.

The engine rejects active relationship graphs that close a cycle/ambiguous path before executing an expression. Inactive relationships do not propagate.

## Evaluation plan

`DaxEngine.explain()` emits deterministic textual evidence covering parse, direct-filter precedence, active relationship propagation, CALCULATE rules and the AST. This is explanatory evidence only; the query planner with scan/filter/join/aggregate/project nodes belongs to Day 7.
