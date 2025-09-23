# Architecture Decision Records (ADR)

## ADR-001: 3-Engine Fallback vs 5-Engine Parallel Search

**Date**: 2025-09-22  
**Status**: Accepted  
**Decision Makers**: Development Team

### Context

The web search system needed to integrate Google Custom Search API and Brave Search API while maintaining reliability and cost efficiency. Two approaches were considered:

1. **5-Engine Parallel**: Query all engines simultaneously (Google, Brave, Bing, DuckDuckGo, Startpage)
2. **3-Engine Fallback**: Use 3 engine pairs with intelligent fallbacks

### Decision

We chose the **3-Engine Fallback System** with the following configuration:
- **Google API → Startpage fallback**: Primary API with web scraping backup
- **Bing → DuckDuckGo fallback**: Web scraping with alternative scraping backup  
- **Brave API (standalone)**: Direct API integration

### Rationale

#### Cost Efficiency
- **API calls are expensive**: Google CSE costs $5/1000 queries beyond free tier
- **Fallback reduces waste**: Only call backup when primary fails
- **Budget predictability**: Easier to estimate costs with controlled API usage

#### Rate Limiting Protection
- **API quotas are strict**: Google (100/day free), Brave (2000/month free)
- **Prevents quota exhaustion**: Fallback system preserves quota for when needed
- **Graceful degradation**: Service continues even when APIs exhausted

#### Quality Over Quantity
- **3 high-quality sources better than 5 mixed**: Focus on best results
- **Reduced noise**: Fewer duplicate results to filter
- **Better ranking**: Quality-first algorithm works better with fewer, better sources

#### Reliability & Resilience
- **Fallback system more robust**: If Google API fails, Startpage provides similar results
- **Reduced single points of failure**: Each engine pair provides redundancy
- **Faster recovery**: Immediate fallback vs waiting for all engines

#### Performance Benefits
- **Lower latency**: Fewer concurrent requests reduce network congestion
- **Reduced resource usage**: Less CPU/memory for result processing
- **Better caching**: More predictable access patterns

### Consequences

#### Positive
- ✅ **Cost effective**: Significant reduction in API costs
- ✅ **Quota efficient**: Longer service availability within free tiers
- ✅ **More reliable**: Fallback system provides better uptime
- ✅ **Easier monitoring**: Simpler to track and debug 3 engine pairs

#### Negative
- ❌ **Potentially fewer results**: Maximum results limited by engine pair performance
- ❌ **Complexity**: Fallback logic more complex than parallel execution

#### Mitigation
- **Result quality maintained**: Quality-first ranking ensures best results surface
- **Fallback testing**: Comprehensive testing ensures reliable fallback behavior
- **Monitoring**: Detailed logging tracks fallback usage and performance

### Implementation Notes

```python
# 3-Engine Fallback System
engines = [
    (google_api, startpage_fallback),    # API + Web scraping
    (bing_search, duckduckgo_fallback),  # Web scraping + Web scraping  
    (brave_api, None)                    # API only (standalone)
]
```

### Alternatives Considered

#### 5-Engine Parallel (Rejected)
- **Pros**: Maximum result diversity, simple implementation
- **Cons**: High API costs, quota exhaustion, resource intensive
- **Rejection reason**: Cost and quota concerns outweighed benefits

#### 2-Engine System (Rejected)  
- **Pros**: Simplest implementation, lowest cost
- **Cons**: Insufficient result diversity, limited fallback options
- **Rejection reason**: Insufficient coverage for production use

### Success Metrics

- **API cost reduction**: >60% reduction in API calls vs 5-engine parallel
- **Quota efficiency**: Service availability >95% within free tier limits
- **Result quality**: Maintained >90% result relevance scores
- **Reliability**: <1% fallback activation rate under normal conditions

### Review Date

This decision should be reviewed in 6 months (March 2026) based on:
- API cost analysis and budget impact
- User satisfaction with result quality and diversity
- System reliability and fallback usage patterns
- New search engine API availability and pricing
