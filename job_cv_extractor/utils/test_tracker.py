"""
Test Tracker Module

Tracks test runs of the CV extractor, recording URLs, status, errors, and results.
Stores data in JSON format for easy analysis and improvement.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
import threading


@dataclass
class TestRun:
    """Represents a single test run."""
    url: str
    timestamp: str
    status: str  # "success", "failure", "partial"
    platform_detected: Optional[str] = None
    extraction_method: Optional[str] = None
    resolved_url: Optional[str] = None
    was_resolved: bool = False
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    content_length: Optional[int] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    skills_extracted: Optional[int] = None
    responsibilities_extracted: Optional[int] = None
    ats_keywords_extracted: Optional[int] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class TestTracker:
    """Thread-safe test tracker that saves runs to JSON file."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.test_file = Path(__file__).parent.parent / "logs" / "test_runs.json"
                cls._instance.test_file.parent.mkdir(exist_ok=True)
                cls._instance.runs: List[TestRun] = []
                cls._instance.load_runs()
            return cls._instance
    
    def load_runs(self) -> None:
        """Load test runs from JSON file."""
        if self.test_file.exists():
            try:
                with open(self.test_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.runs = [
                        TestRun(**run_data) for run_data in data.get('runs', [])
                    ]
            except Exception as e:
                print(f"Error loading test runs: {e}")
                self.runs = []
        else:
            self.runs = []
    
    def save_runs(self) -> None:
        """Save test runs to JSON file."""
        try:
            with open(self.test_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'last_updated': datetime.now().isoformat(),
                    'total_runs': len(self.runs),
                    'runs': [run.to_dict() for run in self.runs]
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving test runs: {e}")
    
    def record_run(
        self,
        url: str,
        status: str,
        platform_detected: Optional[str] = None,
        extraction_method: Optional[str] = None,
        resolved_url: Optional[str] = None,
        was_resolved: bool = False,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        content_length: Optional[int] = None,
        tokens_used: Optional[int] = None,
        model_used: Optional[str] = None,
        job_title: Optional[str] = None,
        company: Optional[str] = None,
        skills_extracted: Optional[int] = None,
        responsibilities_extracted: Optional[int] = None,
        ats_keywords_extracted: Optional[int] = None,
        notes: Optional[str] = None
    ) -> TestRun:
        """Record a new test run."""
        with self._lock:
            run = TestRun(
                url=url,
                timestamp=datetime.now().isoformat(),
                status=status,
                platform_detected=platform_detected,
                extraction_method=extraction_method,
                resolved_url=resolved_url,
                was_resolved=was_resolved,
                error_message=error_message,
                error_type=error_type,
                content_length=content_length,
                tokens_used=tokens_used,
                model_used=model_used,
                job_title=job_title,
                company=company,
                skills_extracted=skills_extracted,
                responsibilities_extracted=responsibilities_extracted,
                ats_keywords_extracted=ats_keywords_extracted,
                notes=notes
            )
            self.runs.append(run)
            self.save_runs()
            return run
    
    def get_runs(self, limit: Optional[int] = None) -> List[TestRun]:
        """Get test runs, optionally limited to most recent N."""
        with self._lock:
            runs = list(self.runs)
            if limit:
                return runs[-limit:]
            return runs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about test runs."""
        with self._lock:
            total = len(self.runs)
            if total == 0:
                return {
                    'total_runs': 0,
                    'success_rate': 0.0,
                    'failure_rate': 0.0,
                    'platforms': {},
                    'error_types': {}
                }
            
            success = sum(1 for r in self.runs if r.status == 'success')
            failure = sum(1 for r in self.runs if r.status == 'failure')
            partial = sum(1 for r in self.runs if r.status == 'partial')
            
            platforms = {}
            for run in self.runs:
                if run.platform_detected:
                    platforms[run.platform_detected] = platforms.get(run.platform_detected, 0) + 1
            
            error_types = {}
            for run in self.runs:
                if run.error_type:
                    error_types[run.error_type] = error_types.get(run.error_type, 0) + 1
            
            return {
                'total_runs': total,
                'success': success,
                'failure': failure,
                'partial': partial,
                'success_rate': (success / total * 100) if total > 0 else 0.0,
                'failure_rate': (failure / total * 100) if total > 0 else 0.0,
                'platforms': platforms,
                'error_types': error_types
            }
    
    def clear_runs(self) -> None:
        """Clear all test runs."""
        with self._lock:
            self.runs = []
            self.save_runs()


# Global instance
tracker = TestTracker()
