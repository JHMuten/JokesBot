import json
import os
from datetime import datetime
from collections import defaultdict

class Analytics:
    """Track user interactions and bot performance."""
    
    def __init__(self, log_file='analytics.json'):
        self.log_file = log_file
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """Create analytics file if it doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)
    
    def log_interaction(self, event_type, data):
        """Log a user interaction event."""
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            **data
        }
        
        logs.append(event)
        
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def log_query(self, user_message, response_type, jokes_returned, response_time_ms, error=None):
        """Log a user query and its outcome."""
        self.log_interaction('query', {
            'user_message': user_message,
            'response_type': response_type,  # 'success', 'no_results', 'error', 'nsfw_blocked'
            'jokes_count': jokes_returned,
            'response_time_ms': response_time_ms,
            'error': error
        })
    
    def log_feedback(self, query_id, rating, comment=None):
        """Log user feedback on a response."""
        self.log_interaction('feedback', {
            'query_id': query_id,
            'rating': rating,  # 1-5 stars or thumbs up/down
            'comment': comment
        })
    
    def log_llm_failure(self, error_type, error_message, fallback_used):
        """Log when the LLM fails."""
        self.log_interaction('llm_failure', {
            'error_type': error_type,
            'error_message': str(error_message),
            'fallback_used': fallback_used
        })
    
    def log_chromadb_failure(self, error_message):
        """Log when ChromaDB search fails."""
        self.log_interaction('chromadb_failure', {
            'error_message': str(error_message)
        })
    
    def get_stats(self):
        """Generate analytics statistics."""
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            return {}
        
        stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'no_results_queries': 0,
            'nsfw_blocked': 0,
            'llm_failures': 0,
            'chromadb_failures': 0,
            'avg_response_time_ms': 0,
            'avg_jokes_per_query': 0,
            'feedback_count': 0,
            'avg_rating': 0,
            'popular_categories': defaultdict(int),
            'common_failures': defaultdict(int)
        }
        
        response_times = []
        jokes_counts = []
        ratings = []
        
        for log in logs:
            event_type = log.get('event_type')
            
            if event_type == 'query':
                stats['total_queries'] += 1
                
                response_type = log.get('response_type')
                if response_type == 'success':
                    stats['successful_queries'] += 1
                elif response_type == 'error':
                    stats['failed_queries'] += 1
                elif response_type == 'no_results':
                    stats['no_results_queries'] += 1
                elif response_type == 'nsfw_blocked':
                    stats['nsfw_blocked'] += 1
                
                if log.get('response_time_ms'):
                    response_times.append(log['response_time_ms'])
                
                if log.get('jokes_count'):
                    jokes_counts.append(log['jokes_count'])
            
            elif event_type == 'feedback':
                stats['feedback_count'] += 1
                if log.get('rating'):
                    ratings.append(log['rating'])
            
            elif event_type == 'llm_failure':
                stats['llm_failures'] += 1
                error_type = log.get('error_type', 'unknown')
                stats['common_failures'][error_type] += 1
            
            elif event_type == 'chromadb_failure':
                stats['chromadb_failures'] += 1
        
        # Calculate averages
        if response_times:
            stats['avg_response_time_ms'] = sum(response_times) / len(response_times)
        
        if jokes_counts:
            stats['avg_jokes_per_query'] = sum(jokes_counts) / len(jokes_counts)
        
        if ratings:
            stats['avg_rating'] = sum(ratings) / len(ratings)
        
        # Calculate success rate
        if stats['total_queries'] > 0:
            stats['success_rate'] = (stats['successful_queries'] / stats['total_queries']) * 100
        else:
            stats['success_rate'] = 0
        
        return stats
    
    def get_failed_queries(self, limit=10):
        """Get recent failed queries for analysis."""
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            return []
        
        failed = [
            log for log in logs 
            if log.get('event_type') == 'query' 
            and log.get('response_type') in ['error', 'no_results']
        ]
        
        return failed[-limit:]
    
    def get_low_satisfaction_queries(self, threshold=2, limit=10):
        """Get queries with low user ratings."""
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            return []
        
        low_rated = [
            log for log in logs 
            if log.get('event_type') == 'feedback' 
            and log.get('rating', 5) <= threshold
        ]
        
        return low_rated[-limit:]
