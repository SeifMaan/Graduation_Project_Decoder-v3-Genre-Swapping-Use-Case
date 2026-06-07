
# Adaptive Narrative Generation Framework

An AI-powered narrative generation framework capable of producing:

- Canon-consistent sequels
- Divergent “what-if” timelines
- Genre-swapped reinterpretations

using adaptive retrieval strategies and staged LLM orchestration.

---

# Features

## Multi-Stage Narrative Generation
The system separates storytelling into structured stages:

1. Context Retrieval
2. Context Compilation
3. Blueprint Generation
4. Chapter Outline Generation
5. Scene Prose Generation
6. Stateful Consistency Updates

This decomposition improves:
- narrative coherence
- controllability
- consistency
- long-form generation quality

---

# Supported Use Cases

## 1. Sequel Generation
Continues a narrative after canon.

### Retrieval Priorities
- unresolved threads
- relationship evolution
- ending states
- future hooks

---

## 2. What-If / Divergent Timeline
Branches the story from an altered canon event.

### Retrieval Priorities
- causal chains
- affected events
- branching consequences
- continuity anchors

---

## 3. Genre Swapping
Reinterprets a story in another genre while preserving core narrative structure.

### Supported Genres
- Romantic Comedy (RomCom)
- Fantasy
- Psychological Thriller

### Genre-Aware Retrieval
The system dynamically prioritizes different context depending on genre:
- relationships and banter for RomCom
- lore and worldbuilding for Fantasy
- paranoia and betrayal for Psychological Thriller

---

# Architecture

```text
User Input
    ↓
Adaptive Retrieval Engine
    ↓
Context Compilation
    ↓
Blueprint Generation
    ↓
Chapter Outline Generation
    ↓
Scene Prose Generation
    ↓
World State Update
```

---

# Project Structure

```text
project/
│
├── main.py
├── retrieval.py
├── generation.py
├── state.py
├── prompts.py
│
├── data/
│   └── retrieval.json
│
├── output/
│
└── README.md
```

---

# File Responsibilities

## main.py
Pipeline orchestration and execution flow.

---

## retrieval.py
Task-adaptive retrieval engine.

Handles:
- sequel retrieval
- what-if retrieval
- genre-aware retrieval weighting

---

## generation.py
Core narrative generation engine.

Handles:
- blueprint generation
- outline generation
- scene generation

---

## state.py
Narrative memory and consistency management.

Handles:
- world state tracking
- chapter memory
- continuity validation

---

## prompts.py
Centralized prompt engineering.

Handles:
- stage prompts
- genre conditioning
- prompt builders

---

# Technical Highlights

## AI Engineering
- Multi-stage LLM orchestration
- Genre-conditioned generation
- Controlled narrative generation

---

## Retrieval Systems
- Adaptive retrieval strategies
- Context prioritization
- Genre-aware retrieval

---

## Narrative Intelligence
- Canon-aware continuation
- Divergent timeline simulation
- Stateful narrative tracking

---

## Software Engineering
- Modular architecture
- Separation of concerns
- Rule-based validation
- Persistent generation state

---

# Example Use Cases

## Sequel Generation
```text
Continue the story after the original ending while focusing on unresolved political tensions.
```

---

## What-If
```text
What if the protagonist never betrayed the kingdom?
```

---

## Genre Swap
```text
Rewrite the story as a psychological thriller.
```

---

# Requirements

Install dependencies:

```bash
pip install requests
```

---

# Running the Project

```bash
python main.py
```

Then select:
- use case
- genre (if applicable)
- generation direction

---

# Future Improvements

- vector database retrieval
- semantic similarity ranking
- character voice embeddings
- dialogue consistency scoring
- multi-agent generation
- GUI interface
- streaming generation

---

# Academic Contribution

This project demonstrates:

- task-adaptive retrieval
- genre-conditioned generation
- staged narrative decomposition
- stateful long-form generation
- controllable AI storytelling pipelines

within a modular and explainable architecture suitable for research and experimentation.
