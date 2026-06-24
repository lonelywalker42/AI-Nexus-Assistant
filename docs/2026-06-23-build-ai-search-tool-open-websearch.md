---
title: "从零打造AI搜索工具：open-webSearch架构解析与实践"
date: 2026-06-23
categories: [AI, 搜索技术, 开源项目]
tags: [AI搜索, 多引擎聚合, 缓存优化, 并发控制, 错误恢复, TypeScript]
description: "深入解析open-webSearch的架构设计与实现细节，展示如何通过多引擎聚合、智能缓存和错误恢复机制，打造高性能的AI搜索工具。"
---

# 从零打造AI搜索工具：open-webSearch架构解析与实践

## 1. 背景与动机

在AI助手的开发中，搜索能力是核心基础设施之一。然而，现有的搜索API服务存在诸多痛点：

| 痛点 | 说明 | 影响 |
|------|------|------|
| 成本高昂 | 商业搜索API按请求计费 | 大规模使用成本不可控 |
| 单一数据源 | 仅依赖Google或Bing | 无法获取专业领域信息 |
| 网络延迟 | 跨国请求延迟高 | 用户体验下降 |
| 服务不稳定 | API限流、故障频繁 | 系统可靠性差 |

为了解决这些问题，我开发了**open-webSearch**——一个开源、免费、多引擎聚合的AI搜索工具。

## 2. 架构设计

### 2.1 整体架构

open-webSearch采用分层架构设计，将搜索引擎抽象为可插拔的适配器：

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Query Parser │  │   Cache     │  │ Rate Limiter│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                    Search Manager                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Concurrency │  │   Retry     │  │   Fallback  │         │
│  │   Control   │  │   Logic     │  │   Strategy  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                  Engine Adapter Layer                         │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│  │DuckDuck│ │  Bing  │ │ Brave  │ │Wiki    │ │ Arxiv  │    │
│  │  Go    │ │        │ │        │ │pedia   │ │        │    │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块划分

```typescript
src/
├── index.ts              // 主入口，启动服务
├── search/
│   ├── SearchManager.ts  // 搜索管理器，协调各引擎
│   ├── engines/          // 搜索引擎适配器
│   │   ├── DuckDuckGo.ts
│   │   ├── Bing.ts
│   │   ├── Brave.ts
│   │   ├── Wikipedia.ts
│   │   └── Arxiv.ts
│   └── types.ts          // 类型定义
├── cache/
│   └── CacheManager.ts   // 缓存管理
├── utils/
│   ├── rateLimiter.ts    // 限流器
│   ├── retry.ts          // 重试逻辑
│   └── logger.ts         // 日志工具
└── config/
    └── index.ts          // 配置管理
```

## 3. 核心实现

### 3.1 搜索引擎适配器模式

采用适配器模式统一不同搜索引擎的接口：

```typescript
// 基础搜索引擎接口
interface SearchEngine {
  name: string;
  search(query: string, options?: SearchOptions): Promise<SearchResult[]>;
  isAvailable(): Promise<boolean>;
}

// 搜索结果接口
interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source: string;
  publishedDate?: string;
  relevanceScore?: number;
}

// DuckDuckGo适配器实现
class DuckDuckGoEngine implements SearchEngine {
  name = 'duckduckgo';
  private baseUrl = 'https://duckduckgo.com/';

  async search(query: string, options?: SearchOptions): Promise<SearchResult[]> {
    const params = new URLSearchParams({
      q: query,
      format: 'json',
      no_html: '1',
      skip_disambig: '1'
    });

    const response = await fetch(`${this.baseUrl}?${params}`);
    const data = await response.json();

    return this.parseResults(data);
  }

  private parseResults(data: any): SearchResult[] {
    return data.results?.map((item: any) => ({
      title: item.title,
      url: item.url,
      snippet: item.snippet,
      source: this.name
    })) || [];
  }

  async isAvailable(): Promise<boolean> {
    try {
      const response = await fetch(this.baseUrl, { method: 'HEAD' });
      return response.ok;
    } catch {
      return false;
    }
  }
}
```

### 3.2 智能缓存机制

实现基于LRU策略的缓存系统，减少重复请求：

