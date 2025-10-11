# Multi-LLM Comparison Chat Design
**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/MULTI_LLM_CHAT_DESIGN.md
**Description:** Design document for multi-model comparison chat interface with local database storage
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2025-10-11

## Overview

A chat interface that allows querying multiple LLMs simultaneously and comparing their responses side-by-side, with all conversations stored in a local SQLite database.

## Features

### 1. Multi-Model Selection
- **Checkbox interface** to select 1-7 models to query simultaneously
- **Quick presets:**
  - "All Agentic Models" (qwen-coder-7b, hermes-3-llama-8b, llama-3.1-8b)
  - "Small & Fast" (phi3, smollm3)
  - "Large Context" (qwen2.5-32b)
  - "All Models"
- **Model status indicators:** Only show running models as available
- **Save custom presets** for frequently used combinations

### 2. Side-by-Side Comparison View

```
┌─────────────────────────────────────────────────────────────┐
│  Your Question: "Explain quantum computing"                 │
│  [Send to 3 selected models]                                │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ phi3        │ │ qwen-coder  │ │ hermes-3    │           │
│ │ ⏱ 2.3s      │ │ ⏱ 3.1s      │ │ ⏱ 2.8s      │           │
│ ├─────────────┤ ├─────────────┤ ├─────────────┤           │
│ │ Quantum     │ │ Quantum     │ │ Quantum     │           │
│ │ computing   │ │ computing   │ │ computing   │           │
│ │ uses...     │ │ leverages...│ │ is a...     │           │
│ │             │ │             │ │             │           │
│ │ [Copy]      │ │ [Copy]      │ │ [Copy]      │           │
│ │ [⭐ Rate]   │ │ [⭐ Rate]   │ │ [⭐ Rate]   │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 3. Response Features
- **Simultaneous queries:** Send to all selected models at once
- **Streaming responses:** Show responses as they arrive (async)
- **Response timing:** Track response time for each model
- **Token counting:** Show approximate tokens used
- **Rating system:** Rate each response (1-5 stars)
- **Copy button:** Easy copy of individual responses
- **Export comparison:** Export all responses to markdown/JSON

### 4. Local Database Storage

**Database:** SQLite (`~/Library/Application Support/llamaCPPManager/chat_history.db`)

**Schema:**

```sql
-- Conversations table
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT  -- JSON array of tags
);

-- Messages table (questions)
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Responses table (answers from models)
CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    model_name TEXT NOT NULL,
    content TEXT NOT NULL,
    response_time_ms INTEGER,
    tokens_used INTEGER,
    rating INTEGER,  -- 1-5 stars
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON: temperature, max_tokens, etc.
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

-- Model comparisons (aggregated insights)
CREATE TABLE comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    best_model TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

-- Search index for full-text search
CREATE VIRTUAL TABLE messages_fts USING fts5(content, tokenize='porter');
CREATE VIRTUAL TABLE responses_fts USING fts5(content, model_name, tokenize='porter');
```

### 5. Search & Analytics

**Search Capabilities:**
- Full-text search across all questions and answers
- Filter by model name
- Filter by date range
- Filter by rating
- Filter by response time
- Tag-based filtering

**Analytics Dashboard:**
```
Model Performance Summary:
┌───────────────┬─────────┬──────────┬────────────┐
│ Model         │ Queries │ Avg Time │ Avg Rating │
├───────────────┼─────────┼──────────┼────────────┤
│ phi3          │ 127     │ 2.1s     │ 4.2 ⭐     │
│ qwen-coder-7b │ 95      │ 3.4s     │ 4.5 ⭐     │
│ hermes-3      │ 103     │ 2.8s     │ 4.3 ⭐     │
└───────────────┴─────────┴──────────┴────────────┘

Top-Rated Responses by Model
Most Similar Responses (duplicate detection)
Response Time Distribution
```

## Implementation Plan

### Phase 1: Database Setup
**Files to create:**
- `src/llamacpp_manager/database.py` - SQLite wrapper and schema
- `src/llamacpp_manager/chat_storage.py` - Chat history storage API

**CLI commands:**
```bash
llamacpp-manager chat-history init       # Create database
llamacpp-manager chat-history search "quantum computing"
llamacpp-manager chat-history export --format json --output history.json
llamacpp-manager chat-history stats      # Show analytics
```

### Phase 2: Multi-Model Query Engine
**Files to create:**
- `src/llamacpp_manager/multi_query.py` - Parallel query handler

**Features:**
- Async/concurrent queries to multiple models
- Timeout handling (max 30s per model)
- Error handling (model crashes, network issues)
- Response streaming

**CLI command:**
```bash
llamacpp-manager compare "explain quantum computing" \
  --models phi3,qwen-coder-7b,hermes-3 \
  --save-to-history \
  --format table
