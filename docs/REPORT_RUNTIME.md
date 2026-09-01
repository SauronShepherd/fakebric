# Report runtime MVP — Day 8

Day 8 introduces the first browser-oriented report runtime contract. A `Report` contains ordered pages, reusable query definitions, scoped filters, a theme and typed visuals. The runtime is intentionally passive: it renders query results and visual states but does not yet implement cross-filter interactions, drill behavior, export or editor UX; those belong to Day 9.

## Pages and geometry

Pages have stable ids, unique order, width, height and portrait/landscape orientation. Every visual has a bounded `Frame` (`x`, `y`, `width`, `height`, `zIndex`). Validation rejects duplicate visual ids and any frame that escapes the page canvas.

## Visuals

The controlled visual catalog is: `card`, `table`, `matrix`, `bar`, `column`, `line`, `pie`, `donut`, `scatter` and `slicer`. Each visual type uses a discriminated Pydantic contract with its own property schema. Visuals reference a declared report query by `queryId`; dangling references fail validation.

## Runtime states and accessibility

`ReportRuntime` emits deterministic `loading`, `empty`, `error` and `ready` states. The minimal HTML representation is data-only and escaped, uses `role="group"`, and exposes a stable `aria-label` from `altText`, title or a deterministic fallback. It does not execute arbitrary HTML or JavaScript from report definitions.

## Theme and format

Reports include a palette, font family, foreground/background and visual background. Visual format supports title visibility, foreground/background and deterministic number-format metadata (decimals, thousands separator, prefix and suffix).

## CRUD API

The standalone report router exposes list/create/get/update/delete plus a minimal render endpoint. Writes use the existing versioned-resource ETag pattern; updates increment `revision` and reject stale `If-Match` values. Persistent control-plane integration remains Day 10 scope.
