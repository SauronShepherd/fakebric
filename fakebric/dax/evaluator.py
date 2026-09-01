from dataclasses import dataclass,field
from decimal import Decimal,InvalidOperation
from enum import Enum
from .ast import BinaryOp,FunctionCall,Literal,Reference,TableReference,UnaryOp,collect_references
from .errors import DaxEvaluationError
from .functions import get_function
from .parser import parse_dax
BLANK=None
class FilterOrigin(str,Enum):REPORT='report';PAGE='page';VISUAL='visual';USER='user';CALCULATE='calculate';CONTEXT_TRANSITION='context-transition'
O={FilterOrigin.REPORT:1,FilterOrigin.PAGE:2,FilterOrigin.VISUAL:3,FilterOrigin.USER:4,FilterOrigin.CALCULATE:5,FilterOrigin.CONTEXT_TRANSITION:6}
@dataclass(frozen=True)
class DirectFilter:table:str;column:str;values:frozenset;origin:FilterOrigin=FilterOrigin.USER
@dataclass(frozen=True)
class FilterContext:
 row_indices:dict=field(default_factory=dict);direct_filters:tuple=()
 @classmethod
 def for_table(c,t,i):return c({t.casefold():frozenset(i)})
 def with_values(s,t,c,v,origin=FilterOrigin.USER):origin=origin if isinstance(origin,FilterOrigin) else FilterOrigin(origin);return FilterContext(dict(s.row_indices),s.direct_filters+(DirectFilter(t,c,frozenset(v),origin),))
 def drop_col(s,t,c):return FilterContext(dict(s.row_indices),tuple(x for x in s.direct_filters if (x.table.casefold(),x.column.casefold())!=(t.casefold(),c.casefold())))
 def drop_table(s,t):t=t.casefold();return FilterContext({k:v for k,v in s.row_indices.items() if k!=t},tuple(x for x in s.direct_filters if x.table.casefold()!=t))
 def keep_cols(s,t,cols):t=t.casefold();cols={x.casefold() for x in cols};return FilterContext(dict(s.row_indices),tuple(x for x in s.direct_filters if x.table.casefold()!=t or x.column.casefold() in cols))
 def clear(s):return FilterContext()
 def is_direct(s,t,c):return any((x.table.casefold(),x.column.casefold())==(t.casefold(),c.casefold()) for x in s.direct_filters)
 def ordered(s):return sorted(s.direct_filters,key=lambda x:(O[x.origin],x.table.casefold(),x.column.casefold()))
@dataclass(frozen=True)
class RowContext:
 rows:dict=field(default_factory=dict)
 @classmethod
 def for_row(c,t,r):return c({t.casefold():r})
 def add(s,t,r):d=dict(s.rows);d[t.casefold()]=r;return RowContext(d)