```typescript
class CacheManager {
  private cache: LRUCache<string, CacheEntry>;
  private defaultTTL: number;

  constructor(options: CacheOptions) {
    this.cache = new LRUCache({
      max: options.maxSize || 1000,
      ttl: options.ttl || 5 * 60 * 1000 // 默认5分钟
    });
    this.defaultTTL = options.ttl || 5 * 60 * 1000;
  }

  // 生成缓存键
  private generateKey(query: string, engines: string[]): string {
    const normalizedQuery = query.toLowerCase().trim();
    const engineKey = engines.sort().join(',');
    return `${normalizedQuery}:${engineKey}`;
  }

  // 获取缓存结果
  get(query: string, engines: string[]): SearchResult[] | null {
    const key = this.generateKey(query, engines);
    const entry = this.cache.get(key);
    
    if (entry && !this.isExpired(entry)) {
      return entry.results;
    }
    
    return null;
  }

  // 设置缓存
  set(query: string, engines: string[], results: SearchResult[]): void {
    const key = this.generateKey(query, engines);
    this.cache.set(key, {
      results,
      timestamp: Date.now(),
      ttl: this.defaultTTL
    });
  }

  private isExpired(entry: CacheEntry): boolean {
    return Date.now() - entry.timestamp > entry.ttl;
  }
}
```

### 3.3 并发控制与限流

实现令牌桶限流器，防止API滥用：

```typescript
class RateLimiter {
  private tokens: number;
  private maxTokens: number;
  private refillRate: number;
  private lastRefill: number;

  constructor(options: RateLimiterOptions) {
    this.maxTokens = options.maxTokens || 10;
    this.tokens = this.maxTokens;
    this.refillRate = options.refillRate || 1; // 每秒补充1个令牌
    this.lastRefill = Date.now();
  }

  async acquire(): Promise<void> {
    this.refill();

    if (this.tokens >= 1) {
      this.tokens -= 1;
      return;
    }

    // 等待令牌补充
    const waitTime = (1 - this.tokens) / this.refillRate * 1000;
    await new Promise(resolve => setTimeout(resolve, waitTime));
    
    this.refill();
    this.tokens -= 1;
  }

  private refill(): void {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    const tokensToAdd = elapsed * this.refillRate;
    
    this.tokens = Math.min(this.maxTokens, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }
}
```

### 3.4 并发搜索调度

实现智能的并发搜索调度器：

```typescript
class SearchManager {
  private engines: SearchEngine[];
  private cache: CacheManager;
  private rateLimiter: RateLimiter;
  private maxConcurrency: number;

  constructor(options: SearchManagerOptions) {
    this.engines = options.engines;
    this.cache = new CacheManager(options.cache);
    this.rateLimiter = new RateLimiter(options.rateLimit);
    this.maxConcurrency = options.maxConcurrency || 3;
  }

  async search(query: string, options: SearchOptions = {}): Promise<SearchResponse> {
    // 1. 检查缓存
    const engines = options.engines || this.engines.map(e => e.name);
    const cached = this.cache.get(query, engines);
    
    if (cached) {
      return {
        results: cached,
        fromCache: true,
        searchTime: 0
      };
    }

    // 2. 选择可用引擎
    const availableEngines = await this.getAvailableEngines(engines);
    
    // 3. 并发搜索
    const startTime = Date.now();
    const results = await this.concurrentSearch(query, availableEngines, options);
    
    // 4. 结果聚合与排序
    const aggregatedResults = this.aggregateResults(results);
    
    // 5. 缓存结果
    this.cache.set(query, engines, aggregatedResults);

    return {
      results: aggregatedResults,
      fromCache: false,
      searchTime: Date.now() - startTime
    };
  }

  private async concurrentSearch(
    query: string,
    engines: SearchEngine[],
    options: SearchOptions
  ): Promise<SearchResult[][]> {
    const chunks = this.chunkEngines(engines, this.maxConcurrency);
    const allResults: SearchResult[][] = [];

    for (const chunk of chunks) {
      const promises = chunk.map(async (engine) => {
        try {
          await this.rateLimiter.acquire();
          return await engine.search(query, options);
        } catch (error) {
          console.error(`Engine ${engine.name} failed:`, error);
          return [];
        }
      });

      const chunkResults = await Promise.all(promises);
      allResults.push(...chunkResults);
    }

    return allResults;
  }

  private chunkEngines(engines: SearchEngine[], size: number): SearchEngine[][] {
    const chunks: SearchEngine[][] = [];
    for (let i = 0; i < engines.length; i += size) {
      chunks.push(engines.slice(i, i + size));
    }
    return chunks;
  }

  private aggregateResults(results: SearchResult[][]): SearchResult[] {
    const flatResults = results.flat();
    
    // 去重
    const uniqueResults = this.deduplicate(flatResults);
    
    // 按相关性排序
    return uniqueResults.sort((a, b) => 
      (b.relevanceScore || 0) - (a.relevanceScore || 0)
    );
  }

  private deduplicate(results: SearchResult[]): SearchResult[] {
    const seen = new Set<string>();
    return results.filter(result => {
      const key = `${result.title}:${result.url}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }
}
```

### 3.5 错误恢复与断路器

实现断路器模式，防止级联故障：

```typescript
class CircuitBreaker {
  private failures: number = 0;
  private lastFailureTime: number = 0;
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  
  private readonly failureThreshold: number;
  private readonly resetTimeout: number;

