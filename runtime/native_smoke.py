from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession

GLUTEN_PLUGIN = "org.apache.gluten.GlutenPlugin"
GLUTEN_SHUFFLE = "org.apache.spark.shuffle.sort.ColumnarShuffleManager"
NATIVE_PLAN_MARKERS = (
    "WholeStageTransformer",
    "ProjectExecTransformer",
    "FilterExecTransformer",
    "VeloxColumnarToRowExec",
)


def build_session() -> SparkSession:
    jar = Path(os.getenv("GLUTEN_BUNDLE_JAR", "/opt/gluten/gluten-velox-bundle.jar"))
    if not jar.is_file():
        raise RuntimeError(f"NATIVE_INIT_FAILED: Gluten bundle not found: {jar}")

    return (
        SparkSession.builder.master("local[1]")
        .appName("fakebric-native-smoke")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.adaptive.enabled", "false")
        .config("spark.plugins", GLUTEN_PLUGIN)
        .config("spark.jars", str(jar))
        .config("spark.driver.extraClassPath", str(jar))
        .config("spark.executor.extraClassPath", str(jar))
        .config("spark.memory.offHeap.enabled", "true")
        .config("spark.memory.offHeap.size", "512m")
        .config("spark.shuffle.manager", GLUTEN_SHUFFLE)
        .getOrCreate()
    )


def main() -> int:
    try:
        spark = build_session()
    except Exception as exc:
        print(json.dumps({"ok": False, "errorCode": "NATIVE_INIT_FAILED", "detail": str(exc)}))
        return 20

    try:
        frame = spark.range(0, 100).where("id % 2 = 0").selectExpr("id", "id * 3 AS triple")
        rows = frame.count()
        total = frame.groupBy().sum("triple").collect()[0][0]
        plan = frame._jdf.queryExecution().executedPlan().toString()
        native_markers = [marker for marker in NATIVE_PLAN_MARKERS if marker in plan]
        payload = {
            "ok": rows == 50 and total == 7350 and bool(native_markers),
            "rows": rows,
            "sumTriple": total,
            "sparkPlugins": spark.sparkContext.getConf().get("spark.plugins", ""),
            "shuffleManager": spark.sparkContext.getConf().get("spark.shuffle.manager", ""),
            "nativePlanMarkers": native_markers,
            "plan": plan,
        }
        print(json.dumps(payload, sort_keys=True))
        return 0 if payload["ok"] else 21
    except Exception as exc:
        print(json.dumps({"ok": False, "errorCode": "NATIVE_EXECUTION_FAILED", "detail": str(exc)}))
        return 22
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
