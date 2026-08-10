# Graph Report - .  (2026-08-10)

## Corpus Check
- 5 files · ~6,106 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 125 nodes · 159 edges · 17 communities (11 shown, 6 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.87)
- Token cost: 70,045 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Repo Ops & Gemini Provider Switch|Repo Ops & Gemini Provider Switch]]
- [[_COMMUNITY_IPO Pipeline & Review Analysis Interface|IPO Pipeline & Review Analysis Interface]]
- [[_COMMUNITY_Fraud Signal Scoring|Fraud Signal Scoring]]
- [[_COMMUNITY_Docker Services & Core Deps|Docker Services & Core Deps]]
- [[_COMMUNITY_CLAUDE.md Architecture Summary & Track Rationale|CLAUDE.md Architecture Summary & Track Rationale]]
- [[_COMMUNITY_Project Vision & Principles|Project Vision & Principles]]
- [[_COMMUNITY_Annotation, RAG & Roadmap (Track B)|Annotation, RAG & Roadmap (Track B)]]
- [[_COMMUNITY_Data Schema|Data Schema]]
- [[_COMMUNITY_CLAUDE.md Ground Rules|CLAUDE.md Ground Rules]]
- [[_COMMUNITY_IndoBERT vs Large-LLM Rationale|IndoBERT vs Large-LLM Rationale]]
- [[_COMMUNITY_Review Analysis AI Deps (Chroma, sentence-transformers)|Review Analysis AI Deps (Chroma, sentence-transformers)]]
- [[_COMMUNITY_FastAPI App Scaffold|FastAPI App Scaffold]]
- [[_COMMUNITY_Streamlit Frontend Scaffold|Streamlit Frontend Scaffold]]
- [[_COMMUNITY_CLAUDE.md Project Summary|CLAUDE.md Project Summary]]
- [[_COMMUNITY_CLAUDE.md Tech Stack Section|CLAUDE.md Tech Stack Section]]
- [[_COMMUNITY_Deployment Notes|Deployment Notes]]
- [[_COMMUNITY_Track B Retraining Loop|Track B Retraining Loop]]