  constructor(options: CircuitBreakerOptions) {
    this.failureThreshold = options.failureThreshold || 5;
    this.resetTimeout = options.resetTimeout || 60000; // 1分钟
  }

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (this.shouldAttemptReset()) {
        this.state = 'half-open';
      } else {
        throw new Error('Circuit breaker is open');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.failures = 0;
    this.state = 'closed';
  }

  private onFailure(): void {
    this.failures += 1;
    this.lastFailureTime = Date.now();

    if (this.failures >= this.failureThreshold) {
      this.state = 'open';
    }
  }

  private shouldAttemptReset(): boolean {
    return Date.now() - this.lastFailureTime >= this.resetTimeout;
  }

  getState(): string {
    return this.state;
  }
}
```

## 4. 性能优化策略

### 4.1 请求合并

对于相同查询的多个并发请求，合并为单次搜索：

```typescript
class RequestCoalescer {
  private pendingRequests = new Map<string, Promise<SearchResponse>>();

  async search(
    query: string,
    options: SearchOptions,
    searchFn: () => Promise<SearchResponse>
  ): Promise<SearchResponse> {
    const key = this.generateKey(query, options);
    
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key)!;
    }

    const promise = searchFn().finally(() => {
      this.pendingRequests.delete(key);
    });

    this.pendingRequests.set(key, promise);
    return promise;
  }

  private generateKey(query: string, options: SearchOptions): string {
    return `${query}:${JSON.stringify(options)}`;
  }
}
```

### 4.2 结果预取

基于用户行为预测，预取可能需要的搜索结果：

```typescript
class PrefetchManager {
  private searchHistory: string[] = [];
  private prefetchCache = new Map<string, Promise<SearchResponse>>();

  async prefetch(query: string, searchFn: () => Promise<SearchResponse>): Promise<void> {
    const similarQueries = this.findSimilarQueries(query);
    
    for (const similarQuery of similarQueries) {
      if (!this.prefetchCache.has(similarQuery)) {
        const promise = searchFn().catch(() => null);
        this.prefetchCache.set(similarQuery, promise);
      }
    }
  }

  private findSimilarQueries(query: string): string[] {
    // 基于搜索历史找到相似查询
    return this.searchHistory
      .filter(historical => this.calculateSimilarity(query, historical) > 0.7)
      .slice(0, 3);
  }

  private calculateSimilarity(a: string, b: string): number {
    // 简单的Jaccard相似度
    const setA = new Set(a.split(' '));
    const setB = new Set(b.split(' '));
    const intersection = new Set([...setA].filter(x => setB.has(x)));
    const union = new Set([...setA, ...setB]);
    return intersection.size / union.size;
  }
}
```

## 5. 与AI助手集成

### 5.1 作为AI工具调用

将搜索功能封装为AI可调用的工具：

```typescript
// 工具定义
const searchTool = {
  type: 'function',
  function: {
    name: 'web_search',
    description: '搜索互联网获取最新信息',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: '搜索查询词'
        },
        engines: {
          type: 'array',
          items: { type: 'string' },
          description: '指定搜索引擎（可选）'
        },
        maxResults: {
          type: 'number',
          description: '最大返回结果数'
        }
      },
      required: ['query']
    }
  }
};

