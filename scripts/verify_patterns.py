import asyncio
import sys
from pathlib import Path

# Add python directory to path
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir / "python"))

from cloudshift.infrastructure.config.dependency_injection import Container
from cloudshift.application.use_cases.manage_patterns import ManagePatternsUseCase

async def main():
    print("=== CloudShift Pattern Catalogue Self-Test ===")
    container = Container()
    
    # Ensure patterns are loaded
    engine = container.pattern_engine
    patterns_dir = current_dir / "patterns"
    if not patterns_dir.is_dir():
        print(f"Error: Patterns directory {patterns_dir} not found.")
        return

    count = engine.load_patterns(str(patterns_dir))
    print(f"Loaded {count} patterns from {patterns_dir}")

    use_case = container.resolve(ManagePatternsUseCase)
    print("Running self-tests for all patterns...")
    
    result = await use_case.test_patterns()
    
    print("\nResults:")
    print(f"  Total Patterns: {result.total_patterns}")
    print(f"  Passed:         {result.passed}")
    print(f"  Failed:         {result.failed}")
    
    if result.failed > 0:
        print("\nFailures:")
        for r in result.results:
            if not r.success:
                print(f"  - Pattern ID: {r.pattern_id}")
                print(f"    Error:      {r.error}")
                if r.expected:
                    # Show a snippet of the mismatch
                    print(f"    Expected:   {r.expected.strip()[:100]}...")
                    print(f"    Actual:     {r.actual.strip()[:100]}...")
                print("-" * 20)
        sys.exit(1)
    else:
        print("\nSUCCESS: All patterns passed their self-tests!")

if __name__ == "__main__":
    asyncio.run(main())
