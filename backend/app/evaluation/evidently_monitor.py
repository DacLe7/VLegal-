"""
Evidently AI Monitoring Module
Real-time monitoring for V-Legal Bot responses
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import json
from pathlib import Path


@dataclass
class MonitoringEvent:
    """A single monitoring event"""
    timestamp: str
    question: str
    answer: str
    sources: List[str]
    scores: Dict[str, float]
    alerts: List[str] = field(default_factory=list)


class LegalMonitor:
    """
    Real-time monitoring for V-Legal Bot
    
    Monitors:
    - Faithfulness: Answer grounded in retrieved context
    - Citation Check: Proper legal citations included
    - Toxic/Bias Detection: Appropriate language and neutrality
    - Response Quality: Length, coherence checks
    """
    
    def __init__(
        self,
        max_history: int = 1000,
        alert_threshold: float = 0.5
    ):
        self.max_history = max_history
        self.alert_threshold = alert_threshold
        self.events: deque = deque(maxlen=max_history)
        self.alerts_count: Dict[str, int] = {}
    
    def check_faithfulness(
        self,
        answer: str,
        context: str
    ) -> float:
        """
        Check if answer is faithful to the provided context
        
        Returns score between 0 and 1
        """
        if not answer or not context:
            return 0.0
        
        # Simple heuristic: keyword overlap ratio
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        
        # Filter out common words
        stopwords = {'là', 'và', 'của', 'có', 'được', 'trong', 'với', 'cho', 'này', 'đó'}
        answer_words -= stopwords
        context_words -= stopwords
        
        if not answer_words:
            return 0.0
        
        overlap = len(answer_words.intersection(context_words))
        return min(overlap / len(answer_words), 1.0)
    
    def check_citations(self, answer: str) -> float:
        """
        Check if answer contains proper legal citations
        
        Looks for patterns like:
        - "Điều X"
        - "Khoản Y"
        - "Luật/Bộ luật..."
        """
        import re
        
        citation_patterns = [
            r'Điều\s+\d+',
            r'Khoản\s+\d+',
            r'Điểm\s+[a-z]',
            r'Luật\s+[^,\.]+',
            r'Bộ luật\s+[^,\.]+',
            r'Nghị định\s+[^,\.]+',
        ]
        
        citations_found = 0
        for pattern in citation_patterns:
            if re.search(pattern, answer, re.IGNORECASE):
                citations_found += 1
        
        # Normalize to 0-1 range (expect at least 2 citation types)
        return min(citations_found / 2, 1.0)
    
    def check_toxic_content(self, text: str) -> float:
        """
        Check for potentially toxic or inappropriate content
        
        Returns score where higher is better (less toxic)
        """
        # Simple keyword-based check
        toxic_keywords = [
            'chết', 'giết', 'phạt tử hình', 'bạo lực',
            'khủng bố', 'ma túy', 'buôn người'
        ]
        
        text_lower = text.lower()
        toxic_count = sum(1 for kw in toxic_keywords if kw in text_lower)
        
        # These topics might appear in legal context, so be lenient
        if toxic_count == 0:
            return 1.0
        elif toxic_count <= 2:
            return 0.7  # Might be legitimate legal discussion
        else:
            return 0.3  # Multiple sensitive terms
    
    def check_bias(self, answer: str) -> float:
        """
        Check for potential bias in the answer
        
        Returns score where higher is better (less biased)
        """
        # Check for neutral language
        biased_phrases = [
            'chắc chắn phải', 'không thể nào', 'luôn luôn',
            'tuyệt đối', 'hoàn toàn'
        ]
        
        answer_lower = answer.lower()
        bias_count = sum(1 for phrase in biased_phrases if phrase in answer_lower)
        
        return max(1.0 - (bias_count * 0.2), 0.0)
    
    def check_response_quality(self, answer: str) -> float:
        """
        Check overall response quality
        
        Considers:
        - Length (not too short, not too long)
        - Has structure (paragraphs, lists)
        """
        if not answer:
            return 0.0
        
        length = len(answer)
        
        # Too short
        if length < 50:
            return 0.3
        
        # Too long
        if length > 5000:
            return 0.6
        
        # Check for structure
        has_structure = '\n' in answer or '•' in answer or '1.' in answer
        
        if has_structure:
            return 1.0
        elif length > 200:
            return 0.8
        else:
            return 0.6
    
    def monitor_response(
        self,
        question: str,
        answer: str,
        context: str,
        sources: List[str]
    ) -> MonitoringEvent:
        """
        Monitor a single response
        
        Returns MonitoringEvent with scores and any alerts
        """
        scores = {
            'faithfulness': self.check_faithfulness(answer, context),
            'citations': self.check_citations(answer),
            'toxicity': self.check_toxic_content(answer),
            'bias': self.check_bias(answer),
            'quality': self.check_response_quality(answer)
        }
        
        # Generate alerts for low scores
        alerts = []
        for metric, score in scores.items():
            if score < self.alert_threshold:
                alert_msg = f"Low {metric} score: {score:.2f}"
                alerts.append(alert_msg)
                self.alerts_count[metric] = self.alerts_count.get(metric, 0) + 1
        
        event = MonitoringEvent(
            timestamp=datetime.now().isoformat(),
            question=question,
            answer=answer[:500],  # Truncate for storage
            sources=sources,
            scores=scores,
            alerts=alerts
        )
        
        self.events.append(event)
        
        return event
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        if not self.events:
            return {
                'total_requests': 0,
                'average_scores': {},
                'alerts_count': {},
                'recent_alerts': []
            }
        
        # Calculate averages
        avg_scores = {}
        metrics = ['faithfulness', 'citations', 'toxicity', 'bias', 'quality']
        
        for metric in metrics:
            scores = [e.scores.get(metric, 0) for e in self.events]
            avg_scores[metric] = sum(scores) / len(scores) if scores else 0
        
        # Recent alerts
        recent_alerts = []
        for event in list(self.events)[-10:]:
            if event.alerts:
                recent_alerts.append({
                    'timestamp': event.timestamp,
                    'question': event.question[:50],
                    'alerts': event.alerts
                })
        
        return {
            'total_requests': len(self.events),
            'average_scores': avg_scores,
            'alerts_count': dict(self.alerts_count),
            'recent_alerts': recent_alerts
        }
    
    def export_logs(self, filepath: str) -> None:
        """Export monitoring logs to file"""
        logs = [
            {
                'timestamp': e.timestamp,
                'question': e.question,
                'scores': e.scores,
                'alerts': e.alerts
            }
            for e in self.events
        ]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)


# Singleton monitor instance
_monitor: Optional[LegalMonitor] = None


def get_monitor() -> LegalMonitor:
    """Get or create monitor singleton"""
    global _monitor
    if _monitor is None:
        _monitor = LegalMonitor()
    return _monitor


if __name__ == "__main__":
    # Test the monitor
    monitor = LegalMonitor()
    
    event = monitor.monitor_response(
        question="Quyền sở hữu là gì?",
        answer="Theo Điều 158 Bộ luật Dân sự 2015, quyền sở hữu bao gồm quyền chiếm hữu, quyền sử dụng và quyền định đoạt tài sản.",
        context="Điều 158. Quyền sở hữu...",
        sources=["Điều 158 Bộ luật Dân sự"]
    )
    
    print("Scores:", event.scores)
    print("Alerts:", event.alerts)
    print("\nDashboard:", monitor.get_dashboard_data())
