from __future__ import annotations

from decimal import Decimal

from .ast import BinaryOp, Expression, FunctionCall, Literal, Reference, TableReference, UnaryOp
from .errors import DaxDiagnostic, DaxError
from .functions import get_function
from .lexer import Token, lex_dax
from .limits import DaxLimits

_PRECEDENCE={"||":10,"&&":20,"=":30,"<>":30,"<":30,"<=":30,">":30,">=":30,"+":40,"-":40,"*":50,"/":50,"^":60}
_COMPARISONS={"=","<>","<","<=",">",">="}
_TABLE_ARGUMENTS={"COUNTROWS":{0},"FILTER":{0},"ALL":{0},"ALLEXCEPT":{0},"REMOVEFILTERS":{0},"VALUES":{0},"DISTINCT":{0}}

class Parser:
    def __init__(self,text:str,limits:DaxLimits|None=None)->None:
        self.text=text;self.limits=limits or DaxLimits();self.tokens=lex_dax(text,self.limits);self.index=0;self.nodes=0
    @property
    def current(self)->Token:return self.tokens[self.index]
    def _advance(self)->Token:
        token=self.current
        if token.kind!="EOF":self.index+=1
        return token
    def _error(self,code,message,token=None):
        target=token or self.current;return DaxError(DaxDiagnostic(code,message,target.line,target.column,target.value))
    def _node(self,node,token):
        self.nodes+=1
        if self.nodes>self.limits.max_nodes:raise self._error("DAX_LIMIT_COMPLEXITY",f"Expression exceeds AST node limit {self.limits.max_nodes}",token)
        return node
    def parse(self):
        if self.current.kind=="EOF":raise self._error("DAX_EMPTY_EXPRESSION","Expression cannot be empty")
        expression=self._expression(0,0)
        if self.current.kind!="EOF":raise self._error("DAX_UNEXPECTED_TOKEN","Unexpected token after complete expression")
        return expression
    def _expression(self,min_precedence,depth):
        if depth>self.limits.max_depth:raise self._error("DAX_LIMIT_DEPTH",f"Expression exceeds depth limit {self.limits.max_depth}")
        left=self._prefix(depth)
        while self.current.kind=="OP" and self.current.value in _PRECEDENCE:
            operator=self.current;precedence=_PRECEDENCE[operator.value]
            if precedence<min_precedence:break
            if operator.value in _COMPARISONS and isinstance(left,BinaryOp) and left.operator in _COMPARISONS:raise self._error("DAX_AMBIGUOUS_COMPARISON","Chained comparisons are ambiguous; use explicit boolean operators",operator)
            self._advance();right=self._expression(precedence if operator.value=="^" else precedence+1,depth+1);left=self._node(BinaryOp(operator.value,left,right),operator)
        return left
    def _prefix(self,depth):
        token=self.current
        if token.kind=="OP" and token.value in {"+","-","!"}:
            self._advance();return self._node(UnaryOp(token.value,self._expression(70,depth+1)),token)
        return self._primary(depth)
    def _primary(self,depth):
        token=self.current
        if token.kind=="NUMBER":
            self._advance();value=Decimal(token.value) if "." in token.value else int(token.value);return self._node(Literal("decimal" if isinstance(value,Decimal) else "integer",value),token)
        if token.kind=="STRING":self._advance();return self._node(Literal("string",token.value),token)
        if token.kind=="DATETIME":self._advance();return self._node(Literal("datetime" if "T" in token.value else "date",token.value),token)
        if token.kind=="BRACKET_NAME":raise self._error("DAX_AMBIGUOUS_REFERENCE","Unqualified [Member] references are not allowed in the controlled grammar; qualify with Table[Member]",token)
        if token.kind=="IDENT":
            self._advance()
            if self.current.kind=="BRACKET_NAME":member=self._advance();return self._node(Reference(token.value,member.value),token)
            if self.current.kind=="LPAREN":return self._function_call(token,depth+1)
            raise self._error("DAX_AMBIGUOUS_IDENTIFIER","Bare identifiers are not valid expressions; use a function call or Table[Member] reference",token)
        if token.kind=="LPAREN":
            self._advance();expression=self._expression(0,depth+1)
            if self.current.kind!="RPAREN":raise self._error("DAX_EXPECTED_RPAREN","Expected closing parenthesis")
            self._advance();return expression
        if token.kind=="EOF":raise self._error("DAX_INCOMPLETE_EXPRESSION","Expression ended before an operand was provided")
        raise self._error("DAX_EXPECTED_EXPRESSION","Expected a literal, reference, function or parenthesized expression")
    def _function_argument(self,name,position,depth):
        if position in _TABLE_ARGUMENTS.get(name,set()) and self.current.kind=="IDENT":
            next_kind=self.tokens[self.index+1].kind
            if next_kind in {"RPAREN","COMMA"}:
                token=self._advance();return self._node(TableReference(token.value),token)
        return self._expression(0,depth+1)
    def _function_call(self,name_token,depth):
        if depth>self.limits.max_depth:raise self._error("DAX_LIMIT_DEPTH",f"Expression exceeds depth limit {self.limits.max_depth}",name_token)
        name=name_token.value.upper();self._advance()
        if name in {"TRUE","FALSE","BLANK"}:
            if self.current.kind!="RPAREN":raise self._error("DAX_INTRINSIC_ARITY",f"{name}() takes no arguments",name_token)
            self._advance();return self._node(Literal("blank",None) if name=="BLANK" else Literal("boolean",name=="TRUE"),name_token)
        spec=get_function(name)
        if spec is None or not spec.parser_supported:raise self._error("DAX_UNSUPPORTED_FUNCTION",f"Function {name} is not in the published parser catalog",name_token)
        arguments=[]
        if self.current.kind!="RPAREN":
            while True:
                arguments.append(self._function_argument(name,len(arguments),depth))
                if self.current.kind!="COMMA":break
                comma=self._advance()
                if self.current.kind=="RPAREN":raise self._error("DAX_TRAILING_COMMA","Trailing comma is not allowed",comma)
        if self.current.kind!="RPAREN":raise self._error("DAX_EXPECTED_RPAREN",f"Expected closing parenthesis for {name}")
        self._advance();count=len(arguments)
        if count<spec.min_args or (spec.max_args is not None and count>spec.max_args):
            expected=str(spec.min_args) if spec.max_args==spec.min_args else f"{spec.min_args}..{spec.max_args if spec.max_args is not None else 'n'}";raise self._error("DAX_FUNCTION_ARITY",f"Function {name} expects {expected} arguments, received {count}",name_token)
        return self._node(FunctionCall(name,tuple(arguments)),name_token)

def parse_dax(text:str,limits:DaxLimits|None=None)->Expression:
    return Parser(text,limits).parse()
