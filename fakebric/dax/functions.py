from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class FunctionSpec:
    name: str
    level: int
    min_args: int
    max_args: int | None
    parser_supported: bool = True

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["minArgs"] = data.pop("min_args")
        data["maxArgs"] = data.pop("max_args")
        data["parserSupported"] = data.pop("parser_supported")
        return data


_FUNCTIONS = (
    FunctionSpec("SUM", 1, 1, 1),
    FunctionSpec("COUNT", 1, 1, 1),
    FunctionSpec("COUNTA", 1, 1, 1),
    FunctionSpec("COUNTROWS", 1, 1, 1),
    FunctionSpec("DISTINCTCOUNT", 1, 1, 1),
    FunctionSpec("AVERAGE", 1, 1, 1),
    FunctionSpec("MIN", 1, 1, 2),
    FunctionSpec("MAX", 1, 1, 2),
    FunctionSpec("DIVIDE", 1, 2, 3),
    FunctionSpec("IF", 1, 2, 3),
    FunctionSpec("SWITCH", 1, 3, None),
    FunctionSpec("COALESCE", 1, 1, None),
    FunctionSpec("CALCULATE", 2, 1, None),
    FunctionSpec("FILTER", 2, 2, 2),
    FunctionSpec("ALL", 2, 0, None),
    FunctionSpec("ALLEXCEPT", 2, 2, None),
    FunctionSpec("REMOVEFILTERS", 2, 0, None),
    FunctionSpec("KEEPFILTERS", 2, 1, 1),
    FunctionSpec("VALUES", 2, 1, 1),
    FunctionSpec("DISTINCT", 2, 1, 1),
    FunctionSpec("SELECTEDVALUE", 2, 1, 2),
    FunctionSpec("HASONEVALUE", 2, 1, 1),
    FunctionSpec("ISFILTERED", 2, 1, 1),
    FunctionSpec("DATE", 3, 3, 3),
    FunctionSpec("YEAR", 3, 1, 1),
    FunctionSpec("MONTH", 3, 1, 1),
    FunctionSpec("DAY", 3, 1, 1),
    FunctionSpec("TODAY", 3, 0, 0),
    FunctionSpec("EOMONTH", 3, 2, 2),
    FunctionSpec("DATESYTD", 3, 1, 2),
    FunctionSpec("TOTALYTD", 3, 2, 3),
    FunctionSpec("DATEADD", 3, 3, 3),
    FunctionSpec("SAMEPERIODLASTYEAR", 3, 1, 1),
)

FUNCTION_CATALOG: dict[str, FunctionSpec] = {item.name: item for item in _FUNCTIONS}


def get_function(name: str) -> FunctionSpec | None:
    return FUNCTION_CATALOG.get(name.upper())


def catalog_by_level() -> dict[int, tuple[FunctionSpec, ...]]:
    levels: dict[int, list[FunctionSpec]] = {}
    for spec in _FUNCTIONS:
        levels.setdefault(spec.level, []).append(spec)
    return {level: tuple(items) for level, items in sorted(levels.items())}
