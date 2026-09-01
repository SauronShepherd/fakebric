from __future__ import annotations

import time

from .cache import CachedExecution, QueryCache
from .cancel import QueryCancellationToken
from .contracts import QueryMetrics, QueryPagination, QueryRequest, QueryResponse
from .executor import QueryExecutor
from .planner import QueryPlanner


class QueryService:
    def __init__(self, cache=None, planner=None, executor=None, clock=time.perf_counter) -> None:
        self.cache = cache or QueryCache()
        self.planner = planner or QueryPlanner()
        self.executor = executor or QueryExecutor()
        self.clock = clock

    def _response(self, model, request, snapshot, cache_hit, duration_ms):
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        rows = [list(row) for row in snapshot.rows[start:end]]
        total = len(snapshot.rows)
        return QueryResponse(modelId=model.id, revision=model.revision, columns=list(snapshot.columns), rows=rows, warnings=list(snapshot.warnings), metrics=QueryMetrics(rowsRead=snapshot.rows_read, bytesRead=snapshot.bytes_read, durationMs=duration_ms, planningMs=0.0 if cache_hit else snapshot.planning_ms, executionMs=0.0 if cache_hit else snapshot.execution_ms, returnedRows=len(rows), cacheHit=cache_hit, backend=snapshot.backend), pagination=QueryPagination(page=request.page, pageSize=request.page_size, totalRows=total, hasMore=end < total), plan=list(snapshot.plan), planText=snapshot.plan_text)

    def query(self, model, tables, request: QueryRequest, *, data_revision="inline", token=None):
        started = self.clock()
        token = token or QueryCancellationToken(request.timeout_ms)
        token.check()
        key = self.cache.key(model, request, tables, data_revision)
        cached = self.cache.get(key)
        if cached is not None:
            return self._response(model, request, cached, True, (self.clock() - started) * 1000)
        planning_started = self.clock()
        plan = self.planner.plan(model, request)
        planning_ms = (self.clock() - planning_started) * 1000
        token.check()
        result = self.executor.execute(model, tables, request, plan, token)
        snapshot = CachedExecution(result.columns, result.rows, result.warnings, plan.nodes, plan.text, result.rows_read, result.bytes_read, result.backend, planning_ms, result.execution_ms)
        self.cache.put(key, snapshot)
        return self._response(model, request, snapshot, False, (self.clock() - started) * 1000)