@dataclass(frozen=True)
class ColumnVector:table:str;column:str;values:tuple;row_count:int
@dataclass(frozen=True)
class TableVector:table:str;rows:tuple;indices:tuple|None=None;replace:bool=False
@dataclass(frozen=True)
class RelationshipBinding:name:str;from_table:str;from_column:str;to_table:str;to_column:str;cardinality:str;filter_direction:str='single';active:bool=True
class DaxEngine:
 def __init__(s,tables,measures=None,relationships=None):s.t={k.casefold():(k,tuple(v)) for k,v in tables.items()};s.m={k.casefold():{n.casefold():e for n,e in v.items()} for k,v in (measures or {}).items()};s.r=tuple(relationships or ());s.stack=[];s._rels()
 @classmethod
 def from_semantic_model(c,m,t):return c(t,{x.name:{y.name:y.expression for y in x.measures} for x in m.tables},[RelationshipBinding(r.name,r.from_table,r.from_column,r.to_table,r.to_column,getattr(r.cardinality,'value',r.cardinality),getattr(r.filter_direction,'value',r.filter_direction),r.active) for r in m.relationships])
 def table(s,n):
  try:return s.t[n.casefold()]
  except KeyError as e:raise DaxEvaluationError('DAX_EVAL_TABLE_NOT_FOUND',n) from e
 def val(s,row,c,t):
  for k,v in row.items():
   if k.casefold()==c.casefold():return v
  raise DaxEvaluationError('DAX_EVAL_COLUMN_NOT_FOUND',f'{t}[{c}]')
 def _rels(s):
  p={k:k for k in s.t}
  def f(x):
   while p[x]!=x:x=p[x]
   return x
  for r in s.r:
   if not r.active:continue
   a,b=r.from_table.casefold(),r.to_table.casefold()
   if a not in p or b not in p:raise DaxEvaluationError('DAX_EVAL_RELATIONSHIP_TABLE_NOT_FOUND',r.name)
   a,b=f(a),f(b)
   if a==b:raise DaxEvaluationError('DAX_EVAL_AMBIGUOUS_RELATIONSHIP',r.name)
   p[b]=a
 def direct(s,t,f):
  n,rows=s.table(t);idx=set(f.row_indices.get(n.casefold(),range(len(rows))))
  for x in f.ordered():
   if x.table.casefold()==n.casefold():idx={i for i in idx if s.val(rows[i],x.column,n) in x.values}
  return idx
 def visible_map(s,f):
  v={n:s.direct(n,f) for n,_ in s.t.values()};chg=True
  while chg:
   chg=False
   for r in s.r:
    if not r.active:continue
    ds=[(r.to_table,r.to_column,r.from_table,r.from_column)] if r.cardinality=='one-to-many' else [(r.from_table,r.from_column,r.to_table,r.to_column)]
    if r.filter_direction=='both':ds+=[(b,d,a,c) for a,c,b,d in ds]
    for a,c,b,d in ds:
     an,ar=s.table(a);bn,br=s.table(b)
     if len(v[an])==len(ar):continue
     allowed={s.val(ar[i],c,an) for i in v[an]};new={i for i in v[bn] if s.val(br[i],d,bn) in allowed}
     if new!=v[bn]:v[bn]=new;chg=True
  return v
 def visible(s,t,f):n,_=s.table(t);return tuple(sorted(s.visible_map(f)[n]))
 def evaluate(s,e,filter_context=None,row_context=None):return s.scalar(s.ev(parse_dax(e) if isinstance(e,str) else e,filter_context or FilterContext(),row_context or RowContext()))
 def evaluate_rows(s,e,t,filter_context=None):f=filter_context or FilterContext();n,rows=s.table(t);a=parse_dax(e) if isinstance(e,str) else e;return tuple(s.scalar(s.ev(a,f,RowContext.for_row(n,rows[i]))) for i in s.visible(n,f))
 def evaluate_measure(s,t,m,filter_context=None):return s.measure(t,m,filter_context or FilterContext())
 def explain(s,e,filter_context=None):
  a=parse_dax(e) if isinstance(e,str) else e;f=filter_context or FilterContext();direct=', '.join(f'{x.origin.value}:{x.table}[{x.column}]={sorted(x.values,key=repr)!r}' for x in f.ordered()) or 'none';rel=', '.join(f'{r.name}:{r.from_table}[{r.from_column}]->{r.to_table}[{r.to_column}]/{r.cardinality}/{r.filter_direction}' for r in s.r if r.active) or 'none';return '\n'.join(['1. parse: controlled immutable AST','2. direct-filter precedence: report -> page -> visual -> user (intersection)',f'3. direct filters: {direct}',f'4. relationship propagation: {rel}','5. CALCULATE: context transition, then modifiers/filters left-to-right; same-column filters replace unless KEEPFILTERS',f'6. evaluate: {a.to_dict()}'])
 def measure(s,t,m,f):
  k=(t.casefold(),m.casefold())
  if k[0] not in s.m or k[1] not in s.m[k[0]]:raise DaxEvaluationError('DAX_EVAL_MEASURE_NOT_FOUND',m)
  if k in s.stack:raise DaxEvaluationError('DAX_EVAL_MEASURE_CYCLE',m)
  s.stack.append(k)
  try:return s.evaluate(s.m[k[0]][k[1]],filter_context=f)
  finally:s.stack.pop()
 def ev(s,n,f,row):
  if isinstance(n,Literal):return n.value
  if isinstance(n,Reference):
   tn,rows=s.table(n.table);cur=row.rows.get(tn.casefold())
   if cur is not None:return s.val(cur,n.name,tn)
   if tn.casefold() in s.m and n.name.casefold() in s.m[tn.casefold()]:return s.measure(tn,n.name,f)
   I=s.visible(tn,f);return ColumnVector(tn,n.name,tuple(s.val(rows[i],n.name,tn) for i in I),len(I))
  if isinstance(n,TableReference):tn,rows=s.table(n.table);I=s.visible(tn,f);return TableVector(tn,tuple(rows[i] for i in I),I)
  if isinstance(n,UnaryOp):v=s.scalar(s.ev(n.operand,f,row));return not s.truth(v) if n.operator=='!' else (s.num(v,1) if n.operator=='+' else -s.num(v,1))
  if isinstance(n,BinaryOp):
   if n.operator=='&&':return s.truth(s.scalar(s.ev(n.left,f,row))) and s.truth(s.scalar(s.ev(n.right,f,row)))
   if n.operator=='||':return s.truth(s.scalar(s.ev(n.left,f,row))) or s.truth(s.scalar(s.ev(n.right,f,row)))
   a,b=s.scalar(s.ev(n.left,f,row)),s.scalar(s.ev(n.right,f,row))
   if n.operator in '+-*/^':
    a,b=s.num(a,1),s.num(b,1)
    if n.operator=='+':return a+b
    if n.operator=='-':return a-b
    if n.operator=='*':return a*b
    if n.operator=='/':
     if not b:raise DaxEvaluationError('DAX_EVAL_DIVIDE_BY_ZERO','zero')
     return a/b
    return a**int(b)
   a,b=s.cmp(a,b);return {'=':a==b,'<>':a!=b,'<':a<b,'<=':a<=b,'>':a>b,'>=':a>=b}[n.operator]
  if isinstance(n,FunctionCall):return s.fn(n,f,row)
 def fn(s,n,f,row):
  lv=get_function(n.name).level
  if lv==1:return s.l1(n,f,row)
  if lv==2:return s.l2(n,f,row)
  raise DaxEvaluationError('DAX_EVAL_UNSUPPORTED_LEVEL',n.name)
 def col(s,a,f,r,name):
  v=s.ev(a,f,r)
  if not isinstance(v,ColumnVector):raise DaxEvaluationError('DAX_EVAL_TYPE',name)
  return v
 def l1(s,n,f,r):
  name=n.name
  if name in {'SUM','COUNT','COUNTA','DISTINCTCOUNT','AVERAGE'}:
   v=s.col(n.arguments[0],f,r,name);vals=[x for x in v.values if x is not None]
   if not v.row_count:return None
   if name=='SUM':return sum((s.num(x) for x in vals),Decimal(0)) if vals else None
   if name=='COUNT':
    if any(isinstance(x,bool) for x in vals):raise DaxEvaluationError('DAX_EVAL_TYPE','COUNT bool')
    return len(vals)
   if name=='COUNTA':return len(vals)
   if name=='DISTINCTCOUNT':return len(set(v.values))
   nums=[s.num(x) for x in vals if not isinstance(x,bool)];return sum(nums,Decimal(0))/Decimal(len(nums)) if nums else Decimal(0)
  if name=='COUNTROWS':t=s.ev(n.arguments[0],f,r);return len(t.rows) or None
  if name in {'MIN','MAX'}:
   if len(n.arguments)==2:a,b=s.cmp(s.scalar(s.ev(n.arguments[0],f,r)),s.scalar(s.ev(n.arguments[1],f,r)));return min(a,b) if name=='MIN' else max(a,b)
   vals=[x for x in s.col(n.arguments[0],f,r,name).values if x is not None];return (min(vals) if name=='MIN' else max(vals)) if vals else None
  if name=='DIVIDE':
   a=s.num(s.scalar(s.ev(n.arguments[0],f,r)),1);b=s.scalar(s.ev(n.arguments[1],f,r));b=Decimal(0) if b is None else s.num(b)
   if not b:return s.scalar(s.ev(n.arguments[2],f,r)) if len(n.arguments)==3 and isinstance(n.arguments[2],Literal) else None
   return a/b
  if name=='IF':return s.scalar(s.ev(n.arguments[1],f,r)) if s.truth(s.scalar(s.ev(n.arguments[0],f,r))) else (s.scalar(s.ev(n.arguments[2],f,r)) if len(n.arguments)>2 else None)
  if name=='COALESCE':
   for a in n.arguments:
    v=s.scalar(s.ev(a,f,r))
    if v is not None:return v
   return None
  if name=='SWITCH':
   x=s.scalar(s.ev(n.arguments[0],f,r));z=n.arguments[1:];last=len(z)%2
   for i in range(0,len(z)-last,2):
    if s.cmp(x,s.scalar(s.ev(z[i],f,r)))[0]==s.cmp(x,s.scalar(s.ev(z[i],f,r)))[1]:return s.scalar(s.ev(z[i+1],f,r))
   return s.scalar(s.ev(z[-1],f,r)) if last else None
 def l2(s,n,f,r):
  name=n.name
  if name=='CALCULATE':
   c=s.transition(f,r)
   for x in n.arguments[1:]:c=s.calc_filter(x,c,r)
   return s.ev(n.arguments[0],c,RowContext())
  if name=='FILTER':
   t=s.ev(n.arguments[0],f,r);rows=[];idx=[]
   for j,x in enumerate(t.rows):
    if s.truth(s.scalar(s.ev(n.arguments[1],f,r.add(t.table,x)))):rows.append(x);idx.append(t.indices[j] if t.indices else j)
   return TableVector(t.table,tuple(rows),tuple(idx),t.replace)
  if name in {'VALUES','DISTINCT'}:
   a=n.arguments[0]
   if isinstance(a,Reference):v=s.col(a,f,r,name);u=s.unique(v.values);return TableVector(v.table,tuple({v.column:x} for x in u))
   t=s.ev(a,f,r)
   if name=='VALUES':return t
   q=[]
   for x in t.rows:
    if x not in q:q.append(x)
   return TableVector(t.table,tuple(q))
  if name=='SELECTEDVALUE':u=s.unique(s.col(n.arguments[0],f,r,name).values);return u[0] if len(u)==1 else (s.scalar(s.ev(n.arguments[1],f,r)) if len(n.arguments)>1 else None)
  if name=='HASONEVALUE':return len(s.unique(s.col(n.arguments[0],f,r,name).values))==1
  if name=='ISFILTERED':a=n.arguments[0];return f.is_direct(a.table,a.name)
  if name=='ALL':return s.all(n)
  raise DaxEvaluationError('DAX_EVAL_MODIFIER_CONTEXT',name)
 def transition(s,f,r):
  c=f
  for t,row in r.rows.items():
   n,_=s.table(t)
   for k,v in row.items():c=c.drop_col(n,k).with_values(n,k,[v],FilterOrigin.CONTEXT_TRANSITION)
  return c
 def calc_filter(s,n,f,r):
  keep=False
  if isinstance(n,FunctionCall):
   if n.name=='KEEPFILTERS':n=n.arguments[0];keep=True
   elif n.name in {'ALL','REMOVEFILTERS'}:return s.remove(n,f)
   elif n.name=='ALLEXCEPT':return f.keep_cols(n.arguments[0].table,{x.name for x in n.arguments[1:]})
  if isinstance(n,FunctionCall) and n.name=='FILTER':
   t=s.l2(n,f,r);base=f if keep else (f.drop_table(t.table) if t.replace else f);d=dict(base.row_indices);d[t.table.casefold()]=frozenset(t.indices or ());return FilterContext(d,base.direct_filters)
  refs=collect_references(n)
  if len(refs)!=1:raise DaxEvaluationError('DAX_EVAL_FILTER_SHAPE','one column')
  a=refs[0];base=f if keep else f.drop_col(a.table,a.name);tn,rows=s.table(a.table);vals=[]
  for i in s.visible(tn,base):
   if s.truth(s.scalar(s.ev(n,base,r.add(tn,rows[i])))):vals.append(s.val(rows[i],a.name,tn))
  return base.with_values(tn,a.name,vals,FilterOrigin.CALCULATE)
 def remove(s,n,f):
  if not n.arguments:return f.clear()
  if len(n.arguments)==1 and isinstance(n.arguments[0],TableReference):return f.drop_table(n.arguments[0].table)
  c=f
  for a in n.arguments:c=c.drop_col(a.table,a.name)
  return c
 def all(s,n):
  if len(n.arguments)==1 and isinstance(n.arguments[0],TableReference):t,rows=s.table(n.arguments[0].table);return TableVector(t,rows,tuple(range(len(rows))),True)
  raise DaxEvaluationError('DAX_EVAL_MODIFIER_CONTEXT','ALL columns only as modifier')
 @staticmethod
 def scalar(v):
  if isinstance(v,(ColumnVector,TableVector)):raise DaxEvaluationError('DAX_EVAL_SCALAR','not scalar')
  return v
 @staticmethod
 def truth(v):return False if v is None else v if isinstance(v,bool) else v!=0 if isinstance(v,(int,float,Decimal)) else v!=''
 @staticmethod
 def num(v,blank=0):
  if v is None:
   if blank:return Decimal(0)
   raise DaxEvaluationError('DAX_EVAL_TYPE','blank')
  if isinstance(v,bool):raise DaxEvaluationError('DAX_EVAL_TYPE','bool')
  try:return v if isinstance(v,Decimal) else Decimal(str(v))
  except InvalidOperation as e:raise DaxEvaluationError('DAX_EVAL_TYPE','numeric') from e
 @classmethod
 def cmp(c,a,b):
  if a is None:a='' if isinstance(b,str) else False if isinstance(b,bool) else Decimal(0)
  if b is None:b='' if isinstance(a,str) else False if isinstance(a,bool) else Decimal(0)
  if isinstance(a,(int,float,Decimal)) and not isinstance(a,bool) and isinstance(b,(int,float,Decimal)) and not isinstance(b,bool):a,b=c.num(a),c.num(b)
  return a,b
 @staticmethod
 def unique(v):
  q=[]
  for x in v:
   if x not in q:q.append(x)
  return tuple(q)
