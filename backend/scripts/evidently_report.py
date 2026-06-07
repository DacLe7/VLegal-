#!/usr/bin/env python
"""
Benchmark Script
Run benchmarks on the V-Legal Bot system
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
from datetime import datetime

from app.evaluation.benchmark import LegalBenchmark, create_sample_gold_dataset, TestCase
from app.core.rag_engine import RAGEngine


def main():
    parser = argparse.ArgumentParser(
        description="Run benchmarks on V-Legal Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with sample dataset
  python evidently_report.py
  
  # Run with custom gold dataset
  python evidently_report.py --gold-dataset ./my_tests.json
  
  # Quick test with a single question
  python evidently_report.py --quick-test "Quyền sở hữu là gì?"
        """
    )
    
    parser.add_argument(
        '--gold-dataset',
        type=str,
        help='Path to gold standard dataset (JSON)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./benchmark_results',
        help='Directory for benchmark results'
    )
    parser.add_argument(
        '--quick-test',
        type=str,
        help='Run a quick test with a single question'
    )
    parser.add_argument(
        '--create-sample',
        action='store_true',
        help='Create a sample gold dataset'
    )
    
    args = parser.parse_args()
    
    # Create sample dataset if requested
    if args.create_sample:
        create_sample_gold_dataset(f"{args.output_dir}/gold_dataset.json")
        return
    
    print("=" * 60)
    print("V-Legal Bot - Benchmark Suite")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Initialize components
    print("Initializing RAG Engine...")
    try:
        engine = RAGEngine()
    except Exception as e:
        print(f"Error initializing RAG Engine: {e}")
        print("Make sure you have:")
        print("  1. Set GEMINI_API_KEY in .env")
        print("  2. Ingested documents into vector store")
        return 1
    
    # Initialize benchmark
    benchmark = LegalBenchmark(output_dir=args.output_dir)
    
    # Quick test mode
    if args.quick_test:
        print(f"\nQuick Test: {args.quick_test}")
        print("-" * 40)
        
        # Create a simple test case
        test_case = TestCase(
            question=args.quick_test,
            expected_answer="",
            expected_sources=[],
            category="quick_test"
        )
        
        response = engine.query(args.quick_test)
        
        print(f"\nAnswer:\n{response.answer}")
        print(f"\nSources:")
        for source in response.sources:
            print(f"  - {source.reference} (score: {source.score:.2%})")
        
        return 0
    
    # Load test cases
    if args.gold_dataset:
        print(f"Loading gold dataset: {args.gold_dataset}")
        benchmark.load_gold_dataset(args.gold_dataset)
    else:
        # Use built-in sample
        print("Using built-in sample test cases")
        from app.evaluation.benchmark import SAMPLE_GOLD_DATASET
        for item in SAMPLE_GOLD_DATASET:
            benchmark.add_test_case(TestCase(
                question=item['question'],
                expected_answer=item['expected_answer'],
                expected_sources=item.get('expected_sources', []),
                category=item.get('category', 'general')
            ))
    
    print(f"Loaded {len(benchmark.test_cases)} test cases")
    print()
    
    # Run benchmark
    print("Running benchmark...")
    print("-" * 40)
    
    results = benchmark.run_benchmark(engine)
    
    # Print results
    print()
    print("=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Pass Rate: {results['pass_rate']:.1%}")
    print()
    print("Average Scores:")
    for metric, score in results['average_scores'].items():
        status = "✓" if score >= 0.7 else "✗"
        print(f"  {status} {metric}: {score:.2%}")
    
    # Save results
    output_file = benchmark.save_results()
    print()
    print(f"Results saved to: {output_file}")
    
    # Return exit code based on pass rate
    if results['pass_rate'] >= 0.8:
        print("\n✓ Benchmark PASSED")
        return 0
    else:
        print("\n✗ Benchmark FAILED - Consider reviewing failed cases")
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
