import sys
import asyncio
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_evaluation import run_benchmark_evaluation
from app.services.scanning_booth import deterministic_scan

async def fast_scan(text, main_cat, sub_cat):
    return deterministic_scan(text, main_cat, sub_cat)

async def main():
    report = await run_benchmark_evaluation(fast_scan)
    print("Metrics:", report["metrics"])
    print("Safety Guardrails:", report["safetyGuardrails"])
    print("Confusion Matrix:", report["confusionMatrix"])
    print("Total Duration:", report["totalDurationMs"], "ms")
    print("All evaluated successfully!")

if __name__ == "__main__":
    asyncio.run(main())
