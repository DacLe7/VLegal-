"""
Evidently AI Benchmark Module
Test suite for evaluating RAG quality before deployment
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

# Note: evidently requires installation
try:
    from evidently import ColumnMapping
    from evidently.report import Report
    from evidently.metric_preset import TextEvals
    from evidently.metrics import TextLength, SentenceCount
    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False


@dataclass
class TestCase:
    """A single test case for benchmark"""
    question: str
    expected_answer: str  # Gold standard answer
    expected_sources: List[str]  # Expected citations
    category: str = "general"  # Category for grouping


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    test_case: TestCase
    actual_answer: str
    actual_sources: List[str]
    scores: Dict[str, float]
    passed: bool
    timestamp: str


class LegalBenchmark:
    """
    Benchmark suite for V-Legal Bot
    
    Metrics:
    - Semantic Similarity: Compare bot answer with gold standard
    - Context Precision: Check if retrieved sources are relevant
    - Citation Accuracy: Verify correct citations
    - Faithfulness: Ensure answer is grounded in retrieved context
    """
    
    def __init__(
        self,
        gold_dataset_path: Optional[str] = None,
        output_dir: str = "./benchmark_results"
    ):
        self.gold_dataset_path = gold_dataset_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_cases: List[TestCase] = []
        self.results: List[BenchmarkResult] = []
    
    def load_gold_dataset(self, filepath: str) -> None:
        """Load gold standard Q&A dataset"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.test_cases = [
            TestCase(
                question=item['question'],
                expected_answer=item['expected_answer'],
                expected_sources=item.get('expected_sources', []),
                category=item.get('category', 'general')
            )
            for item in data
        ]
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a single test case"""
        self.test_cases.append(test_case)
    
    def calculate_semantic_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """Calculate semantic similarity between two texts"""
        # Using embedding service for similarity
        from app.core.embeddings import get_embedding_service
        
        service = get_embedding_service()
        emb1 = service.embed_text(text1)
        emb2 = service.embed_text(text2)
        
        return service.similarity(emb1, emb2)
    
    def check_citations(
        self,
        answer: str,
        expected_sources: List[str]
    ) -> float:
        """Check if expected citations appear in the answer"""
        if not expected_sources:
            return 1.0
        
        found = 0
        for source in expected_sources:
            if source.lower() in answer.lower():
                found += 1
        
        return found / len(expected_sources)
    
    def evaluate_faithfulness(
        self,
        answer: str,
        context: str
    ) -> float:
        """
        Check if the answer is faithful to the context
        Simple heuristic: check keyword overlap
        """
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        
        if not answer_words:
            return 0.0
        
        overlap = answer_words.intersection(context_words)
        return len(overlap) / len(answer_words)
    
    def run_single_test(
        self,
        test_case: TestCase,
        rag_engine
    ) -> BenchmarkResult:
        """Run a single benchmark test"""
        # Query the RAG system
        response = rag_engine.query(test_case.question)
        
        # Calculate scores
        scores = {}
        
        # Semantic similarity with gold answer
        scores['semantic_similarity'] = self.calculate_semantic_similarity(
            response.answer,
            test_case.expected_answer
        )
        
        # Citation accuracy
        actual_sources = [s.reference for s in response.sources]
        scores['citation_accuracy'] = self.check_citations(
            response.answer,
            test_case.expected_sources
        )
        
        # Context used
        if response.sources:
            context = " ".join([s.content for s in response.sources])
            scores['faithfulness'] = self.evaluate_faithfulness(
                response.answer,
                context
            )
        else:
            scores['faithfulness'] = 0.0
        
        # Overall pass/fail
        passed = (
            scores['semantic_similarity'] >= 0.7 and
            scores['faithfulness'] >= 0.3
        )
        
        return BenchmarkResult(
            test_case=test_case,
            actual_answer=response.answer,
            actual_sources=actual_sources,
            scores=scores,
            passed=passed,
            timestamp=datetime.now().isoformat()
        )
    
    def run_benchmark(self, rag_engine) -> Dict[str, Any]:
        """Run all benchmark tests"""
        self.results = []
        
        for test_case in self.test_cases:
            print(f"Testing: {test_case.question[:50]}...")
            result = self.run_single_test(test_case, rag_engine)
            self.results.append(result)
        
        # Calculate aggregate metrics
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        
        avg_scores = {
            'semantic_similarity': sum(r.scores['semantic_similarity'] for r in self.results) / total,
            'citation_accuracy': sum(r.scores['citation_accuracy'] for r in self.results) / total,
            'faithfulness': sum(r.scores['faithfulness'] for r in self.results) / total,
        }
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': passed / total if total > 0 else 0,
            'average_scores': avg_scores,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save benchmark results to file"""
        if filename is None:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.output_dir / filename
        
        output = {
            'summary': {
                'total': len(self.results),
                'passed': sum(1 for r in self.results if r.passed),
                'timestamp': datetime.now().isoformat()
            },
            'results': [
                {
                    'question': r.test_case.question,
                    'expected': r.test_case.expected_answer[:200],
                    'actual': r.actual_answer[:200],
                    'scores': r.scores,
                    'passed': r.passed
                }
                for r in self.results
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return str(filepath)


# Sample gold dataset for testing
SAMPLE_GOLD_DATASET = [
    {
        "question": "Quyền sở hữu bao gồm những quyền gì?",
        "expected_answer": "Quyền sở hữu bao gồm quyền chiếm hữu, quyền sử dụng và quyền định đoạt tài sản của chủ sở hữu.",
        "expected_sources": ["Điều 158", "Bộ luật Dân sự"],
        "category": "civil_law"
    },
    {
        "question": "Thời hiệu khởi kiện vụ án dân sự là bao lâu?",
        "expected_answer": "Thời hiệu khởi kiện để yêu cầu Tòa án giải quyết vụ án dân sự là 03 năm kể từ ngày người có quyền yêu cầu biết hoặc phải biết quyền, lợi ích hợp pháp của mình bị xâm phạm.",
        "expected_sources": ["Điều 429", "Bộ luật Dân sự"],
        "category": "civil_law"
    }
]


def create_sample_gold_dataset(output_path: str = "./benchmark_results/gold_dataset.json"):
    """Create a sample gold dataset file"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(SAMPLE_GOLD_DATASET, f, ensure_ascii=False, indent=2)
    
    print(f"Created sample gold dataset: {output_path}")
    return output_path


if __name__ == "__main__":
    # Create sample dataset
    create_sample_gold_dataset()
    print("Sample gold dataset created. Edit it with your own test cases.")
