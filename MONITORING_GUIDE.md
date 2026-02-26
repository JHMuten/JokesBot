# Joke Bot Monitoring & Analytics Guide

## Overview
This guide explains how to track user satisfaction and identify bot failures in production.

## 🎯 Key Metrics Tracked

### 1. **Query Success Metrics**
- **Total Queries**: Total number of user requests
- **Success Rate**: Percentage of queries that returned jokes
- **Failed Queries**: Queries that resulted in errors
- **No Results**: Queries where no matching jokes were found
- **NSFW Blocked**: Inappropriate requests that were blocked

### 2. **Performance Metrics**
- **Average Response Time**: Time taken to respond (in milliseconds)
- **Average Jokes per Query**: Number of jokes returned per request
- **LLM Failures**: Times when the AI model failed
- **ChromaDB Failures**: Times when the vector database failed

### 3. **User Satisfaction Metrics**
- **Average Rating**: User feedback ratings (1-5 scale)
- **Feedback Count**: Number of users who provided feedback
- **Low Satisfaction Queries**: Queries rated 2 or below

## 📊 Accessing Analytics

### Admin Dashboard
Visit: `http://localhost:5000/admin/dashboard`

Features:
- Real-time statistics
- Failed queries table
- Low satisfaction feedback
- Auto-refreshes every 30 seconds

### API Endpoints

**Get Statistics:**
```bash
GET /api/analytics/stats
```

**Get Failed Queries:**
```bash
GET /api/analytics/failed-queries
```

**Get Low Satisfaction Queries:**
```bash
GET /api/analytics/low-satisfaction
```

## 🚨 Identifying Failures

### 1. **Bot Can't Find Jokes**

**Indicators:**
- High "No Results" count
- Low success rate (<80%)
- Specific queries appearing in failed queries table

**Root Causes:**
- ChromaDB embeddings not matching user intent
- Limited joke collection (only 100 jokes)
- User asking for categories not in collection

**Solutions:**
- Review failed queries to identify patterns
- Add more jokes in underrepresented categories
- Improve ChromaDB search parameters
- Add synonyms/aliases for categories

### 2. **LLM Failures**

**Indicators:**
- LLM Failures count increasing
- Errors in failed queries table
- Slow response times

**Root Causes:**
- API rate limits hit
- Network timeouts
- Invalid API key
- OpenRouter service issues

**Solutions:**
- Check OpenRouter status page
- Verify API key is valid
- Implement retry logic
- Use fallback to ChromaDB-only search

### 3. **Low User Satisfaction**

**Indicators:**
- Average rating below 3.5
- Many thumbs down (rating = 1)
- Comments in low satisfaction table

**Root Causes:**
- Jokes don't match user intent
- Wrong jokes returned
- Response too slow
- Not enough jokes returned

**Solutions:**
- Review low-rated queries
- Improve prompt engineering
- Adjust ChromaDB search parameters
- Add more jokes to collection

## 📈 Monitoring Best Practices

### Daily Checks
1. Check success rate (should be >85%)
2. Review failed queries from last 24 hours
3. Check average response time (<2000ms)
4. Monitor LLM failure count

### Weekly Analysis
1. Analyze trends in query types
2. Identify most requested categories
3. Review user feedback comments
4. Update joke collection based on demand

### Monthly Review
1. Calculate month-over-month improvements
2. Identify seasonal patterns
3. Plan feature enhancements
4. Review and optimize costs

## 🔧 Troubleshooting Guide

### High Failure Rate

**Check:**
```python
# View recent errors
curl http://localhost:5000/api/analytics/failed-queries
```

**Common Issues:**
- ChromaDB not initialized
- API key expired
- Network connectivity
- jokes.json file missing

### Slow Response Times

**Check:**
```python
# View average response time
curl http://localhost:5000/api/analytics/stats | grep avg_response_time
```

**Optimization:**
- Reduce ChromaDB search results (n_results)
- Use faster LLM model
- Add caching layer
- Optimize prompt length

### Low User Satisfaction

