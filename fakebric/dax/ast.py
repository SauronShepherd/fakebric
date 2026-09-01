from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypeAlias


class Expr:
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Literal(Expr):
    literal_type: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        value = self.value
        if isinstance(value, Decimal):
            value = format(value, "f")
        return {"kind": "literal", "literalType": self.literal_type, "value": value}


@dataclass(frozen=True, slots=True)
class Reference(Expr):
    table: str
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "reference", "table": self.table, "name": self.name}


@dataclass(frozen=True, slots=True)
class TableReference(Expr):
    table: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "tableReference", "table": self.table}


@dataclass(frozen=True, slots=True)
class UnaryOp(Expr):
    operator: str
    operand: "Expression"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "unary", "operator": self.operator, "operand": self.operand.to_dict()}


@dataclass(frozen=True, slots=True)
class BinaryOp(Expr):
    operator: str
    left: "Expression"
    right: "Expression"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "binary",
            "operator": self.operator,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class FunctionCall(Expr):
    name: str
    arguments: tuple["Expression", ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "function",
            "name": self.name,
            "arguments": [argument.to_dict() for argument in self.arguments],
        }


Expression: TypeAlias = Literal | Reference | TableReference | UnaryOp | BinaryOp | FunctionCall


def collect_references(expression: Expression) -> tuple[Reference, ...]:
    found: dict[tuple[str, str], Reference] = {}

    def visit(node: Expression) -> None:
        if isinstance(node, Reference):
            found[(node.table.casefold(), node.name.casefold())] = node
            return
        if isinstance(node, UnaryOp):
            visit(node.operand)
            return
        if isinstance(node, BinaryOp):
            visit(node.left)
            visit(node.right)
            return
        if isinstance(node, FunctionCall):
            for argument in node.arguments:
                visit(argument)

    visit(expression)
    return tuple(found[key] for key in sorted(found))
