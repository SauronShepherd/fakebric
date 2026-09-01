from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .errors import DaxDiagnostic, DaxError
from .limits import DaxLimits


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: str
    line: int
    column: int
    offset: int


class Lexer:
    def __init__(self, text: str, limits: DaxLimits | None = None) -> None:
        self.text = text
        self.limits = limits or DaxLimits()
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    def _diagnostic(self, code: str, message: str, token: str, line: int | None = None, column: int | None = None) -> DaxError:
        return DaxError(DaxDiagnostic(code, message, self.line if line is None else line, self.column if column is None else column, token))

    def _peek(self, count: int = 0) -> str:
        position = self.index + count
        return self.text[position] if position < len(self.text) else ""

    def _advance(self) -> str:
        char = self._peek()
        if not char:
            return ""
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _emit(self, kind: str, value: str, line: int, column: int, offset: int) -> None:
        self.tokens.append(Token(kind, value, line, column, offset))
        if len(self.tokens) > self.limits.max_tokens:
            raise self._diagnostic("DAX_LIMIT_TOKENS", f"Expression exceeds token limit {self.limits.max_tokens}", value, line, column)

    def tokenize(self) -> tuple[Token, ...]:
        if len(self.text) > self.limits.max_length:
            raise DaxError(DaxDiagnostic("DAX_LIMIT_LENGTH", f"Expression exceeds length limit {self.limits.max_length}", 1, self.limits.max_length + 1, self.text[self.limits.max_length:self.limits.max_length+16]))
        while self.index < len(self.text):
            char = self._peek()
            if char.isspace(): self._advance(); continue
            line, column, offset = self.line, self.column, self.index
            if char == '"':
                self._advance(); value=[]
                while True:
                    current=self._peek()
                    if not current: raise self._diagnostic("DAX_UNTERMINATED_STRING","Unterminated string literal",'"',line,column)
                    if current == '"':
                        self._advance()
                        if self._peek() == '"': self._advance(); value.append('"'); continue
                        break
                    value.append(self._advance())
                self._emit("STRING","".join(value),line,column,offset); continue
            if char == "'":
                self._advance(); value=[]
                while True:
                    current=self._peek()
                    if not current: raise self._diagnostic("DAX_UNTERMINATED_IDENTIFIER","Unterminated quoted identifier","'",line,column)
                    if current == "'":
                        self._advance()
                        if self._peek() == "'": self._advance(); value.append("'"); continue
                        break
                    value.append(self._advance())
                self._emit("IDENT","".join(value),line,column,offset); continue
            if char == "[":
                self._advance(); value=[]
                while True:
                    current=self._peek()
                    if not current: raise self._diagnostic("DAX_UNTERMINATED_REFERENCE","Unterminated bracket reference","[",line,column)
                    if current == "]":
                        self._advance()
                        if self._peek() == "]": self._advance(); value.append("]"); continue
                        break
                    value.append(self._advance())
                name="".join(value).strip()
                if not name: raise self._diagnostic("DAX_EMPTY_REFERENCE","Bracket reference cannot be empty","[]",line,column)
                self._emit("BRACKET_NAME",name,line,column,offset); continue
            if char.isdigit():
                value=[self._advance()]
                while self._peek().isdigit(): value.append(self._advance())
                if self._peek() == ".":
                    value.append(self._advance())
                    if not self._peek().isdigit(): raise self._diagnostic("DAX_INVALID_NUMBER","Decimal point must be followed by digits","".join(value),line,column)
                    while self._peek().isdigit(): value.append(self._advance())
                self._emit("NUMBER","".join(value),line,column,offset); continue
            if char.isalpha() or char == "_":
                value=[self._advance()]
                while self._peek().isalnum() or self._peek() == "_": value.append(self._advance())
                identifier="".join(value)
                if identifier.casefold() == "dt" and self._peek() == '"':
                    self._advance(); literal=[]
                    while True:
                        current=self._peek()
                        if not current: raise self._diagnostic("DAX_UNTERMINATED_DATETIME","Unterminated DAX datetime literal",'dt"',line,column)
                        if current == '"': self._advance(); break
                        literal.append(self._advance())
                    raw="".join(literal)
                    try:
                        normalized = datetime.fromisoformat(raw.replace("Z","+00:00")).isoformat() if ("T" in raw or " " in raw) else date.fromisoformat(raw).isoformat()
                    except ValueError as exc:
                        raise self._diagnostic("DAX_INVALID_DATETIME",'DAX datetime literal must use dt"YYYY-MM-DD" or an ISO datetime form',raw,line,column) from exc
                    self._emit("DATETIME",normalized,line,column,offset); continue
                self._emit("IDENT",identifier,line,column,offset); continue
            pair=char+self._peek(1)
            if pair in {"<=",">=","<>","!=","==","&&","||"}:
                self._advance(); self._advance(); normalized="=" if pair=="==" else "<>" if pair=="!=" else pair; self._emit("OP",normalized,line,column,offset); continue
            if char in "+-*/^=<>!": self._advance(); self._emit("OP",char,line,column,offset); continue
            if char == "(": self._advance(); self._emit("LPAREN",char,line,column,offset); continue
            if char == ")": self._advance(); self._emit("RPAREN",char,line,column,offset); continue
            if char == ",": self._advance(); self._emit("COMMA",char,line,column,offset); continue
            raise self._diagnostic("DAX_INVALID_TOKEN","Unsupported token",char,line,column)
        self.tokens.append(Token("EOF","",self.line,self.column,self.index))
        return tuple(self.tokens)


def lex_dax(text: str, limits: DaxLimits | None = None) -> tuple[Token, ...]:
    return Lexer(text, limits).tokenize()