**Check:**
```python
# View low-rated queries
curl http://localhost:5000/api/analytics/low-satisfaction
```

**Actions:**
- Analyze what users expected vs. what they got
- Improve joke categorization
- Add more diverse jokes
- Enhance LLM selection logic

## 📝 Analytics Data Structure

### Query Log Entry
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "event_type": "query",
  "user_message": "Tell me a physics joke",
  "response_type": "success",
  "jokes_count": 2,
  "response_time_ms": 850,
  "error": null
}
```

### Feedback Entry
```json
{
  "timestamp": "2024-01-15T10:31:00",
  "event_type": "feedback",
  "query_id": 1705315800000,
  "rating": 5,
  "comment": "Great joke!"
}
```

### Failure Entry
```json
{
  "timestamp": "2024-01-15T10:32:00",
  "event_type": "llm_failure",
  "error_type": "timeout",
  "error_message": "Request timeout after 10s",
  "fallback_used": "chromadb_direct"
}
```

## 🎯 Success Criteria

### Healthy Bot Metrics
- ✅ Success Rate: >85%
- ✅ Average Response Time: <2000ms
- ✅ Average Rating: >4.0/5
- ✅ LLM Failures: <5% of queries
- ✅ No Results: <10% of queries

### Warning Signs
- ⚠️ Success Rate: 70-85%
- ⚠️ Average Response Time: 2000-3000ms
- ⚠️ Average Rating: 3.0-4.0
- ⚠️ LLM Failures: 5-10%

### Critical Issues
- 🚨 Success Rate: <70%
- 🚨 Average Response Time: >3000ms
- 🚨 Average Rating: <3.0
- 🚨 LLM Failures: >10%

## 🔔 Setting Up Alerts

### Option 1: Log Monitoring
Monitor `analytics.json` file for patterns:
```bash
# Check for high failure rate
tail -f analytics.json | grep "error"
```

### Option 2: External Monitoring
Integrate with services like:
- Sentry (error tracking)
- DataDog (metrics)
- New Relic (APM)
- Prometheus + Grafana (custom dashboards)

### Option 3: Custom Alerts
Add to `analytics.py`:
```python
def check_health(self):
    stats = self.get_stats()
    if stats['success_rate'] < 70:
        send_alert("Critical: Success rate below 70%")
    if stats['avg_response_time_ms'] > 3000:
        send_alert("Warning: Slow response times")
```

## 📊 Sample Queries for Analysis

### Find Most Common Failed Queries
```python
from collections import Counter
import json

with open('analytics.json') as f:
    logs = json.load(f)

failed = [log['user_message'] for log in logs 
          if log.get('response_type') == 'no_results']
common = Counter(failed).most_common(10)
print(common)
```

### Calculate Peak Usage Times
```python
from datetime import datetime
from collections import defaultdict

with open('analytics.json') as f:
    logs = json.load(f)

hours = defaultdict(int)
for log in logs:
    if log.get('event_type') == 'query':
        hour = datetime.fromisoformat(log['timestamp']).hour
        hours[hour] += 1

print(sorted(hours.items(), key=lambda x: x[1], reverse=True))
```

## 🎓 Learning from Data

### Improve Joke Collection
- Identify underrepresented categories
- Add jokes for frequently requested topics
- Remove jokes that never get selected

### Optimize LLM Prompts
- Analyze queries where LLM selection was poor
- Test different prompt variations
- A/B test prompt changes

### Enhance User Experience
- Reduce response time for common queries
- Add quick responses for popular categories
- Implement caching for frequent requests

## 📞 Support & Maintenance

### Regular Maintenance Tasks
1. **Daily**: Check dashboard for anomalies
2. **Weekly**: Review and archive old logs
3. **Monthly**: Analyze trends and plan improvements
4. **Quarterly**: Full system audit and optimization

### When to Scale
- Queries per day > 10,000
- Response time consistently > 2s
- LLM costs becoming significant
- Need for real-time analytics

### Next Steps
- Implement A/B testing framework
- Add user session tracking
- Create automated reports
- Build ML model for query classification