// 工具处理函数
async function handleWebSearch(params: WebSearchParams): Promise<string> {
  const searchManager = new SearchManager({
    engines: [new DuckDuckGoEngine(), new BingEngine(), new BraveEngine()],
    cache: { maxSize: 1000, ttl: 5 * 60 * 1000 },
    rateLimit: { maxTokens: 10, refillRate: 1 },
    maxConcurrency: 3
  });

  const response = await searchManager.search(params.query, {
    engines: params.engines,
    maxResults: params.maxResults || 10
  });

  return JSON.stringify({
    results: response.results,
    searchTime: response.searchTime,
    fromCache: response.fromCache
  });
}
```

### 5.2 RAG增强对话

结合检索增强生成（RAG）提升对话质量：

```typescript
class RAGEnhancedChat {
  private searchManager: SearchManager;
  private llm: LLMClient;

  async chat(userMessage: string): Promise<string> {
    // 1. 分析用户意图，判断是否需要搜索
    const needsSearch = await this.analyzeIntent(userMessage);
    
    if (!needsSearch) {
      return this.llm.chat(userMessage);
    }

    // 2. 提取搜索关键词
    const searchQuery = await this.extractSearchQuery(userMessage);
    
    // 3. 搜索相关信息
    const searchResults = await this.searchManager.search(searchQuery);
    
    // 4. 构建增强上下文
    const context = this.buildContext(searchResults.results);
    
    // 5. 生成回答
    const enhancedPrompt = `
基于以下搜索结果回答用户问题：

搜索结果：
${context}

用户问题：${userMessage}

请提供准确、有帮助的回答，并引用相关来源。
`;

    return this.llm.chat(enhancedPrompt);
  }

  private async analyzeIntent(message: string): Promise<boolean> {
    // 判断是否需要实时信息
    const keywords = ['最新', '今天', '现在', '价格', '新闻', '天气'];
    return keywords.some(keyword => message.includes(keyword));
  }

  private async extractSearchQuery(message: string): Promise<string> {
    // 使用LLM提取搜索关键词
    const prompt = `从以下用户消息中提取最适合搜索引擎的查询词：\n${message}`;
    return this.llm.chat(prompt);
  }

  private buildContext(results: SearchResult[]): string {
    return results
      .slice(0, 5)
      .map((result, index) => 
        `[${index + 1}] ${result.title}\n${result.snippet}\n来源: ${result.url}`
      )
      .join('\n\n');
  }
}
```

## 6. 部署与配置

### 6.1 环境变量配置

```bash
# .env
PORT=3000
LOG_LEVEL=info
CACHE_MAX_SIZE=1000
CACHE_TTL=300000
RATE_LIMIT_MAX_TOKENS=10
RATE_LIMIT_REFILL_RATE=1
MAX_CONCURRENT_ENGINES=3
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RESET_TIMEOUT=60000
```

### 6.2 Docker部署

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY dist/ ./dist/
COPY .env ./

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### 6.3 启动脚本

```json
{
  "scripts": {
    "dev": "ts-node src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "jest",
    "lint": "eslint src/**/*.ts"
  }
}
```

## 7. 测试策略

### 7.1 单元测试

```typescript
describe('SearchManager', () => {
  let searchManager: SearchManager;

  beforeEach(() => {
    searchManager = new SearchManager({
      engines: [new MockEngine()],
      cache: { maxSize: 100, ttl: 5000 },
      rateLimit: { maxTokens: 5, refillRate: 1 },
      maxConcurrency: 2
    });
  });

  test('should return cached results on second search', async () => {
    const query = 'test query';
    
    const firstResponse = await searchManager.search(query);
    const secondResponse = await searchManager.search(query);
    
    expect(firstResponse.fromCache).toBe(false);
    expect(secondResponse.fromCache).toBe(true);
    expect(secondResponse.results).toEqual(firstResponse.results);
  });

  test('should handle engine failures gracefully', async () => {
    const failingEngine = new FailingEngine();
    const workingEngine = new WorkingEngine();
    
    const manager = new SearchManager({
      engines: [failingEngine, workingEngine],
      cache: { maxSize: 100, ttl: 5000 },
      rateLimit: { maxTokens: 5, refillRate: 1 },
      maxConcurrency: 2
    });

    const response = await manager.search('test');
    
    expect(response.results.length).toBeGreaterThan(0);
  });
});
```

### 7.2 集成测试

```typescript
describe('Integration: Search Flow', () => {
  test('should perform full search with caching', async () => {
    const searchManager = createSearchManager();
    
    // First search - fresh
    const response1 = await searchManager.search('TypeScript tutorial');
    expect(response1.fromCache).toBe(false);
    expect(response1.results.length).toBeGreaterThan(0);
    
    // Second search - cached
    const response2 = await searchManager.search('TypeScript tutorial');
    expect(response2.fromCache).toBe(true);
    expect(response2.searchTime).toBe(0);
  });
});
```

## 8. 监控与可观测性

### 8.1 性能指标

```typescript
class SearchMetrics {
  private metrics = {
    totalSearches: 0,
    cacheHits: 0,
    cacheMisses: 0,
    averageSearchTime: 0,
    engineFailures: new Map<string, number>()
  };