## God Nodes (most connected - your core abstractions)
1. `Fraud Detection MVP (Online Shop)` - 12 edges
2. `Fraud Signal Weight Table` - 11 edges
3. `Data Schema Definitions` - 7 edges
4. `Annotation & Fine-Tuning Flow` - 7 edges
5. `Input-Process-Output Architecture` - 6 edges
6. `Review Analysis Result Entity` - 6 edges
7. `api Service` - 6 edges
8. `2026-08-10 Log: Re-graph Rule Relaxed + Gemini Provider Switch` - 6 edges
9. `Google Gemini API (Lapis 2 LLM)` - 6 edges
10. `STEP 2: Feature Extraction` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Rule-Based as Sanity Check on Fine-Tuned Model` --semantically_similar_to--> `Scoring Formula & Compound Overrides`  [INFERRED] [semantically similar]
  context/05-model-approach-mvp.md → CLAUDE.md
- `api Service` --shares_data_with--> `fastapi dependency`  [INFERRED]
  docker-compose.yml → requirements.txt
- `api Service` --shares_data_with--> `uvicorn[standard] dependency`  [INFERRED]
  docker-compose.yml → requirements.txt
- `.env Filled with GEMINI_API_KEY Checkpoint (pending)` --conceptually_related_to--> `GEMINI_API_KEY Environment Variable`  [INFERRED]
  PROGRESS.md → CLAUDE.md
- `Principle: AI as Additional Signal Layer, Not Decision Maker` --semantically_similar_to--> `Architecture Design Principles`  [INFERRED] [semantically similar]
  context/01-project-overview.md → context/02-architecture-ipo.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **LLM Provider Swap: Claude API to Google Gemini API** — requirements_google_genai_dependency, context_06_tech_stack_mvp_google_gemini_api, claude_lapis_2_google_gemini_api, progress_log_entry_2026_08_10_regraph_and_provider_switch [EXTRACTED 1.00]
- **Re-graph Rule Relaxed to Periodic Cadence** — claude_repository_ground_rules, claude_regraph_periodically, progress_log_entry_2026_08_10_regraph_and_provider_switch [EXTRACTED 1.00]
- **review_authenticity_score Contract as Track A/B Swap Seam** — claude_review_authenticity_score_contract, claude_two_parallel_tracks, context_05_model_approach_mvp_two_parallel_tracks, context_05_model_approach_mvp_rule_based_sanity_check [INFERRED 0.85]
- **review_authenticity_score Contract Consistent Across Pipeline** — context_02_architecture_ipo_review_authenticity_score_contract, context_03_data_schema_review_analysis_result_entity, context_08_review_analysis_module_get_review_authenticity_score_interface, context_09_track_b_finetuning_pipeline_get_review_authenticity_score_integration, context_04_fraud_signal_features_review_authenticity_score_signal [EXTRACTED 1.00]
- **Signal Rules Jointly Forming Final Score** — context_04_fraud_signal_features_score_price_deviation_func, context_04_fraud_signal_features_score_store_age_func, context_04_fraud_signal_features_score_rating_review_func, context_04_fraud_signal_features_score_review_authenticity_func, context_04_fraud_signal_features_baseline_scoring_formula [EXTRACTED 1.00]
- **Track B Fine-Tuning Pipeline Components** — context_09_track_b_finetuning_pipeline_annotation_flow, context_06_tech_stack_mvp_streamlit_annotation_tool, context_08_review_analysis_module_rag_knowledge_base, context_06_tech_stack_mvp_indobert_base, context_09_track_b_finetuning_pipeline_finetuning_technical_setup [INFERRED 0.85]

## Communities (17 total, 6 thin omitted)

### Community 0 - "Repo Ops & Gemini Provider Switch"
Cohesion: 0.14
Nodes (18): Dev Environment (Docker), GEMINI_API_KEY Environment Variable, Lapis 2: Google Gemini API Call, Planned Folder Structure, Gemini/GPT (General-Purpose Large LLMs), Data Layer, Recommended Folder Structure, Google Gemini API (Lapis 2 LLM) (+10 more)

### Community 1 - "IPO Pipeline & Review Analysis Interface"
Cohesion: 0.17
Nodes (16): Architecture Design Principles, Fixture Data Fallback (DATA_SOURCE=fixture), Input-Process-Output Architecture, review_authenticity_score Interface Contract, STEP 1: Live Scraping (Playwright), STEP 2: Feature Extraction, STEP 3: Scoring Engine (rule-based), STEP 4: Labeling (+8 more)

### Community 2 - "Fraud Signal Scoring"
Cohesion: 0.21
Nodes (15): Baseline Scoring Formula (50 + contributions), Compound Red Flags, is_official_store Signal, price_deviation Signal, rating Signal, response_rate Signal, review_authenticity_score Signal, review_count Signal (+7 more)

### Community 3 - "Docker Services & Core Deps"
Cohesion: 0.14
Nodes (14): Backend / Core Logic Stack, Frontend Interface (Streamlit), api Service, API_URL Environment Setting, DATA_SOURCE=fixture Environment Setting, Dockerfile.api, Dockerfile.frontend, .env File Reference (+6 more)

### Community 4 - "CLAUDE.md Architecture Summary & Track Rationale"
Cohesion: 0.18
Nodes (11): IPO Pipeline Architecture, Data Contracts, Review Analysis Module Flow, review_authenticity_score Contract, Scoring Formula & Compound Overrides, Two Parallel Tracks (Track A / Track B), Roadmap After Track B (V0/V1/V2), Rule-Based Core Decision Principle (+3 more)

### Community 5 - "Project Vision & Principles"
Cohesion: 0.22
Nodes (10): Principle: AI as Additional Signal Layer, Not Decision Maker, Fraud Detection MVP (Online Shop), Goal: Input-Process-Output Fraud Labeling System, Principle: No Fine-Tuning Without Labeled Data, Problem Statement: Opaque Store Credibility, Principle: Deterministic Rule-Based Label Decisions, Scope, Constraints & Assumptions, MVP Success Metrics (+2 more)

### Community 6 - "Annotation, RAG & Roadmap (Track B)"
Cohesion: 0.31
Nodes (9): Annotation Record Entity, Definition of Done (MVP & Track B), Track A Phases (Fase 0-6), Track B Phases (Fase B1-B4), Lapis 2: LLM Analysis, RAG Knowledge Base (Fraud Patterns), Annotation & Fine-Tuning Flow, Manual Annotation Rationale (+1 more)

### Community 7 - "Data Schema"
Cohesion: 0.48
Nodes (7): SQLite Cache for Review Analysis Result, Data Schema Definitions, Fraud Assessment Entity, Product Entity, Review Analysis Result Entity, Review Entity, Store Entity

### Community 8 - "CLAUDE.md Ground Rules"
Cohesion: 0.50
Nodes (5): Progress Tracked in Three Places (Rule 3), Read Through Graph By Default (Rule 1), Re-graph Periodically, Not After Every Edit (Rule 2), Repository Ground Rules, Progress Status Summary

### Community 9 - "IndoBERT vs Large-LLM Rationale"
Cohesion: 0.50
Nodes (5): IndoBERT, Why Not Fine-Tune Large LLM (Gemini/GPT), Explicitly Excluded from MVP Scope, IndoBERT Base Model (indobenchmark/indobert-base-p1), Track B Annotation & Fine-Tuning Stack

### Community 10 - "Review Analysis AI Deps (Chroma, sentence-transformers)"
Cohesion: 0.40
Nodes (5): Chroma Vector Store, Review Analysis Module Tools Table, sentence-transformers (multilingual embedding), chromadb dependency, sentence-transformers dependency

## Knowledge Gaps
- **36 isolated node(s):** `Problem Statement: Opaque Store Credibility`, `MVP Success Metrics`, `Scope, Constraints & Assumptions`, `Fixture Data Fallback (DATA_SOURCE=fixture)`, `SQLite Cache for Review Analysis Result` (+31 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Fraud Detection MVP (Online Shop)` connect `Project Vision & Principles` to `IPO Pipeline & Review Analysis Interface`, `Fraud Signal Scoring`, `Annotation, RAG & Roadmap (Track B)`, `Data Schema`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `Fraud Signal Weight Table` connect `Fraud Signal Scoring` to `IPO Pipeline & Review Analysis Interface`, `Project Vision & Principles`, `Annotation, RAG & Roadmap (Track B)`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `Google Gemini API (Lapis 2 LLM)` connect `Repo Ops & Gemini Provider Switch` to `Review Analysis AI Deps (Chroma, sentence-transformers)`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **What connects `Problem Statement: Opaque Store Credibility`, `Principle: Deterministic Rule-Based Label Decisions`, `Principle: No Fine-Tuning Without Labeled Data` to the rest of the system?**
  _44 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Repo Ops & Gemini Provider Switch` be split into smaller, more focused modules?**
  _Cohesion score 0.13725490196078433 - nodes in this community are weakly interconnected._
- **Should `Docker Services & Core Deps` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._