```

### Phase 3: GUI Implementation
**Files to create:**
- `gui-macos/Sources/MultiChatView.swift` - Comparison chat UI
- `gui-macos/Sources/ChatHistoryView.swift` - Search and browse history
- `gui-macos/Sources/AnalyticsView.swift` - Model performance dashboard

**GUI additions:**
- New menu item: "Compare Models"
- New menu item: "Chat History"
- New menu item: "Model Analytics"

### Phase 4: Advanced Features
- **Export formats:** Markdown, JSON, CSV
- **Conversation branching:** Continue from any historical message
- **Model recommendations:** "Use phi3 for quick answers, qwen2.5-32b for complex reasoning"
- **Duplicate detection:** "You asked something similar on Oct 5th"
- **Batch processing:** Upload CSV of questions, get responses from all models

## User Workflow Examples

### Example 1: Quick Comparison
```
1. Click "Compare Models" in menu bar
2. Select: [✓] phi3  [✓] qwen-coder-7b  [✓] hermes-3
3. Type: "Write a Python function to parse JSON"
4. Click "Send to 3 models"
5. See 3 responses side-by-side in real-time
6. Rate each response
7. Copy the best one
8. All saved automatically to database
```

### Example 2: Research Session
```
1. Start new conversation: "Quantum Computing Research"
2. Add tags: #research #quantum #physics
3. Query all 7 models: "Explain superposition"
4. Compare responses, rate them
5. Ask follow-up: "How does entanglement work?"
6. Export entire conversation to markdown
7. Later: Search history for "quantum" → find all related conversations
```

### Example 3: Model Evaluation
```
1. Open "Model Analytics" dashboard
2. See: phi3 is fastest (2.1s avg) but hermes-3 has highest ratings (4.5⭐)
3. Filter: Show all queries about "code generation"
4. Insight: qwen-coder-7b performs best on code tasks
5. Save preset: "Code Tasks" → [qwen-coder-7b, hermes-3]
```

## Technical Considerations

### Performance
- **Concurrent queries:** Use `asyncio` to query models in parallel
- **Database indexing:** Full-text search indexes on content
- **Response caching:** Optional - cache responses for identical queries
- **Pagination:** Load history in chunks (50 conversations per page)

### Storage Estimates
- Average question: ~100 bytes
- Average response: ~500 bytes per model
- 1000 questions × 3 models = ~1.5MB
- Including metadata: ~2MB per 1000 queries

### Privacy & Security
- **Local only:** All data stays on device
- **No cloud sync:** Database is local SQLite file
- **Encryption:** Optional database encryption with SQLCipher
- **Export control:** User controls all data exports

## API Design

### Python API
```python
from llamacpp_manager.multi_query import MultiModelQuery
from llamacpp_manager.chat_storage import ChatStorage

# Query multiple models
query = MultiModelQuery()
results = await query.ask(
    question="Explain quantum computing",
    models=["phi3", "qwen-coder-7b", "hermes-3"],
    save_to_db=True,
    conversation_id=123
)

for result in results:
    print(f"{result.model}: {result.content}")
    print(f"Time: {result.response_time_ms}ms")

# Search history
storage = ChatStorage()
conversations = storage.search(
    query="quantum",
    models=["phi3"],
    min_rating=4,
    date_from="2025-10-01"
)
```

### Swift API (GUI)
```swift
// Query multiple models
let query = MultiModelQuery(service: cliService)
let results = try await query.ask(
    question: userInput,
    models: selectedModels,
    saveToHistory: true
)

// Display in comparison view
for result in results {
    ComparisonCard(
        model: result.modelName,
        response: result.content,
        responseTime: result.responseTimeMs
    )
}
```

## Benefits

### For Users
1. **Better decisions:** Compare multiple perspectives before choosing
2. **Model insights:** Learn which models excel at what tasks
3. **Knowledge base:** Build searchable archive of all interactions
4. **Efficiency:** Query multiple models at once instead of one-by-one
5. **Context:** See historical conversations, avoid repeating questions

### For Development
1. **Model evaluation:** Quantitative data on model performance
2. **Use case optimization:** Discover best models for specific tasks
3. **Quality tracking:** Monitor response quality over time
4. **Cost analysis:** Track token usage and response times

## Next Steps

**To implement this, I would:**

1. **Create the database schema** (5 minutes)
2. **Build the CLI comparison tool** (30 minutes)
3. **Add GUI comparison view** (1 hour)
4. **Implement search and analytics** (1 hour)
5. **Add export functionality** (30 minutes)

**Total implementation time:** ~3 hours

**Should I proceed with implementation?**

I can start with:
- Option A: CLI tool first (quick win, test functionality)
- Option B: GUI implementation first (visual interface)
- Option C: Database + CLI + GUI all together (complete feature)

Which would you prefer?