  recordSearch(response: SearchResponse): void {
    this.metrics.totalSearches++;
    
    if (response.fromCache) {
      this.metrics.cacheHits++;
    } else {
      this.metrics.cacheMisses++;
      this.updateAverageSearchTime(response.searchTime);
    }
  }

  recordEngineFailure(engineName: string): void {
    const current = this.metrics.engineFailures.get(engineName) || 0;
    this.metrics.engineFailures.set(engineName, current + 1);
  }

  getMetrics() {
    return {
      ...this.metrics,
      cacheHitRate: this.metrics.cacheHits / this.metrics.totalSearches
    };
  }

  private updateAverageSearchTime(newTime: number): void {
    const total = this.metrics.averageSearchTime * (this.metrics.cacheMisses - 1);
    this.metrics.averageSearchTime = (total + newTime) / this.metrics.cacheMisses;
  }
}
```

### 8.2 健康检查

```typescript
app.get('/health', async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    engines: {} as Record<string, string>
  };

  // 检查各引擎状态
  for (const engine of searchManager.engines) {
    try {
      const isAvailable = await engine.isAvailable();
      health.engines[engine.name] = isAvailable ? 'available' : 'unavailable';
    } catch (error) {
      health.engines[engine.name] = 'error';
    }
  }

  // 检查是否有可用引擎
  const availableEngines = Object.values(health.engines)
    .filter(status => status === 'available');
  
  if (availableEngines.length === 0) {
    health.status = 'unhealthy';
    return res.status(503).json(health);
  }

  res.json(health);
});
```

## 9. 最佳实践总结

| 实践 | 说明 | 收益 |
|------|------|------|
| 适配器模式 | 统一不同搜索引擎接口 | 易于扩展新引擎 |
| 智能缓存 | LRU策略 + TTL过期 | 减少重复请求，提升响应速度 |
| 并发控制 | 令牌桶限流 + 并发限制 | 防止API滥用，保持稳定性 |
| 断路器模式 | 自动检测故障，快速失败 | 防止级联故障，提升系统韧性 |
| 结果去重 | 基于标题+URL去重 | 避免重复结果，提升用户体验 |
| 请求合并 | 相同查询合并为单次搜索 | 减少资源消耗 |
| 监控指标 | 搜索次数、缓存命中率、引擎状态 | 便于性能调优和故障排查 |

## 10. 未来规划

- **语义搜索集成**：集成向量数据库，支持语义相似度搜索
- **搜索结果排序优化**：基于用户反馈和点击率优化排序算法
- **更多搜索引擎支持**：添加Google Scholar、PubMed等学术搜索引擎
- **分布式部署**：支持多实例部署，提升搜索吞吐量
- **搜索分析仪表盘**：可视化搜索性能指标和用户行为分析

## 11. 总结

open-webSearch通过模块化架构设计、智能缓存机制、并发控制和错误恢复策略，构建了一个高性能、高可用的AI搜索工具。其核心优势在于：

1. **多引擎聚合**：整合多个搜索引擎，提供更全面的搜索结果
2. **智能缓存**：减少重复请求，提升响应速度
3. **高可靠性**：断路器模式和重试机制确保系统稳定性
4. **易于扩展**：适配器模式支持快速集成新引擎
5. **AI友好**：天然支持RAG增强和工具调用

这个项目不仅解决了AI助手的搜索需求，也为构建高性能搜索服务提供了可复用的架构模式。开源社区可以基于此框架快速构建自己的搜索服务，满足不同场景的需求。

---

**项目地址**：[github.com/maikeps/open-webSearch](https://github.com/maikeps/open-webSearch)

**相关阅读**：
- [从零构建个人AI研究助手：技术选型与架构设计](./2026-06-22-build-personal-ai-research-assistant.md)
- [AI研究助手的系统架构设计](./2026-06-21-ai-research-assistant-architecture.md)
