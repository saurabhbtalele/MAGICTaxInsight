# Architecture Approach Document
## Intelligent Mortgage Document Processing Platform

| Field              | Detail                                      |
|--------------------|---------------------------------------------|
| **Version**        | 2.0                                         |
| **Date**           | March 4, 2026                               |
| **Status**         | Draft                                       |
| **Classification** | Internal - Confidential                     |
| **Domain**         | Mortgage Lending - Document Processing      |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Business Context & Problem Statement](#2-business-context--problem-statement)
3. [Goals & Success Criteria](#3-goals--success-criteria)
4. [Architecture Principles](#4-architecture-principles)
5. [System Overview](#5-system-overview)
6. [Detailed Architecture](#6-detailed-architecture)
7. [Classification Architecture — Azure DI Composed Ensemble](#7-classification-architecture--azure-di-composed-ensemble)
8. [Tax Document Extraction & MGIC Cash Flow Analysis](#8-tax-document-extraction--mgic-cash-flow-analysis)
9. [Multi-Bank Format Handling Strategy](#9-multi-bank-format-handling-strategy)
10. [Document Processing Pipeline](#10-document-processing-pipeline)
11. [Human-in-the-Loop Workflow](#11-human-in-the-loop-workflow)
12. [Technology Stack](#12-technology-stack)
13. [Data Architecture](#13-data-architecture)
14. [Integration Architecture](#14-integration-architecture)
15. [Security & Compliance](#15-security--compliance)
16. [Deployment Architecture](#16-deployment-architecture)
17. [Cost Optimization Strategy](#17-cost-optimization-strategy)
18. [Phased Delivery Roadmap](#18-phased-delivery-roadmap)
19. [Risks & Mitigations](#19-risks--mitigations)
20. [Appendix](#20-appendix)

---

## 1. Executive Summary

This document defines the architecture for an intelligent document processing platform designed for the mortgage lending industry. The platform automates the ingestion, classification, data extraction, validation, and summarization of mortgage-related documents such as bank statements, tax returns (W-2, 1099, 1040), pay stubs, appraisals, and identity documents.

The system adopts a **hybrid architecture** with the primary backend in **.NET** and specialized AI/ML microservices in **Python**, a **React** frontend, all deployed on **Microsoft Azure**. This hybrid approach leverages the strengths of both ecosystems: .NET for enterprise orchestration, API management, and business logic; Python for its mature ML/AI ecosystem, OCR libraries, and NLP tooling.

### Key Architecture Decisions Driven by Domain Analysis

**1. Classification at Scale (75+ Document Types)**
The system manages **75+ distinct document labels** across multiple loan types (Conventional, Common, FHA, NANQ, VALoan, Correspondent). Azure Document Intelligence's monolithic classifier has hard limits (2 GB training size, 25,000 pages). The architecture adopts a **Composed Classifier Ensemble** — splitting labels into 10 functional groups, each trained independently, then composed into a single Master Classifier endpoint. This provides 10x capacity headroom (20 GB, 250,000 pages) and enables incremental updates without full retraining.

**2. Tax Document Extraction & MGIC Cash Flow Analysis**
The primary extraction target is the **MGIC SAM Cash Flow Analysis Worksheet** — the industry-standard template used by underwriters to calculate qualifying income. This requires precise field-to-IRS-form-box mapping across 47+ MGIC rows covering Schedules B, C, D, E, F, Partnership (Form 1065), and S-Corporation (Form 1120-S) returns. Azure DI's prebuilt tax models cover ~95% of personal tax forms. The remaining ~5% (business entity forms: K-1, 1065, 1120-S) require **custom extraction models** or LLM-based extraction.

**3. Multi-Bank Format Diversity**
A single document type (e.g., "bank statement") can have vastly different layouts depending on the issuing institution. The architecture addresses this through a three-tier extraction strategy: template matching for known high-volume formats, adaptive layout-aware extraction for unseen formats, and LLM-based intelligent extraction as a fallback.

The system targets **85-90% straight-through processing** for standard documents while ensuring every extraction passes through a human review workflow before downstream consumption.

---

## 2. Business Context & Problem Statement

### 2.1 Industry Context

Mortgage loan processing requires collecting, verifying, and analyzing 50-100+ documents per loan application. Loan officers and underwriters spend significant time manually reviewing documents, extracting key financial figures, and cross-referencing data across multiple sources.

### 2.2 Core Problems

| # | Problem | Impact |
|---|---------|--------|
| 1 | Manual document classification | Loan officers spend 15-20 min per application sorting documents |
| 2 | Manual data extraction | Re-keying data from documents into LOS (Loan Origination System) is error-prone |
| 3 | Format diversity | Every bank, employer, and institution produces documents in unique layouts |
| 4 | Volume scaling | Processing capacity is linearly tied to headcount |
| 5 | Inconsistent review quality | Manual review quality varies by reviewer experience and fatigue |
| 6 | Compliance burden | Audit trails for document decisions are often incomplete |

### 2.3 Scale Assumptions

| Metric | Estimate |
|--------|----------|
| Loan applications per month | 500 - 5,000 |
| Documents per application | 50 - 100 |
| Total documents per month | 25,000 - 500,000 |
| Unique bank/institution formats | 500+ |
| Document types (labels) | 75+ across 6 loan types (Conventional, Common, FHA, NANQ, VALoan, Correspondent) |
| Functional classification groups | 10 clusters |
| Tax form types requiring extraction | 20+ (personal + business entity) |
| MGIC worksheet rows to populate | 47+ calculated fields |

---

## 3. Goals & Success Criteria

### 3.1 Primary Goals

1. **Automate document classification** with 95%+ accuracy on known document types
2. **Extract structured data** from mortgage documents with 90%+ field-level accuracy
3. **Handle multi-bank format diversity** without requiring per-bank custom templates for every institution
4. **Reduce manual processing time** by 60-70% per loan application
5. **Maintain full audit trail** for every document decision and data extraction
6. **Human-in-the-loop** review on 100% of extractions before downstream use

### 3.2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Classification accuracy | >= 95% | Correct doc type / total docs |
| Extraction accuracy (key fields) | >= 90% | Correct field values / total fields |
| Straight-through processing rate | >= 85% | Docs needing no manual correction / total docs |
| Average processing time per doc | < 30 seconds | Ingestion to review-ready |
| Human review time per doc | < 2 minutes | Avg time in review UI |
| System availability | 99.9% | Monthly uptime |

---

## 4. Architecture Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Open-source first, cloud-augmented** | Use open-source OCR and ML models as the default. Escalate to cloud AI services (Azure, Claude API) only for complex cases. Controls cost at scale. |
| 2 | **Hybrid .NET + Python** | .NET for orchestration, APIs, business logic. Python for ML/AI services. Communicate via REST/gRPC and message queues. |
| 3 | **Format-agnostic extraction** | Do not build per-bank templates as the primary strategy. Use adaptive, layout-aware extraction that generalizes across formats. Templates only for high-volume known formats as an optimization. |
| 4 | **Human-in-the-loop always** | No extraction result is consumed downstream without human review. Automation assists, humans approve. |
| 5 | **Confidence-driven routing** | Every AI decision includes a confidence score. Low-confidence items get routed differently than high-confidence ones. |
| 6 | **Feedback loop** | Human corrections feed back into model improvement. The system gets smarter over time. |
| 7 | **Event-driven processing** | Documents flow through the pipeline via events/queues, enabling async processing, retry, and scaling. |
| 8 | **Immutable audit trail** | Every action (classification, extraction, human edit, approval) is logged immutably. |

---

## 5. System Overview

### 5.1 High-Level Architecture Diagram

```
                         ┌─────────────────────────────┐
                         │      React Frontend          │
                         │  - Upload Portal             │
                         │  - Review Dashboard          │
                         │  - Admin / Analytics         │
                         └──────────┬──────────────────┘
                                    │ HTTPS
                         ┌──────────▼──────────────────┐
                         │   Azure API Management       │
                         │   (Gateway + Auth + Rate)     │
                         └──────────┬──────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
   ┌──────────▼────────┐ ┌────────▼─────────┐ ┌────────▼─────────┐
   │  .NET Core APIs   │ │  .NET Core APIs   │ │  .NET Core APIs   │
   │  Document Service  │ │  Workflow Service  │ │  Review Service   │
   │  - Upload/Store    │ │  - Orchestration   │ │  - Human Review   │
   │  - Metadata        │ │  - Routing         │ │  - Corrections    │
   │  - Status Tracking │ │  - Business Rules  │ │  - Approval       │
   └──────────┬────────┘ └────────┬─────────┘ └────────┬─────────┘
              │                    │                     │
              └────────────────────┼─────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    Azure Service Bus         │
                    │    (Message Queue / Topics)   │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────┬───────────┼───────────┬──────────────┐
         │             │           │           │              │
   ┌─────▼─────┐ ┌────▼────┐ ┌───▼────┐ ┌───▼─────┐ ┌──────▼──────┐
   │  Python   │ │ Python  │ │ Python │ │ Python  │ │  Python     │
   │  OCR      │ │ Classify│ │ Extract│ │ Validate│ │  Summarize  │
   │  Service  │ │ Service │ │ Service│ │ Service │ │  Service    │
   └───────────┘ └─────────┘ └────────┘ └─────────┘ └─────────────┘
         │             │           │           │              │
         └─────────────┴───────────┼───────────┴──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     Data Layer               │
                    │  Azure Blob   │  PostgreSQL  │
                    │  (Documents)  │  (Metadata)  │
                    │               │  Redis Cache │
                    └──────────────────────────────┘
```

### 5.2 Service Responsibility Matrix

| Service | Runtime | Responsibility |
|---------|---------|---------------|
| **Document Service** (.NET) | .NET 8 | Upload, storage, metadata, status tracking, document lifecycle |
| **Workflow Service** (.NET) | .NET 8 | Pipeline orchestration, routing rules, retry logic, SLA monitoring |
| **Review Service** (.NET) | .NET 8 | Human review queue, corrections capture, approval workflow |
| **Admin Service** (.NET) | .NET 8 | User management, configuration, analytics, reporting |
| **OCR Service** (Python) | Python 3.11+ | Text extraction from images/scans using Tesseract, PaddleOCR, Azure DI |
| **Classification Service** (Python) | Python 3.11+ | Document type identification using ML models |
| **Extraction Service** (Python) | Python 3.11+ | Structured data extraction using templates + LLM |
| **Validation Service** (Python) | Python 3.11+ | Cross-field and cross-document validation |
| **Summarization Service** (Python) | Python 3.11+ | LLM-based loan package summarization |

---

## 6. Detailed Architecture

### 6.1 .NET Backend (Orchestration Layer)

The .NET layer is the **system of record** and the **orchestrator**. It owns:

- **API surface** consumed by the React frontend
- **Document lifecycle management** (uploaded, queued, processing, review, approved, rejected)
- **Workflow engine** that drives documents through the pipeline
- **Business rules engine** for mortgage-specific logic
- **Human review queue management** and assignment
- **Audit logging** for every state transition
- **Integration** with downstream systems (LOS, CRM)

```
.NET Solution Structure:
├── src/
│   ├── DocProcess.API/                  # ASP.NET Core Web API
│   │   ├── Controllers/
│   │   │   ├── DocumentController.cs     # Upload, status, metadata
│   │   │   ├── ReviewController.cs       # Review queue, approve/reject
│   │   │   ├── WorkflowController.cs     # Pipeline status, retry
│   │   │   └── AdminController.cs        # Config, analytics
│   │   ├── Middleware/
│   │   │   ├── AuditMiddleware.cs        # Log all actions
│   │   │   └── TenantMiddleware.cs       # Multi-tenancy support
│   │   └── Program.cs
│   │
│   ├── DocProcess.Core/                 # Domain models, interfaces
│   │   ├── Models/
│   │   │   ├── Document.cs
│   │   │   ├── ExtractionResult.cs
│   │   │   ├── ReviewDecision.cs
│   │   │   └── LoanPackage.cs
│   │   ├── Interfaces/
│   │   │   ├── IDocumentRepository.cs
│   │   │   ├── IWorkflowEngine.cs
│   │   │   └── IPipelineService.cs
│   │   └── Enums/
│   │       ├── DocumentType.cs
│   │       ├── ProcessingStatus.cs
│   │       └── ConfidenceLevel.cs
│   │
│   ├── DocProcess.Infrastructure/       # Data access, external integrations
│   │   ├── Persistence/
│   │   │   ├── AppDbContext.cs
│   │   │   └── Repositories/
│   │   ├── BlobStorage/
│   │   │   └── AzureBlobService.cs
│   │   ├── Messaging/
│   │   │   └── ServiceBusPublisher.cs
│   │   └── ExternalServices/
│   │       └── PythonServiceClient.cs    # HTTP/gRPC client to Python services
│   │
│   ├── DocProcess.Workflow/             # Orchestration engine
│   │   ├── PipelineOrchestrator.cs
│   │   ├── RoutingEngine.cs
│   │   └── RetryPolicy.cs
│   │
│   └── DocProcess.Workers/             # Background workers (Azure Functions / Worker Service)
│       ├── DocumentQueueWorker.cs        # Picks docs from queue, calls Python services
│       ├── StatusUpdateWorker.cs
│       └── SlaMonitorWorker.cs
│
├── tests/
│   ├── DocProcess.API.Tests/
│   ├── DocProcess.Core.Tests/
│   └── DocProcess.Integration.Tests/
```

#### Key .NET Design Decisions

**Communication with Python services**: The .NET Workflow Service communicates with Python microservices through two channels:

1. **Azure Service Bus** (primary, async) — .NET publishes a message (e.g., `document.uploaded`), Python OCR service picks it up, processes, and publishes `ocr.completed`. This is the main pipeline flow.
2. **HTTP/gRPC** (secondary, sync) — For real-time queries like "re-extract this field" from the review UI, .NET calls Python services directly.

```
Pipeline Flow (async, queue-based):

  .NET Document Service
       │
       ▼ publishes: document.uploaded
  ─────────────────────────────
  Azure Service Bus
  ─────────────────────────────
       │
       ▼ subscribes: document.uploaded
  Python OCR Service
       │
       ▼ publishes: ocr.completed
  ─────────────────────────────
  Azure Service Bus
  ─────────────────────────────
       │
       ▼ subscribes: ocr.completed
  Python Classification Service
       │
       ▼ publishes: classification.completed
  ... continues through pipeline ...
```

### 6.2 Python AI/ML Layer (Intelligence Layer)

The Python layer provides all ML/AI capabilities as independent microservices. Each service is containerized and deployed on Azure Container Apps or AKS.

```
Python Services Structure:
├── services/
│   ├── ocr-service/
│   │   ├── app/
│   │   │   ├── main.py                  # FastAPI app
│   │   │   ├── ocr_engine.py            # OCR orchestration
│   │   │   ├── engines/
│   │   │   │   ├── tesseract_engine.py   # Tesseract wrapper
│   │   │   │   ├── paddle_engine.py      # PaddleOCR wrapper
│   │   │   │   └── azure_di_engine.py    # Azure Document Intelligence client
│   │   │   ├── preprocessing/
│   │   │   │   ├── deskew.py
│   │   │   │   ├── denoise.py
│   │   │   │   └── enhance.py
│   │   │   └── models/
│   │   │       └── schemas.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── classification-service/
│   │   ├── app/
│   │   │   ├── main.py                  # FastAPI app
│   │   │   ├── classifier.py            # Classification orchestration
│   │   │   ├── models/
│   │   │   │   ├── text_classifier.py    # Text-based (fine-tuned transformer)
│   │   │   │   ├── layout_classifier.py  # Layout/visual features
│   │   │   │   └── ensemble.py           # Combine signals
│   │   │   └── training/
│   │   │       ├── train.py
│   │   │       └── evaluate.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── extraction-service/
│   │   ├── app/
│   │   │   ├── main.py                  # FastAPI app
│   │   │   ├── extraction_engine.py     # Extraction orchestration
│   │   │   ├── strategies/
│   │   │   │   ├── template_strategy.py  # Known-format template matching
│   │   │   │   ├── layout_strategy.py    # Layout-aware adaptive extraction
│   │   │   │   └── llm_strategy.py       # LLM-based extraction (Claude API)
│   │   │   ├── templates/
│   │   │   │   ├── template_registry.py  # Template management
│   │   │   │   └── known_formats/        # Per-bank templates (optimization)
│   │   │   ├── post_processing/
│   │   │   │   ├── normalizer.py         # Date, currency, name normalization
│   │   │   │   └── validator.py          # Field-level validation
│   │   │   └── models/
│   │   │       └── schemas.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── validation-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── cross_field_validator.py  # Within-document validation
│   │   │   ├── cross_doc_validator.py    # Across-document validation
│   │   │   └── rules/
│   │   │       ├── income_rules.py
│   │   │       ├── asset_rules.py
│   │   │       └── identity_rules.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── summarization-service/
│       ├── app/
│       │   ├── main.py
│       │   ├── summarizer.py
│       │   └── prompts/
│       │       ├── loan_summary.py
│       │       └── discrepancy_report.py
│       ├── Dockerfile
│       └── requirements.txt
│
├── shared/
│   ├── messaging/                       # Shared Service Bus client
│   │   └── azure_sb_client.py
│   ├── storage/                         # Shared Blob Storage client
│   │   └── blob_client.py
│   └── observability/                   # Shared logging, metrics
│       └── telemetry.py
```

### 6.3 React Frontend

```
React Frontend Structure:
├── src/
│   ├── pages/
│   │   ├── Upload/                      # Document upload portal
│   │   │   ├── UploadPage.tsx
│   │   │   ├── DragDropZone.tsx
│   │   │   └── UploadProgress.tsx
│   │   │
│   │   ├── Review/                      # Human review workspace
│   │   │   ├── ReviewDashboard.tsx       # Queue of items to review
│   │   │   ├── ReviewWorkspace.tsx       # Side-by-side review UI
│   │   │   ├── DocumentViewer.tsx        # Original document with highlights
│   │   │   ├── ExtractionPanel.tsx       # Extracted fields (editable)
│   │   │   ├── ConfidenceIndicator.tsx   # Visual confidence scores
│   │   │   └── ApprovalActions.tsx       # Approve / Reject / Escalate
│   │   │
│   │   ├── LoanPackage/                 # Loan-level view
│   │   │   ├── LoanOverview.tsx          # All docs for a loan
│   │   │   ├── SummaryView.tsx           # AI-generated summary
│   │   │   └── DiscrepancyReport.tsx     # Flagged issues
│   │   │
│   │   └── Admin/                       # Administration
│   │       ├── AnalyticsDashboard.tsx    # Processing metrics
│   │       ├── TemplateManager.tsx       # Manage extraction templates
│   │       └── UserManagement.tsx
│   │
│   ├── components/
│   │   ├── PDFViewer/                   # PDF rendering with annotation
│   │   ├── FieldHighlight/              # Highlight extracted regions on doc
│   │   └── ConfidenceBadge/             # Color-coded confidence display
│   │
│   └── services/
│       └── api.ts                       # API client to .NET backend
```

---

## 7. Classification Architecture — Azure DI Composed Ensemble

### 7.1 The Scalability Problem

The current classification infrastructure uses monolithic custom models containing ~75 document types. These models have hit Azure Document Intelligence service-level limits:

| Constraint | Azure DI Limit | Current Usage | Remaining Headroom |
|-----------|---------------|---------------|-------------------|
| Training data size | 2 GB per classifier | ~1.8 GB | ~10% |
| Total page count | 25,000 pages per classifier | ~22,000 | ~12% |

Under this monolithic structure:
- **Cannot add new document types** without exceeding limits
- **Cannot add training samples** to improve accuracy on existing labels
- **Any single-label fix requires full retraining** of the entire 75-label model (high risk, high latency)
- **6 separate monolithic models** exist (Conventional, Common, FHA, NANQ, VALoan, Correspondent) each approaching these limits

### 7.2 Solution: Composed Classifier Ensembles

The architecture uses Azure DI's **Composed Classifier** mechanism (v4.0 GA) to create an ensemble of specialized sub-models managed as a single logical unit.

```
┌──────────────────────────────────────────────────────────────┐
│                   MASTER CLASSIFIER                           │
│            (Single Model ID / Single Endpoint)                │
│                                                               │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐    │
│  │ Grp 01    │ │ Grp 02    │ │ Grp 03    │ │ Grp 04    │    │
│  │ Application│ │ Appraisal │ │ Income    │ │ Income    │    │
│  │ & Initial  │ │ & Value   │ │ (Employ)  │ │ (Tax/Biz) │    │
│  │ 9 labels   │ │ 9 labels  │ │ 5 labels  │ │ 6 labels  │    │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘    │
│                                                               │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐    │
│  │ Grp 05    │ │ Grp 06    │ │ Grp 07    │ │ Grp 08    │    │
│  │ Identity  │ │ Assets &  │ │ Compliance│ │ Purchase  │    │
│  │ & Eligib  │ │ Banking   │ │ & Legal   │ │ Contract  │    │
│  │ 9 labels  │ │ 3 labels  │ │ 9 labels  │ │ 4 labels  │    │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘    │
│                                                               │
│  ┌───────────┐ ┌───────────┐                                 │
│  │ Grp 09    │ │ Grp 10    │  Document ─► Master Classifier  │
│  │ Closing & │ │ Property &│  ─► Routes across sub-models    │
│  │ Settlement│ │ Insurance │  ─► Returns: label + confidence  │
│  │ 9 labels  │ │ 6 labels  │                                 │
│  └───────────┘ └───────────┘                                 │
└──────────────────────────────────────────────────────────────┘
```

**Architectural Mechanism:**
- **Unified Model ID**: A single "Master Classifier" ID acts as the primary endpoint
- **Intelligent Routing**: Upon document submission, the Master Classifier orchestrates routing across constituent sub-classifiers
- **Label Integrity**: Returns original label strings (e.g., `paystubs`, `w2_1099`). Downstream systems see no change
- **Transparent Integration**: The composed model response structure is identical to a single custom model

### 7.3 Functional Group Mapping (75 Labels → 10 Groups)

| Group | Cluster | Labels | Sub-Model ID Pattern |
|-------|---------|--------|---------------------|
| **Grp 01** | Application & Initial | `app_1003_init`, `app_1008`, `ack_intent`, `elec_consent`, `borrower_auth`, `2015-service_provider`, `loan_toolkit`, `lsm_init_disc`, `app_scif` | `conv_grp01_app_v01_YYYYMMDD` |
| **Grp 02** | Appraisal & Valuation | `appr`, `appr_1004d`, `appr_air_cert`, `appr_invoice`, `appr_pod`, `appr_rov_disc`, `appr_rov_req`, `appr_ssr`, `comp_report` | `conv_grp02_val_v01_YYYYMMDD` |
| **Grp 03** | Income (Employment) | `paystubs`, `w2_1099`, `written_voe`, `income_uw_analysis`, `income-uw-analysis` | `conv_grp03_emp_v01_YYYYMMDD` |
| **Grp 04** | Income (Tax/Business) | `tax_returns_business`, `tax-returns-personal`, `curr_pl_bs`, `cpa_cert`, `4506c-corelogic`, `irs-4506-copy-processed` | `conv_grp04_tax_v01_YYYYMMDD` |
| **Grp 05** | Identity & Eligibility | `drivers_lic`, `passport`, `ead_card`, `perm_alien`, `res_alien`, `ssn_card`, `form_ssa89`, `patriot_act_disc`, `credit_report` | `conv_grp05_ids_v01_YYYYMMDD` |
| **Grp 06** | Assets & Banking | `bank_statements`, `mortgage_stmt`, `title_emd` | `conv_grp06_ast_v01_YYYYMMDD` |
| **Grp 07** | Compliance & Legal | `anti_steering`, `ecoa`, `loan-prd-adv`, `disc_borr_cert`, `nmls_check`, `homebuyers_counsel_cert`, `homeowner_counsel`, `homeowners_counseller`, `internal_lon_ids_comp_cert` | `conv_grp07_leg_v01_YYYYMMDD` |
| **Grp 08** | Purchase Contract | `purchasecontract-contract`, `purchasecontract-addendum`, `purchasecontract-counter`, `purchasecontract-disclosure` | `conv_grp08_con_v01_YYYYMMDD` |
| **Grp 09** | Closing & Settlement | `title_cpl`, `title_prelim_commit`, `title_tax_cert`, `title_wiring`, `disc_closing_cd`, `coc_cd`, `fee_sheet_cd`, `hud1_settlement_stmt`, `sec_lock_conf` | `conv_grp09_set_v01_YYYYMMDD` |
| **Grp 10** | Property & Insurance | `insurance`, `flood_cert`, `fema_disaster`, `rep-cost-est`, `app_geocoding`, `app_ldp_gsa`, `desktop_uw`, `loan_estimate`, `coc_le`, `fee_sheet_le`, `agent_info` | `conv_grp10_prop_v01_YYYYMMDD` |

### 7.4 Capacity Gains

| Metric | Monolithic | Composed Ensemble | Improvement |
|--------|-----------|-------------------|-------------|
| Training data capacity | 2 GB | 20 GB (10 x 2 GB) | **10x** |
| Page count capacity | 25,000 | 250,000 (10 x 25K) | **10x** |
| Retraining blast radius | All 75 labels | 1 group (~7 labels) | **~90% reduction** |
| Retraining time | ~4 hours | ~25 minutes per group | **~90% faster** |
| Adding new doc type | Risky (near limits) | Safe (group has headroom) | **Unblocked** |

### 7.5 Blob Storage Architecture for Training Data

```
conventional_samples/                    # Root container
├── income/
│   ├── paystubs/                        # Label folders (leaf nodes)
│   ├── w2_1099/
│   ├── tax-returns-personal/
│   ├── tax_returns_business/
│   ├── bank_statements/
│   ├── written_voe/
│   ├── curr_pl_bs/
│   ├── cpa_cert/
│   └── mortgage_stmt/
├── identity/
│   ├── drivers_lic/
│   ├── ssn_card/
│   ├── passport/
│   ├── ead_card/
│   ├── perm_alien/
│   └── res_alien/
├── appraisal/
│   ├── appr/
│   ├── appr_1004d/
│   ├── appr_invoice/
│   ├── appr_air_cert/
│   ├── appr_ssr/
│   ├── appr_rov_req/
│   ├── appr_rov_disc/
│   ├── appr_pod/
│   ├── rep-cost-est/
│   └── comp_report/
├── disclosures/
│   ├── disc_borr_cert/
│   ├── disc_closing_cd/
│   ├── ecoa/
│   ├── anti_steering/
│   ├── loan_toolkit/
│   ├── elec_consent/
│   ├── loan-prd-adv/
│   └── lsm_init_disc/
├── fees_closing/
│   ├── fee_sheet_le/
│   ├── fee_sheet_cd/
│   ├── loan_estimate/
│   ├── hud1_settlement_stmt/
│   ├── coc_le/
│   ├── coc_cd/
│   └── sec_lock_conf/
├── title/
│   ├── title_prelim_commit/
│   ├── title_cpl/
│   ├── title_emd/
│   ├── title_tax_cert/
│   └── title_wiring/
├── purchase_contract/
│   ├── purchasecontract-contract/
│   ├── purchasecontract-disclosure/
│   ├── purchasecontract-addendum/
│   └── purchasecontract-counter/
├── application/
│   ├── app_1003_init/
│   ├── app_geocoding/
│   ├── app_ldp_gsa/
│   ├── app_scif/
│   ├── app_1008/
│   ├── form_ssa89/
│   ├── irs-4506-copy-processed/
│   └── 4506c-corelogic/
├── underwriting/
│   ├── credit_report/
│   ├── desktop_uw/
│   ├── income_uw_analysis/
│   ├── nmls_check/
│   ├── patriot_act_disc/
│   └── internal_lon_ids_comp_cert/
└── insurance_flood/
    ├── flood_cert/
    ├── fema_disaster/
    ├── insurance/
    ├── homeowner_counsel/
    ├── homebuyers_counsel_cert/
    └── homeowners_counseller/
```

### 7.6 Ensemble Training API

```python
# New API endpoint for group-specific training
# POST /api/TrainEnsembleClassifier

class EnsembleClassifierTrainer:
    """
    Trains sub-classifiers by functional group.
    Reuses existing OCR + build lifecycle from monolithic trainer.
    """

    ENSEMBLE_GROUP_MAP = {
        "identity":         ["drivers_lic", "ssn_card", "passport", "ead_card", ...],
        "income":           ["paystubs", "w2_1099", "tax_returns_business", ...],
        "appraisal":        ["appr", "appr_1004d", "appr_invoice", ...],
        "disclosures":      ["disc_borr_cert", "disc_closing_cd", "ecoa", ...],
        "fees_closing":     ["fee_sheet_le", "fee_sheet_cd", "loan_estimate", ...],
        "title":            ["title_prelim_commit", "title_cpl", "title_emd", ...],
        "purchase_contract":["purchasecontract-contract", "purchasecontract-disclosure", ...],
        "application":      ["app_1003_init", "app_geocoding", "app_ldp_gsa", ...],
        "underwriting":     ["credit_report", "desktop_uw", "income_uw_analysis", ...],
        "insurance_flood":  ["flood_cert", "fema_disaster", "insurance", ...],
    }

    def __init__(self, loan_type: str, sync_prod: bool, group: str = None):
        self.loan_type = loan_type
        self.sync_prod = sync_prod
        self.group = group  # If None, trains all groups

    def train_group(self, group_name: str, labels: list[str]):
        """
        Reuses existing OCR + build flow (train_labels())
        scoped ONLY to the labels in this functional cluster.
        Source path: conventional_samples/{group_name}/{label_name}
        """
        source_uri = f"conventional_samples/{group_name}"
        # ... existing OCR + documentClassifiers:build logic ...

    def train_all_groups(self):
        """Iterates through all groups and trains each independently."""
        for group_name, labels in self.ENSEMBLE_GROUP_MAP.items():
            self.train_group(group_name, labels)
```

### 7.7 Training State Tracking

The `trainingState` Azure Table Storage is extended with a `Group` column:

| Column | Example Value |
|--------|--------------|
| PartitionKey | `ensemble_conventional_income_20260302143022` |
| Status | `Completed` |
| Labels | `["paystubs", "w2_1099", "tax_returns_business", ...]` |
| Group | `income` |
| ModelId | `conv_grp03_emp_v01_20260302` |

### 7.8 Composition & Rollout Plan

```
Phase 1: Conventional + Common models
    ├── Train 10 sub-classifiers per loan type
    ├── Validate each sub-model independently
    ├── Compose into Master Classifier via Azure DI Studio
    └── Update production Model ID → new Composed ID

Phase 2: FHA, NANQ, VALoan models
    └── Same process, leveraging Phase 1 learnings

Phase 3: Correspondent model
    └── Final rollout

Downstream Impact: ZERO
    • API call structure unchanged
    • Label strings unchanged
    • Only the Model ID reference is updated
```

---

## 8. Tax Document Extraction & MGIC Cash Flow Analysis

### 8.1 Overview

The MGIC SAM Cash Flow Analysis Worksheet is the industry-standard template used by underwriters to calculate a borrower's qualifying income. The system must extract specific fields from IRS tax forms and map them to MGIC worksheet rows for automated cash flow analysis.

### 8.2 Tax Document Taxonomy

```
Tax Document Package (uploaded as multi-page PDF)
│
├── PERSONAL TAX RETURN (Form 1040)
│   ├── Schedule 1  ─── Additional income sources
│   ├── Schedule A  ─── Itemized deductions
│   ├── Schedule B  ─── Interest & dividends
│   ├── Schedule C  ─── Sole proprietorship profit/loss
│   ├── Schedule D  ─── Capital gains/losses
│   ├── Schedule E  ─── Rental income, partnerships, S-corps
│   ├── Schedule F  ─── Farm income
│   └── Schedule SE ─── Self-employment tax
│
├── BUSINESS ENTITY RETURNS
│   ├── Form 1065   ─── Partnership return
│   │   └── Schedule K-1 (1065) ─── Partner's share
│   ├── Form 1120-S ─── S-Corporation return
│   │   └── Schedule K-1 (1120-S) ─── Shareholder's share
│   └── Form 1120   ─── C-Corporation return
│
├── INCOME VERIFICATION
│   ├── Form W-2    ─── Wage and tax statement
│   ├── Form 1098   ─── Mortgage interest statement
│   ├── Form 1099-NEC ── Nonemployee compensation
│   └── Form 1099-R ─── Retirement distributions
│
└── LENDER FORMS
    ├── Form 4506-C ─── IRS transcript request
    ├── Form 4562  ─── Depreciation/amortization
    └── Form 1084  ─── Self-employment income analysis
```

### 8.3 Business Structure → Tax Form Mapping

| Business Structure | Primary Tax Form | Key Schedule | Underwriting Purpose |
|-------------------|-----------------|-------------|---------------------|
| Sole Proprietorship | Form 1040 (Personal) | Schedule C | Business profit/loss reported directly on personal return |
| Rental Property Owner | Form 1040 (Personal) | Schedule E | Supplemental income from individual rental real estate |
| S-Corporation | Form 1120-S (Business) | Schedule K-1 | "Passes through" profit/loss from business to owner's 1040 |
| Partnership / LLC | Form 1065 (Business) | Schedule K-1 | Reports individual partner's share of business earnings |

### 8.4 Extraction Model Routing: Azure DI Prebuilt vs. Custom

The system uses a **classifier-first, then route-to-extractor** pattern:

```
Tax Package (multi-page PDF)
        │
        ▼
┌──────────────────────────────────┐
│  Step 1: CLASSIFY                 │
│  Custom Classifier identifies     │
│  individual forms within the      │
│  tax package (page ranges)        │
│                                   │
│  "Pages 1-2: Form 1040"          │
│  "Pages 3-4: Schedule C"         │
│  "Pages 5-6: Schedule K-1 (1065)"│
│  "Pages 7-10: Form 1065"         │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Step 2: ROUTE TO EXTRACTOR       │
│                                   │
│  Is it a personal tax form?       │
│  ├── YES → Azure DI Prebuilt     │
│  │         (95% of MGIC fields)   │
│  │                                │
│  └── NO → Custom Model / LLM     │
│           (5% of MGIC fields)     │
│           K-1, 1065, 1120-S       │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Step 3: MAP TO MGIC WORKSHEET   │
│  Extracted fields → MGIC rows    │
│  Calculate subtotals              │
│  Apply ownership percentages      │
│  Two-year comparison              │
└──────────────────────────────────┘
```

### 8.5 Azure DI Prebuilt Model Coverage (95% of MGIC)

| Schedule | Azure Model ID | Confidence | MGIC Rows | Status |
|----------|---------------|-----------|-----------|--------|
| **Schedule B** | `tax.us.1040ScheduleB.2023` | 98% | Rows 1-2 | Supported |
| **Schedule C** | `tax.us.1040ScheduleC.2023` | 87% | Rows 4-12 | Supported |
| **Schedule D** | `tax.us.1040ScheduleD.2022` | 87% | Row 13 | Supported |
| **Schedule E** | `tax.us.1040ScheduleE.2023` | 87% | Rows 14-16 | Supported |
| **Schedule F** | `tax.us.1040ScheduleF.2023` | ~85% | Rows 17-23 | Supported |

### 8.6 Custom Models Required (5% of MGIC)

| Form | MGIC Rows | Status | Solution |
|------|-----------|--------|----------|
| **Schedule K-1 (Form 1065)** | Rows 24-36 (Partnership) | Not supported by Azure DI | Custom extraction model + LLM fallback |
| **Form 1065** | Rows 28-35 | Not supported by Azure DI | Custom extraction model + LLM fallback |
| **Schedule K-1 (Form 1120-S)** | Rows 37-47 (S-Corp) | Not supported by Azure DI | Custom extraction model + LLM fallback |
| **Form 1120-S** | Rows 40-46 | Not supported by Azure DI | Custom extraction model + LLM fallback |

### 8.7 Complete MGIC Field Extraction Map

#### Schedule B — Interest and Dividends from Self-Employment

| MGIC Row | Field Name | Tax Form Source | Azure Box |
|----------|-----------|----------------|-----------|
| 1 | Recurring Interest Income | Schedule B Line 1 or 1040 Line 2b | Box 1 |
| 2 | Recurring Dividend Income | Schedule B Line 5 or 1040 Line 3b | Box 5 |

#### Schedule C — Sole Proprietorship

| MGIC Row | Field Name | Tax Form Line | Azure Box | Azure Field Name |
|----------|-----------|--------------|-----------|-----------------|
| - | Business Name | Header | Header | `BusinessName` |
| 4 | Net Profit (Loss) | Line 31 | Box 31 | `NetProfitOrLoss` |
| 5 | Deduct nonrecurring income | Line 6 | Box 6 | `OtherIncome` |
| 6 | Depletion | Line 12 | Box 12 | `Depletion` |
| 7 | Depreciation | Line 13 | Box 13 | `Depreciation` |
| 8 | Non-Deductible Meals & Entertainment | Line 24b | Box 24b | `MealsAndEntertainment` |
| 9 | Business Use of Home | Line 30 | Box 30 | `ExpensesForHomeUse` |

#### Schedule D — Capital Gains and Losses

| MGIC Row | Field Name | Tax Form Source | Azure Box |
|----------|-----------|----------------|-----------|
| 13 | Recurring Capital Gains (Loss) | Page 2, Line 16 | Box 16 |

#### Schedule E — Supplemental Income and Loss

| MGIC Row | Field Name | Tax Form Source | Azure Box |
|----------|-----------|----------------|-----------|
| 14 | Royalty Income (Loss) | Schedule E Line 4 | Box 4 (each property column) |
| 15 | Total Expenses | Schedule E Line 20 | Box 20 (each property) |
| 16 | Depreciation Expense or Depletion | Schedule E Line 18 | Box 18 (each property) |

#### Schedule F — Farm Income

| MGIC Row | Field Name | Tax Form Source | Azure Box |
|----------|-----------|----------------|-----------|
| 17 | Net Profit (Loss) | Schedule F Line 34 | Box 34 |
| 18 | Non-Tax Portion Ongoing Co-op & CCC | Lines 3a-b through 6a-b | Box 3a-3b through 6 |
| 19 | Add nonrecurring loss | Schedule F Lines 2-8 | Box 2, 8 |
| 20 | Deduct nonrecurring income | Schedule F Lines 2-8 | — |
| 21 | Depreciation | Schedule F Line 14 | Box 14 |
| 22 | Amortization/Casualty Loss/Depletion | Schedule F Line 32 | Box 32a-32f |
| 23 | Business Use of Home | Schedule F Line 32 | — |

#### Partnership Cash Flow (CUSTOM MODEL REQUIRED)

| MGIC Row | Field Name | Source Form | Source Field |
|----------|-----------|-----------|-------------|
| - | Partnership Name | K-1 Header | Box B |
| 24 | Ordinary Income (Loss) | Schedule K-1 Line 1 | Box 1 |
| 25 | Net Rental Income (Loss) | Schedule K-1 Lines 2 & 3 | Box 2, 3 |
| 26 | Guaranteed Payments | Schedule K-1 Line 4c | Box 4c |
| 27 | Wages | W-2 Box 5 | — |
| 28 | Passthrough (Income) Loss | Form 1065 Line 4 | Box 4 |
| 29 | Deduct nonrecurring income | Form 1065 Lines 5, 6 & 7 | Box 5, 6, 7 |
| 30 | Depreciation | Form 1065 Line 16c | Box 16c |
| 31 | Depreciation (Form 8825) | Form 8825 Line 14 | Box 14 per property |
| 32 | Depletion | Form 1065 Line 17 | Box 17 |
| 33 | Amortization/Casualty Loss | From statement or Lines 5,6,7 | — |
| 34 | Mortgages/Notes Payable < 1 Year | Schedule L, Line 16, Col d | Link |
| 35 | Non-Deductible Travel & Entertainment | Schedule M-1, Line 4b | Box 4b |
| 36 | Multiplied by Ownership Percentage | Schedule K-1 Ownership % | — |

#### S-Corporation Cash Flow (CUSTOM MODEL REQUIRED)

| MGIC Row | Field Name | Source Form | Source Field |
|----------|-----------|-----------|-------------|
| - | S Corporation Name | K-1 Header | Box B |
| 37 | Ordinary Income (Loss) | Schedule K-1 Line 1 | Box 1 |
| 38 | Net Rental Income (Loss) | Schedule K-1 Lines 2 & 3 | Box 2, 3 |
| 39 | Wages | W-2 Box 5 | — |
| 40 | Deduct nonrecurring income | Form 1120S Lines 4 & 5 | Box 4, 5 |
| 41 | Depreciation | Form 1120S Line 14 | Box 14 |
| 42 | Depreciation (Form 8825) | Form 1120S Line 14 | Box 14 per property |
| 43 | Depletion | Form 1120S Line 15 | Box 15 |
| 44 | Amortization/Casualty Loss | From statement or Lines 4 & 5 | Box 4, 5 |
| 45 | Mortgages/Notes Payable < 1 Year | Schedule L, Line 17, Col d | Box 17 per property |
| 46 | Non-Deductible Travel & Entertainment | Schedule M-1, Line 3b | Box 3b |
| 47 | Multiplied by Ownership Percentage | Schedule K-1 Ownership % | — |

### 8.8 MGIC Extraction Engine Architecture

```python
class MGICExtractionEngine:
    """
    Orchestrates extraction from tax documents and maps
    results to MGIC Cash Flow Analysis worksheet rows.
    """

    def process_tax_package(self, tax_package: TaxPackage) -> MGICWorksheet:
        # Step 1: Classify each form within the tax package
        classified_forms = self.classifier.classify_pages(tax_package)
        # Result: [("1040", pages 1-2), ("ScheduleC", pages 3-4), ...]

        mgic = MGICWorksheet(borrower=tax_package.borrower)

        for form_type, page_range in classified_forms:
            # Step 2: Route to appropriate extractor
            if form_type in self.AZURE_PREBUILT_FORMS:
                # Personal tax forms → Azure DI prebuilt
                extracted = self.azure_di.extract(
                    model_id=self.AZURE_MODEL_MAP[form_type],
                    pages=page_range
                )
            else:
                # Business forms (K-1, 1065, 1120-S) → Custom model + LLM fallback
                extracted = self.custom_extractor.extract(
                    form_type=form_type,
                    pages=page_range,
                    fallback_to_llm=True
                )

            # Step 3: Map extracted fields to MGIC rows
            mgic_rows = self.mgic_mapper.map(form_type, extracted)
            mgic.add_section(form_type, mgic_rows)

        # Step 4: Apply business rules
        mgic.apply_ownership_percentages()   # K-1 ownership % multiplication
        mgic.calculate_subtotals()            # Per-section subtotals
        mgic.apply_mileage_depreciation()     # IRS annual rates

        return mgic

    AZURE_MODEL_MAP = {
        "ScheduleB": "tax.us.1040ScheduleB.2023",
        "ScheduleC": "tax.us.1040ScheduleC.2023",
        "ScheduleD": "tax.us.1040ScheduleD.2022",
        "ScheduleE": "tax.us.1040ScheduleE.2023",
        "ScheduleF": "tax.us.1040ScheduleF.2023",
        "Form1040":  "tax.us.1040.2023",
        "W2":        "tax.us.w2",
        "1099NEC":   "tax.us.1099NEC.2023",
        "1099R":     "tax.us.1099R.2023",
    }

    AZURE_PREBUILT_FORMS = set(AZURE_MODEL_MAP.keys())
```

### 8.9 Additional MGIC Business Rules

| Rule | Details |
|------|---------|
| **Multiple Entities** | Worksheet supports multiple businesses per entity type (multiple Schedule C, multiple partnerships, multiple S-Corps) |
| **Two-Year Comparison** | All fields require data for two consecutive tax years for trend analysis |
| **Subtotal Calculations** | Each section (Schedule B, C, D, E, F, Partnership, S-Corp) has auto-calculated subtotals |
| **Mileage Depreciation Rates** | System must apply correct IRS annual rates: 2025: $0.33, 2024: $0.30, 2023: $0.28 per mile |
| **Ownership Percentage** | Partnership and S-Corp income must be multiplied by borrower's ownership percentage from K-1 |
| **Distribution Requirements** | K-1 income greater than distributions triggers additional underwriting requirements |

### 8.10 Custom Model Strategy for Business Entity Forms

For the ~5% of MGIC requirements not covered by Azure DI prebuilt models, the system uses a layered approach:

```
Business Entity Document (K-1, 1065, 1120-S)
        │
        ▼
┌───────────────────────────────────┐
│  Attempt 1: Azure DI Custom Model │
│  (trained on annotated samples)    │
│  Confidence threshold: 80%         │
└───────────┬───────────────────────┘
            │
     Confidence >= 80%?
    /                \
  Yes                 No
   │                  │
   ▼                  ▼
Accept         ┌──────────────────────┐
result         │ Attempt 2: LLM       │
               │ (Claude API)          │
               │                       │
               │ Send OCR text +       │
               │ MGIC field schema     │
               │ as structured tool    │
               │ call                  │
               └──────────┬───────────┘
                          │
                   ┌──────▼──────┐
                   │ Normalize + │
                   │ Validate +  │
                   │ → Review    │
                   └─────────────┘
```

### 8.11 Tax Extraction Data Model

```sql
-- Tax package (multi-page uploaded document)
CREATE TABLE tax_packages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_application_id UUID NOT NULL REFERENCES loan_applications(id),
    borrower_id         UUID NOT NULL,
    tax_year            VARCHAR(4) NOT NULL,
    blob_storage_path   VARCHAR(1000) NOT NULL,
    azure_di_raw_response JSONB,           -- Full Azure DI response for reprocessing
    processing_status   VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    total_pages         INTEGER,
    error_details       JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Individual forms identified within a tax package
CREATE TABLE tax_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_package_id      UUID NOT NULL REFERENCES tax_packages(id),
    doc_type            VARCHAR(100) NOT NULL,  -- 'tax.us.1040ScheduleC.2023'
    page_range_start    INTEGER NOT NULL,
    page_range_end      INTEGER NOT NULL,
    classification_confidence DECIMAL(5,4),
    extraction_model_used VARCHAR(100),          -- 'azure_prebuilt' or 'custom' or 'llm'
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Individual extracted fields per document
CREATE TABLE extracted_fields (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_document_id     UUID NOT NULL REFERENCES tax_documents(id),
    field_name          VARCHAR(100) NOT NULL,
    box_number          VARCHAR(20),              -- e.g., 'Box31', 'Box13'
    raw_value           TEXT,                      -- Exact Azure DI extraction
    normalized_value    TEXT,                      -- Cleaned/validated value
    data_type           VARCHAR(20),               -- 'currency', 'string', 'date', 'percentage'
    confidence          DECIMAL(5,4),
    extraction_status   VARCHAR(20) DEFAULT 'extracted',  -- 'extracted', 'low_confidence', 'failed'
    field_errors        JSONB,                     -- Validation errors per field
    manually_corrected  BOOLEAN DEFAULT FALSE,
    corrected_value     TEXT,
    corrected_by        UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- MGIC worksheet row mappings (calculated from extracted fields)
CREATE TABLE mgic_mappings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_application_id UUID NOT NULL REFERENCES loan_applications(id),
    borrower_id         UUID NOT NULL,
    tax_year            VARCHAR(4) NOT NULL,
    mgic_row            INTEGER NOT NULL,
    mgic_field_name     VARCHAR(200) NOT NULL,
    calculated_value    DECIMAL(15,2),
    source_document_id  UUID REFERENCES tax_documents(id),
    source_fields       JSONB,                     -- Links to extracted_fields used
    calculation_formula TEXT,                       -- How value was derived
    validation_status   VARCHAR(20) DEFAULT 'pending',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(loan_application_id, borrower_id, tax_year, mgic_row)
);

-- Form schema registry (handles different tax years / form versions)
CREATE TABLE form_schemas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_type            VARCHAR(100) NOT NULL,     -- 'tax.us.1040ScheduleC.2023'
    tax_year            VARCHAR(4) NOT NULL,
    version             VARCHAR(10) NOT NULL,
    field_definitions   JSONB NOT NULL,            -- Schema definition per field
    validation_rules    JSONB,                      -- Field validation rules
    mgic_row_mappings   JSONB,                      -- MGIC row mappings
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(doc_type, tax_year, version)
);
```

---

## 9. Multi-Bank Format Handling Strategy (Non-Tax Documents)

This is the most critical architectural challenge. A "bank statement" from Chase looks completely different from one from Wells Fargo, a local credit union, or an international bank. Multiplied across 20-30 document types and 500+ institutions, building individual templates is not sustainable.

### 7.1 The Format Diversity Problem

```
Same Document Type, Different Formats:

  Chase Bank Statement         Wells Fargo Statement       Local Credit Union
  ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
  │ CHASE ◉           │        │ WELLS FARGO       │        │ ABC Credit Union  │
  │ Statement Period   │        │ Account Summary   │        │ Monthly Statement │
  │ 01/01 - 01/31     │        │ Period: Jan 2026  │        │ January 2026     │
  │                    │        │                    │        │                   │
  │ Account: ****1234  │        │ Acct#: XXXX5678   │        │ Member# 9012     │
  │ Begin Bal: $5,000  │        │ Opening: $3,200   │        │ Prior: $8,100    │
  │ End Bal: $4,250    │        │ Closing: $4,100   │        │ Current: $7,900  │
  │                    │        │                    │        │                   │
  │ DEPOSITS           │        │ Credits            │        │ + Additions      │
  │ 01/15 Payroll 3000 │        │ 01/15 ACH 3000    │        │ Jan 15 DD 3000   │
  └──────────────────┘        └──────────────────┘        └──────────────────┘

  Different labels, layouts, date formats, terminology — SAME data needed
```

### 7.2 Three-Tier Extraction Strategy

Rather than building templates for every bank, we use a tiered strategy:

```
                    ┌─────────────────────────┐
                    │     Document Arrives     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Tier 1: Template Match  │ ◄── Known high-volume formats
                    │  (Fast, Cheap, Precise)  │     Chase, WF, BofA, etc.
                    └────────────┬────────────┘
                                 │
                         Match found?
                        /            \
                      Yes             No
                      │               │
               ┌──────▼──────┐  ┌────▼──────────────┐
               │  Template   │  │  Tier 2: Adaptive  │ ◄── Layout-aware extraction
               │  Extraction │  │  Layout Extraction │     Works on unseen formats
               │  (Known)    │  │  (Generalizable)   │
               └──────┬──────┘  └────────┬───────────┘
                      │                   │
                      │           Confidence > 80%?
                      │          /              \
                      │        Yes               No
                      │         │                │
                      │   ┌─────▼─────┐   ┌─────▼──────────┐
                      │   │  Accept   │   │  Tier 3: LLM   │ ◄── Claude API
                      │   │  Result   │   │  Extraction     │     Handles anything
                      │   └─────┬─────┘   │  (Intelligent)  │
                      │         │         └─────┬──────────┘
                      │         │               │
                      └─────────┴───────┬───────┘
                                        │
                              ┌─────────▼─────────┐
                              │  Normalize + Validate │
                              │  → Human Review Queue │
                              └───────────────────────┘
```

### 7.3 Tier Details

#### Tier 1: Template-Based Extraction (Known Formats)

For the top 20-30 banks by volume (which typically cover 60-70% of all documents):

- Pre-built templates that define field locations, label patterns, and table structures
- Templates are version-managed (banks change layouts periodically)
- Very fast (milliseconds), very cheap (no API calls), very accurate (95%+)
- Templates are built from human-reviewed corrections — the system learns which formats it sees often

```python
# Template definition example
class ChaseStatementTemplate:
    bank_identifier = ["CHASE", "JPMorgan Chase"]
    version = "2025-v2"

    field_map = {
        "statement_period": {
            "anchor_label": r"Statement\s+Period",
            "relative_position": "right_of_label",
            "format": "date_range",
            "pattern": r"\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4}"
        },
        "ending_balance": {
            "anchor_label": r"Ending\s+Balance|End\.?\s+Bal",
            "relative_position": "right_of_label",
            "format": "currency",
            "pattern": r"\$[\d,]+\.\d{2}"
        },
        "deposits": {
            "type": "table",
            "header_pattern": r"DEPOSITS|Credits",
            "columns": ["date", "description", "amount"],
            "end_pattern": r"WITHDRAWALS|Debits|Total Deposits"
        }
    }
```

#### Tier 2: Adaptive Layout-Aware Extraction (Unknown Formats)

For documents from banks without pre-built templates, use layout-aware extraction that understands document structure without needing a specific template:

- Uses **LayoutLM / LayoutLMv3** (Microsoft's document understanding model) fine-tuned on mortgage documents
- Understands spatial relationships between labels and values
- Trained on general patterns: "a label on the left, a value on the right"
- Can extract from unseen bank formats with 80-85% accuracy
- Runs on your own infrastructure (Azure Container Apps with GPU)

```python
# Layout-aware extraction - works across bank formats
class AdaptiveLayoutExtractor:
    """
    Uses a fine-tuned LayoutLM model to understand document structure
    regardless of specific bank format.
    """

    def extract(self, ocr_result: OCRResult, doc_type: str) -> ExtractionResult:
        # Get the schema of fields we need for this doc type
        target_schema = DOCUMENT_SCHEMAS[doc_type]
        # e.g., for "bank_statement": [statement_period, account_number,
        #         beginning_balance, ending_balance, deposits, withdrawals]

        # Run layout model to identify label-value pairs
        layout_entities = self.layout_model.predict(
            tokens=ocr_result.tokens,
            bounding_boxes=ocr_result.bboxes,
            image=ocr_result.page_image
        )

        # Match detected entities to target schema
        extracted = self.schema_matcher.match(layout_entities, target_schema)

        return ExtractionResult(
            fields=extracted.fields,
            confidence=extracted.avg_confidence,
            strategy="adaptive_layout"
        )
```

#### Tier 3: LLM-Based Extraction (Fallback for Complex/Unusual Docs)

For documents that Tier 2 cannot handle with sufficient confidence, fall back to an LLM (Claude API):

- Send the OCR text (not the image, to save tokens) along with a structured extraction prompt
- Use Claude's tool-use/function-calling to get structured JSON output
- Most expensive tier but handles virtually any format
- Claude's Batches API provides 50% cost reduction for non-urgent processing

```python
# LLM-based extraction prompt structure
EXTRACTION_PROMPT = """
You are extracting structured data from a {doc_type}.

Document text (from OCR):
---
{ocr_text}
---

Extract the following fields. If a field is not found, set it to null.
Return your response using the extract_fields tool.
"""

# Claude tool definition for structured output
EXTRACT_TOOL = {
    "name": "extract_fields",
    "description": "Extract structured fields from document",
    "input_schema": {
        "type": "object",
        "properties": {
            "statement_period_start": {"type": "string", "description": "Start date of statement period"},
            "statement_period_end": {"type": "string", "description": "End date of statement period"},
            "account_number_last4": {"type": "string", "description": "Last 4 digits of account"},
            "beginning_balance": {"type": "number", "description": "Starting balance"},
            "ending_balance": {"type": "number", "description": "Ending balance"},
            "total_deposits": {"type": "number", "description": "Sum of all deposits"},
            "total_withdrawals": {"type": "number", "description": "Sum of all withdrawals"},
            "large_deposits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "description": {"type": "string"},
                        "amount": {"type": "number"}
                    }
                },
                "description": "Deposits > $1,000"
            }
        }
    }
}
```

### 7.4 Bank Identification & Template Routing

Before extraction, the system identifies which bank/institution issued the document:

```python
class BankIdentifier:
    """
    Identifies the issuing bank/institution from document content.
    Used to route to the correct template (Tier 1) or skip to Tier 2.
    """

    def identify(self, ocr_text: str, visual_features: dict) -> BankMatch:
        # Strategy 1: Logo detection (if visual features available)
        logo_match = self.logo_detector.detect(visual_features)

        # Strategy 2: Text pattern matching
        text_match = self.text_matcher.match(ocr_text, self.bank_patterns)
        # Patterns: routing numbers, bank names, URLs, phone numbers

        # Strategy 3: Layout fingerprint
        layout_match = self.layout_fingerprinter.match(visual_features)

        # Combine signals
        best_match = self.ensemble(logo_match, text_match, layout_match)

        return BankMatch(
            bank_id=best_match.bank_id,
            bank_name=best_match.bank_name,
            confidence=best_match.confidence,
            has_template=self.template_registry.exists(best_match.bank_id)
        )
```

### 7.5 Continuous Template Learning

The system automatically identifies candidates for new templates based on volume and human correction patterns:

```
  Human reviews and corrects extractions
                │
                ▼
  System logs: (bank_id, doc_type, correction_count, volume)
                │
                ▼
  Weekly analysis: "ABC Bank statements processed 200 times
                    this month with 40% correction rate"
                │
                ▼
  Alert to ops team: "Consider building a template for
                      ABC Bank statements — ROI: high"
                │
                ▼
  Template builder tool assists in creating new template
  from corrected examples
```

---

## 10. Document Processing Pipeline

### 10.1 End-to-End Pipeline Flow

```
Step 1: INGEST                Step 2: OCR                 Step 3: CLASSIFY
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│ Upload via    │             │ Preprocess   │             │ Identify     │
│ React UI     │────────────▶│ • Deskew     │────────────▶│ document     │
│ or API/SFTP  │             │ • Denoise    │             │ type         │
│              │             │ • Enhance    │             │              │
│ Store in     │             │              │             │ W-2? 1040?   │
│ Azure Blob   │             │ OCR          │             │ Bank stmt?   │
│              │             │ • Tesseract  │             │ Pay stub?    │
│ Create DB    │             │ • PaddleOCR  │             │              │
│ record       │             │ • Azure DI*  │             │ Confidence:  │
│              │             │              │             │ 0.0 → 1.0    │
│ Queue for    │             │ Output:      │             │              │
│ processing   │             │ text + bbox  │             │ If < 0.7 →   │
│              │             │ + tables     │             │ flag for     │
└──────────────┘             └──────────────┘             │ manual class │
                                                          └──────────────┘

Step 4: EXTRACT               Step 5: VALIDATE            Step 6: SUMMARIZE
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│ Based on     │             │ Field-level   │             │ Per-document  │
│ doc type:    │             │ • Date valid? │             │ summary       │
│              │────────────▶│ • Amount ≥ 0? │────────────▶│              │
│ Tier 1/2/3   │             │ • SSN format? │             │ Cross-doc     │
│ extraction   │             │              │             │ summary       │
│              │             │ Cross-field   │             │              │
│ Structured   │             │ • Bal = Start │             │ Discrepancy   │
│ output:      │             │   + Dep - Wdl │             │ report        │
│ JSON fields  │             │              │             │              │
│ + confidence │             │ Cross-doc     │             │ Generated via │
│ per field    │             │ • W2 income   │             │ Claude API    │
│              │             │   vs 1040 AGI │             │              │
└──────────────┘             └──────────────┘             └──────────────┘

Step 7: HUMAN REVIEW
┌──────────────────────────────────────────────────┐
│ Review Dashboard                                  │
│                                                    │
│ ┌─────────────────┐  ┌──────────────────────────┐ │
│ │ Original Doc    │  │ Extracted Data            │ │
│ │ (PDF viewer     │  │                           │ │
│ │  with field     │  │ Period: 01/01 - 01/31 [✓] │ │
│ │  highlights)    │  │ End Bal: $4,250      [✓]  │ │
│ │                 │  │ Deposits: $3,000    [✓]   │ │
│ │  ◄ highlight    │  │ Large Dep: $3,000   [✎]  │ │
│ │    where field  │  │                           │ │
│ │    was found    │  │ Confidence: 92% ████████░ │ │
│ └─────────────────┘  └──────────────────────────┘ │
│                                                    │
│  [ Approve ]  [ Reject ]  [ Escalate ]            │
└──────────────────────────────────────────────────┘
```

### 10.2 OCR Engine Selection Logic

```python
class OCROrchestrator:
    """
    Selects the optimal OCR engine based on document characteristics.
    Goal: Maximize accuracy while minimizing cost.
    """

    def process(self, document: Document) -> OCRResult:
        # Step 1: Assess document quality
        quality = self.quality_assessor.assess(document.image)

        # Step 2: Check if document is digital-native PDF
        if document.is_digital_pdf:
            # Extract text directly — no OCR needed (free, perfect accuracy)
            return self.pdf_text_extractor.extract(document)

        # Step 3: For scanned documents, choose OCR engine
        if quality.is_clean and quality.is_standard_layout:
            # Clean scan, standard layout → Tesseract (free)
            result = self.tesseract.extract(document.image)
            if result.confidence > 0.85:
                return result

        # Step 4: If Tesseract result is low confidence or doc is complex
        if quality.has_tables or quality.is_multi_column:
            # Complex layout → PaddleOCR (free, better with tables)
            result = self.paddle_ocr.extract(document.image)
            if result.confidence > 0.80:
                return result

        # Step 5: Fallback to Azure Document Intelligence
        # for handwritten content, very poor scans, or complex forms
        result = self.azure_di.extract(document.image)
        return result
```

### 10.3 Classification Model Architecture

```python
class DocumentClassifier:
    """
    Ensemble classifier combining text and layout signals.
    Handles 25+ mortgage document categories.
    """

    DOCUMENT_TYPES = [
        "w2", "1099_int", "1099_misc", "1099_div",
        "1040", "1040_schedule_c",
        "bank_statement", "investment_statement",
        "pay_stub",
        "drivers_license", "passport",
        "property_appraisal", "title_report",
        "homeowners_insurance", "flood_insurance",
        "gift_letter", "explanation_letter",
        "purchase_agreement", "closing_disclosure",
        "credit_report",
        "employment_verification", "rent_verification",
        # ...
    ]

    def classify(self, ocr_result: OCRResult) -> ClassificationResult:
        # Signal 1: Text-based classification (fine-tuned DistilBERT)
        text_pred = self.text_model.predict(ocr_result.full_text)

        # Signal 2: Layout-based classification (visual features)
        layout_pred = self.layout_model.predict(
            ocr_result.bboxes,
            ocr_result.page_image
        )

        # Signal 3: Keyword heuristics (fast, interpretable)
        keyword_pred = self.keyword_matcher.match(ocr_result.full_text)
        # e.g., "Wage and Tax Statement" → W-2
        # e.g., "Schedule C" → 1040 Schedule C

        # Ensemble: weighted combination
        final = self.ensemble.combine(
            text_pred,      # weight: 0.4
            layout_pred,    # weight: 0.35
            keyword_pred    # weight: 0.25
        )

        return ClassificationResult(
            doc_type=final.predicted_type,
            confidence=final.confidence,
            alternatives=final.top_3,  # Top 3 for human review
            needs_manual_review=final.confidence < 0.70
        )
```

### 10.4 Field Extraction Schemas by Document Type

```python
DOCUMENT_SCHEMAS = {
    "w2": {
        "fields": [
            {"name": "tax_year", "type": "year", "required": True},
            {"name": "employer_name", "type": "string", "required": True},
            {"name": "employer_ein", "type": "ein", "required": True},
            {"name": "employee_name", "type": "string", "required": True},
            {"name": "employee_ssn_last4", "type": "ssn4", "required": True},
            {"name": "wages_tips_compensation", "type": "currency", "required": True},  # Box 1
            {"name": "federal_tax_withheld", "type": "currency", "required": True},     # Box 2
            {"name": "social_security_wages", "type": "currency", "required": False},   # Box 3
            {"name": "medicare_wages", "type": "currency", "required": False},           # Box 5
            {"name": "state", "type": "state_code", "required": False},
            {"name": "state_wages", "type": "currency", "required": False},
            {"name": "state_tax_withheld", "type": "currency", "required": False},
        ]
    },
    "bank_statement": {
        "fields": [
            {"name": "bank_name", "type": "string", "required": True},
            {"name": "account_holder_name", "type": "string", "required": True},
            {"name": "account_number_last4", "type": "string", "required": True},
            {"name": "account_type", "type": "enum", "values": ["checking", "savings", "money_market"], "required": True},
            {"name": "statement_period_start", "type": "date", "required": True},
            {"name": "statement_period_end", "type": "date", "required": True},
            {"name": "beginning_balance", "type": "currency", "required": True},
            {"name": "ending_balance", "type": "currency", "required": True},
            {"name": "total_deposits", "type": "currency", "required": True},
            {"name": "total_withdrawals", "type": "currency", "required": True},
            {"name": "average_daily_balance", "type": "currency", "required": False},
            {"name": "large_deposits", "type": "transaction_list", "required": True,
             "description": "All deposits >= $1,000"},
            {"name": "nsf_overdraft_count", "type": "integer", "required": True},
        ]
    },
    "pay_stub": {
        "fields": [
            {"name": "employer_name", "type": "string", "required": True},
            {"name": "employee_name", "type": "string", "required": True},
            {"name": "pay_period_start", "type": "date", "required": True},
            {"name": "pay_period_end", "type": "date", "required": True},
            {"name": "pay_date", "type": "date", "required": True},
            {"name": "gross_pay", "type": "currency", "required": True},
            {"name": "net_pay", "type": "currency", "required": True},
            {"name": "ytd_gross", "type": "currency", "required": True},
            {"name": "ytd_net", "type": "currency", "required": False},
            {"name": "pay_frequency", "type": "enum",
             "values": ["weekly", "biweekly", "semi_monthly", "monthly"], "required": False},
            {"name": "regular_hours", "type": "number", "required": False},
            {"name": "overtime_hours", "type": "number", "required": False},
        ]
    },
    "1040": {
        "fields": [
            {"name": "tax_year", "type": "year", "required": True},
            {"name": "filing_status", "type": "enum",
             "values": ["single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"],
             "required": True},
            {"name": "taxpayer_name", "type": "string", "required": True},
            {"name": "total_income", "type": "currency", "required": True},          # Line 9
            {"name": "adjusted_gross_income", "type": "currency", "required": True}, # Line 11
            {"name": "taxable_income", "type": "currency", "required": True},        # Line 15
            {"name": "total_tax", "type": "currency", "required": True},             # Line 24
            {"name": "self_employment_income", "type": "currency", "required": False},
            {"name": "has_schedule_c", "type": "boolean", "required": True},
            {"name": "has_schedule_e", "type": "boolean", "required": True},
        ]
    },
}
```

---

## 11. Human-in-the-Loop Workflow

### 11.1 Design Philosophy

100% automation is not the goal — **assisted automation** is. The system does the heavy lifting; humans verify and approve. This is both a regulatory requirement (mortgage lending) and a quality safeguard.

### 11.2 Review Queue Design

```
┌──────────────────────────────────────────────────────────────────┐
│  REVIEW DASHBOARD                                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Filters: [All ▼] [High Priority ▼] [My Queue ▼] [Doc Type ▼]  │
│                                                                  │
│  ┌────┬──────────┬───────────┬────────────┬──────────┬────────┐ │
│  │ #  │ Loan ID  │ Doc Type  │ Confidence │ Status   │ Action │ │
│  ├────┼──────────┼───────────┼────────────┼──────────┼────────┤ │
│  │ 1  │ LN-4521  │ W-2       │ ██████ 97% │ Ready    │ Review │ │
│  │ 2  │ LN-4521  │ Bank Stmt │ █████░ 84% │ Ready    │ Review │ │
│  │ 3  │ LN-4522  │ Pay Stub  │ ███░░░ 62% │ Flagged  │ Review │ │
│  │ 4  │ LN-4522  │ Unknown   │ ░░░░░░ 31% │ Classify │ Review │ │
│  │ 5  │ LN-4523  │ 1040      │ ██████ 95% │ Ready    │ Review │ │
│  └────┴──────────┴───────────┴────────────┴──────────┴────────┘ │
│                                                                  │
│  Stats: 142 pending │ 38 flagged │ 891 completed today           │
└──────────────────────────────────────────────────────────────────┘
```

### 11.3 Review Workspace (Side-by-Side)

```
┌───────────────────────────────────────────────────────────────────────┐
│  REVIEW: LN-4521 / Bank Statement / Chase / Confidence: 84%         │
├────────────────────────────┬──────────────────────────────────────────┤
│                            │                                          │
│   ORIGINAL DOCUMENT        │   EXTRACTED DATA                         │
│                            │                                          │
│   ┌──────────────────┐     │   Bank: Chase               [✓ locked]  │
│   │  CHASE            │     │   Account: ****1234         [✓ locked]  │
│   │                  │     │   Type: Checking            [✓]         │
│   │  Statement       │     │   Period: 01/01 - 01/31/26  [✓]         │
│   │  Period: 01/01 - │◄────│   Begin Bal: $5,000.00      [✓]         │
│   │  01/31/2026      │     │   End Bal: $4,250.00        [✓]         │
│   │                  │     │   Total Deposits: $3,000.00 [✓]         │
│   │  Account: ***1234│     │   Total Withdrawals: $3,750 [⚠ verify]  │
│   │                  │     │   Avg Daily Bal: $4,600     [⚠ low conf]│
│   │  Begin Bal: $5000│     │   Large Deposits:                        │
│   │  End Bal: $4,250 │     │     01/15 - Payroll - $3,000 [✓]        │
│   │                  │     │   NSF/Overdraft: 0          [✓]         │
│   │  DEPOSITS        │     │                                          │
│   │  01/15 Payroll   │     │   ─────────────────────────────          │
│   │  $3,000.00       │     │   Validation Checks:                     │
│   │                  │     │   ✓ End = Begin + Dep - Wdl              │
│   │  WITHDRAWALS     │     │   ✓ Large deposits identified            │
│   │  01/03 Rent      │     │   ⚠ Total withdrawals: verify           │
│   │  $1,500          │     │                                          │
│   │  01/20 Utilities │     │   ─────────────────────────────          │
│   │  $250            │     │   AI Notes:                              │
│   │  ...             │     │   "Statement shows stable balance.       │
│   │                  │     │    One large payroll deposit monthly.    │
│   └──────────────────┘     │    No NSF or overdraft activity."        │
│                            │                                          │
│  [◄ Prev] [Next ►]        │  [✓ Approve] [✗ Reject] [↑ Escalate]    │
│  [Zoom+] [Zoom-] [Rotate] │  [✎ Edit Field] [💬 Add Note]           │
└────────────────────────────┴──────────────────────────────────────────┘
```

### 11.4 Confidence-Based Routing

```python
class ReviewRouter:
    """
    Routes documents to appropriate review workflows based on
    extraction confidence and business rules.
    """

    def route(self, extraction: ExtractionResult) -> ReviewAssignment:
        overall_confidence = extraction.overall_confidence

        if overall_confidence >= 0.95:
            # HIGH CONFIDENCE — Quick review (1-click approve)
            return ReviewAssignment(
                queue="quick_review",
                priority="normal",
                ui_mode="summary_view",         # Show summary, not field-by-field
                expected_review_time="30 seconds",
                reviewer_level="any"
            )

        elif overall_confidence >= 0.75:
            # MEDIUM CONFIDENCE — Standard review
            # Highlight low-confidence fields
            low_conf_fields = [
                f for f in extraction.fields
                if f.confidence < 0.80
            ]
            return ReviewAssignment(
                queue="standard_review",
                priority="normal",
                ui_mode="side_by_side",          # Full side-by-side review
                highlight_fields=low_conf_fields,
                expected_review_time="2 minutes",
                reviewer_level="any"
            )

        elif overall_confidence >= 0.50:
            # LOW CONFIDENCE — Detailed review
            return ReviewAssignment(
                queue="detailed_review",
                priority="high",
                ui_mode="side_by_side_enhanced",  # All fields editable
                expected_review_time="5 minutes",
                reviewer_level="experienced"
            )

        else:
            # VERY LOW CONFIDENCE — Manual processing
            return ReviewAssignment(
                queue="manual_processing",
                priority="urgent",
                ui_mode="manual_entry",           # Pre-filled but mostly manual
                expected_review_time="10 minutes",
                reviewer_level="senior"
            )
```

### 11.5 Feedback Loop (Learning from Corrections)

Every human correction is captured and feeds back into model improvement:

```
Human corrects a field
        │
        ▼
┌──────────────────────────┐
│ Correction Record:        │
│ - document_id: doc_123    │
│ - field: "ending_balance" │
│ - extracted: $4,200       │
│ - corrected: $4,250       │
│ - strategy: "tier_2"      │
│ - bank: "chase"           │
│ - confidence_was: 0.72    │
└──────────────────────────┘
        │
        ├──► Stored in corrections database
        │
        ├──► Aggregated weekly for model retraining
        │    "Tier 2 accuracy on Chase statements dropped to 78%
        │     — 42 corrections this week on ending_balance field"
        │
        ├──► Template candidate detection
        │    "Chase format seen 200+ times, correction rate > 15%
        │     → recommend building Tier 1 template"
        │
        └──► Prompt improvement for Tier 3
             "Common error: confusing 'Available Balance' with
              'Ending Balance' on Chase statements → update prompt"
```

---

## 12. Technology Stack

### 12.1 Complete Technology Matrix

| Layer | Technology | Purpose | Justification |
|-------|-----------|---------|---------------|
| **Frontend** | React 18+ | Review UI, Upload Portal, Admin | Existing stack |
| | TypeScript | Type safety | Industry standard |
| | PDF.js / react-pdf | Document viewing | In-browser PDF rendering |
| | TanStack Query | Data fetching | Caching, optimistic updates |
| | Zustand / Redux Toolkit | State management | Review workflow state |
| **API Gateway** | Azure API Management | Auth, rate limiting, routing | Unified entry point |
| **Backend (.NET)** | .NET 8 (ASP.NET Core) | REST APIs, orchestration | Existing stack, enterprise-grade |
| | Entity Framework Core | ORM | Database access |
| | MassTransit | Message bus abstraction | Clean Service Bus integration |
| | Hangfire / Azure Functions | Background jobs | Async processing workers |
| | FluentValidation | Input validation | Business rule validation |
| **Backend (Python)** | Python 3.11+ | AI/ML services | ML ecosystem |
| | FastAPI | REST APIs | Async, fast, auto-docs |
| | Celery / Azure Functions | Task queue workers | Async processing |
| | Pydantic | Data validation | Schema enforcement |
| **OCR** | Tesseract 5 | Primary OCR (free) | Open-source, good for clean docs |
| | PaddleOCR | Secondary OCR (free) | Better table/layout handling |
| | Azure AI Document Intelligence | Fallback OCR (paid) | Handwriting, complex layouts |
| **ML/AI Models** | LayoutLMv3 | Layout-aware extraction | Document understanding |
| | DistilBERT (fine-tuned) | Document classification | Fast, efficient |
| | Claude API (Anthropic) | LLM extraction + summarization | Best for unstructured extraction |
| **Infrastructure** | Azure Container Apps | Python service hosting | Serverless containers, auto-scale |
| | Azure App Service | .NET hosting | Existing deployment target |
| | Azure Blob Storage | Document storage | Cheap, durable |
| | Azure Service Bus | Message queue | Async pipeline communication |
| | Azure Key Vault | Secrets management | API keys, connection strings |
| | Azure Monitor + App Insights | Observability | Logs, metrics, traces |
| **Database** | Azure PostgreSQL Flexible | Primary database | Relational data, JSONB for extractions |
| | Redis (Azure Cache) | Caching | Template cache, session, rate limiting |
| **DevOps** | Azure DevOps / GitHub Actions | CI/CD | Build, test, deploy pipelines |
| | Docker | Containerization | Python services |
| | Terraform / Bicep | IaC | Infrastructure as code |

### 12.2 Python Package Ecosystem

```
# Core OCR
pytesseract>=0.3.10          # Tesseract wrapper
paddleocr>=2.7                # PaddleOCR
azure-ai-formrecognizer>=3.3  # Azure Document Intelligence

# ML / Document Understanding
transformers>=4.35            # LayoutLMv3, DistilBERT
torch>=2.1                    # PyTorch backend
Pillow>=10.0                  # Image processing
pdf2image>=1.16               # PDF to image conversion
pymupdf>=1.23                 # PDF text extraction (digital PDFs)
opencv-python>=4.8            # Image preprocessing

# LLM
anthropic>=0.40               # Claude API client

# API Framework
fastapi>=0.104                # REST API
uvicorn>=0.24                 # ASGI server
pydantic>=2.5                 # Data validation

# Messaging & Storage
azure-servicebus>=7.11        # Azure Service Bus
azure-storage-blob>=12.19     # Azure Blob Storage

# Data Processing
numpy>=1.25
pandas>=2.1                   # Tabular data processing
python-dateutil>=2.8          # Date parsing
```

---

## 13. Data Architecture

### 13.1 Database Schema (PostgreSQL)

```sql
-- Core document tracking
CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_application_id UUID NOT NULL,
    original_filename   VARCHAR(500) NOT NULL,
    blob_storage_path   VARCHAR(1000) NOT NULL,
    file_size_bytes     BIGINT NOT NULL,
    mime_type           VARCHAR(100) NOT NULL,
    page_count          INTEGER,
    upload_source       VARCHAR(50),        -- 'web_upload', 'api', 'sftp', 'email'
    status              VARCHAR(50) NOT NULL DEFAULT 'uploaded',
        -- uploaded → ocr_processing → ocr_complete → classifying →
        -- classified → extracting → extracted → validating →
        -- validated → review_pending → review_in_progress →
        -- approved → rejected → reprocessing
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          UUID REFERENCES users(id)
);

-- OCR results
CREATE TABLE ocr_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id),
    engine_used     VARCHAR(50) NOT NULL,  -- 'tesseract', 'paddleocr', 'azure_di'
    full_text       TEXT,
    pages           JSONB,                  -- Per-page text and bounding boxes
    confidence      DECIMAL(5,4),
    processing_ms   INTEGER,
    cost_usd        DECIMAL(10,6),          -- Track cost per OCR call
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Classification results
CREATE TABLE classification_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id),
    predicted_type      VARCHAR(100) NOT NULL,
    confidence          DECIMAL(5,4) NOT NULL,
    alternative_types   JSONB,              -- Top 3 alternatives with scores
    model_version       VARCHAR(50),
    strategy_used       VARCHAR(50),        -- 'text_model', 'layout_model', 'ensemble'
    manually_corrected  BOOLEAN DEFAULT FALSE,
    corrected_type      VARCHAR(100),
    corrected_by        UUID REFERENCES users(id),
    corrected_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Extraction results
CREATE TABLE extraction_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id),
    document_type       VARCHAR(100) NOT NULL,
    extraction_strategy VARCHAR(50) NOT NULL,  -- 'template', 'adaptive_layout', 'llm'
    bank_identified     VARCHAR(200),
    template_used       VARCHAR(100),           -- Template ID if Tier 1
    extracted_fields    JSONB NOT NULL,          -- Structured extraction output
    field_confidences   JSONB NOT NULL,          -- Per-field confidence scores
    overall_confidence  DECIMAL(5,4) NOT NULL,
    processing_ms       INTEGER,
    cost_usd            DECIMAL(10,6),
    model_version       VARCHAR(50),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

/*
  extracted_fields JSONB example:
  {
    "bank_name": "Chase",
    "account_number_last4": "1234",
    "statement_period_start": "2026-01-01",
    "statement_period_end": "2026-01-31",
    "beginning_balance": 5000.00,
    "ending_balance": 4250.00,
    "total_deposits": 3000.00,
    "total_withdrawals": 3750.00,
    "large_deposits": [
      {"date": "2026-01-15", "description": "Payroll", "amount": 3000.00}
    ],
    "nsf_overdraft_count": 0
  }
*/

-- Validation results
CREATE TABLE validation_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id),
    extraction_id   UUID NOT NULL REFERENCES extraction_results(id),
    checks          JSONB NOT NULL,         -- Array of check results
    has_warnings    BOOLEAN DEFAULT FALSE,
    has_errors      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

/*
  checks JSONB example:
  [
    {"check": "balance_reconciliation", "status": "pass",
     "detail": "End = Begin + Deposits - Withdrawals"},
    {"check": "large_deposits_identified", "status": "pass"},
    {"check": "cross_doc_income_match", "status": "warning",
     "detail": "W-2 wages ($65,000) vs pay stub annualized ($67,200) - 3.4% variance"}
  ]
*/

-- Human review tracking
CREATE TABLE review_decisions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id),
    extraction_id   UUID NOT NULL REFERENCES extraction_results(id),
    reviewer_id     UUID NOT NULL REFERENCES users(id),
    decision        VARCHAR(20) NOT NULL,   -- 'approved', 'rejected', 'escalated'
    corrections     JSONB,                  -- Fields that were corrected
    notes           TEXT,
    review_duration_seconds INTEGER,
    review_queue    VARCHAR(50),            -- 'quick', 'standard', 'detailed', 'manual'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

/*
  corrections JSONB example:
  [
    {"field": "total_withdrawals", "original": 3700.00, "corrected": 3750.00,
     "reason": "OCR misread 5 as 0"}
  ]
*/

-- Immutable audit log
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_type VARCHAR(50) NOT NULL,       -- 'document', 'extraction', 'review'
    entity_id   UUID NOT NULL,
    action      VARCHAR(100) NOT NULL,       -- 'status_changed', 'field_corrected', 'approved'
    actor_type  VARCHAR(20) NOT NULL,        -- 'system', 'user'
    actor_id    VARCHAR(100),
    details     JSONB,
    ip_address  INET
);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);

-- Loan application (aggregate view)
CREATE TABLE loan_applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_number         VARCHAR(50) UNIQUE NOT NULL,
    borrower_name       VARCHAR(200),
    status              VARCHAR(50) NOT NULL DEFAULT 'documents_pending',
    total_documents     INTEGER DEFAULT 0,
    documents_approved  INTEGER DEFAULT 0,
    documents_pending   INTEGER DEFAULT 0,
    summary             JSONB,              -- AI-generated loan summary
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Template registry (for Tier 1 extraction)
CREATE TABLE extraction_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_id         VARCHAR(100) NOT NULL,
    bank_name       VARCHAR(200) NOT NULL,
    document_type   VARCHAR(100) NOT NULL,
    template_version VARCHAR(20) NOT NULL,
    template_config JSONB NOT NULL,         -- Field definitions, patterns, coordinates
    is_active       BOOLEAN DEFAULT TRUE,
    accuracy_rate   DECIMAL(5,4),           -- Tracked accuracy
    usage_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(bank_id, document_type, template_version)
);
```

### 13.2 Blob Storage Structure

```
mortgage-documents/
├── raw/                          # Original uploaded files (never modified)
│   └── {loan_id}/
│       └── {document_id}/
│           └── original.pdf
│
├── processed/                    # Preprocessed images for OCR
│   └── {document_id}/
│       ├── page_001.png
│       ├── page_002.png
│       └── metadata.json
│
├── ocr/                          # OCR output
│   └── {document_id}/
│       ├── full_text.txt
│       └── layout.json           # Text with bounding boxes
│
└── exports/                      # Approved extractions for downstream
    └── {loan_id}/
        └── extraction_package.json
```

---

## 14. Integration Architecture

### 14.1 Upstream Integrations (Document Sources)

```
┌───────────────┐    ┌──────────────┐    ┌──────────────┐
│  React Upload │    │  API / REST  │    │  SFTP / Email│
│  (Drag & Drop)│    │  (LOS Push)  │    │  (Batch)     │
└──────┬────────┘    └──────┬───────┘    └──────┬───────┘
       │                     │                   │
       └─────────────────────┼───────────────────┘
                             │
                   ┌─────────▼──────────┐
                   │  Document Service   │
                   │  (Unified Ingest)   │
                   └────────────────────┘
```

- **Web Upload**: React drag-and-drop with chunked upload for large files
- **API Integration**: REST API for LOS (Encompass, Byte, etc.) to push documents
- **SFTP/Email**: Batch ingestion for legacy workflows via Azure Logic Apps

### 14.2 Downstream Integrations (Consumers)

```
                   ┌────────────────────┐
                   │  Approved Data     │
                   │  (Post Human Review)│
                   └─────────┬──────────┘
                             │
       ┌─────────────────────┼───────────────────┐
       │                     │                   │
┌──────▼────────┐    ┌──────▼───────┐    ┌──────▼───────┐
│  LOS Export   │    │  Data Lake   │    │  Reporting   │
│  (Encompass)  │    │  (Analytics) │    │  (Power BI)  │
└───────────────┘    └──────────────┘    └──────────────┘
```

- **LOS Export**: Push approved extractions into Encompass/Byte via their APIs
- **Data Lake**: Feed processed data into Azure Data Lake for analytics
- **Reporting**: Operational dashboards via Power BI

---

## 15. Security & Compliance

### 15.1 Regulatory Requirements

| Regulation | Requirement | Implementation |
|-----------|-------------|----------------|
| **GLBA** (Gramm-Leach-Bliley) | Protect consumer financial data | Encryption at rest and in transit, access controls |
| **SOC 2 Type II** | Security, availability, processing integrity | Audit logging, access reviews, incident response |
| **ECOA / Fair Lending** | No discriminatory decisions based on protected classes | AI models audited for bias, decisions logged |
| **TRID** (TILA-RESPA) | Accurate disclosure of loan terms | Extraction accuracy validation, human review |
| **State Privacy Laws** | CCPA, etc. | Data retention policies, right to deletion |

### 15.2 Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Security Layers                                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. NETWORK                                              │
│     • Azure Virtual Network (VNet)                       │
│     • Private endpoints for all PaaS services            │
│     • NSG rules — no public access to backend services   │
│     • Azure Front Door with WAF for React app            │
│                                                          │
│  2. IDENTITY & ACCESS                                    │
│     • Azure AD / Entra ID for authentication             │
│     • RBAC: Uploader, Reviewer, Senior Reviewer, Admin   │
│     • JWT tokens with short expiry                       │
│     • MFA required for reviewer and admin roles           │
│                                                          │
│  3. DATA PROTECTION                                      │
│     • Encryption at rest: Azure Storage Service Encryption│
│     • Encryption in transit: TLS 1.3                     │
│     • SSN, account numbers: masked in UI, encrypted in DB│
│     • PII redaction in logs                              │
│     • Azure Key Vault for all secrets and API keys       │
│                                                          │
│  4. AUDIT & MONITORING                                   │
│     • Immutable audit log (append-only table)            │
│     • Every human action logged with user ID, timestamp  │
│     • Every AI decision logged with model version        │
│     • Azure Monitor alerts for anomalous patterns        │
│     • 7-year audit log retention (regulatory)            │
│                                                          │
│  5. DATA RETENTION                                       │
│     • Raw documents: retain per loan lifecycle + 7 years │
│     • Extractions: retain with loan record               │
│     • Processing artifacts (OCR cache): 90-day retention │
│     • Audit logs: 7-year minimum retention               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 15.3 PII Handling

```python
class PIIHandler:
    """
    Ensures PII is properly handled throughout the pipeline.
    """

    # Fields that contain PII and require special handling
    PII_FIELDS = {
        "ssn": {"mask": "***-**-{last4}", "log": False, "encrypt": True},
        "account_number": {"mask": "****{last4}", "log": False, "encrypt": True},
        "routing_number": {"mask": "****{last4}", "log": False, "encrypt": True},
        "date_of_birth": {"mask": "**/**/****", "log": False, "encrypt": True},
    }

    # Fields that are OK to log but should be access-controlled
    SENSITIVE_FIELDS = {
        "borrower_name", "employer_name", "address",
        "income", "wages", "balance"
    }

    def mask_for_display(self, field_name: str, value: str) -> str:
        """Mask PII for UI display. Only last 4 digits shown."""
        if field_name in self.PII_FIELDS:
            config = self.PII_FIELDS[field_name]
            last4 = value[-4:] if len(value) >= 4 else value
            return config["mask"].format(last4=last4)
        return value

    def mask_for_logging(self, field_name: str, value: str) -> str:
        """Redact PII completely for log entries."""
        if field_name in self.PII_FIELDS:
            return "[REDACTED]"
        return value
```

---

## 16. Deployment Architecture

### 16.1 Azure Infrastructure

```
┌──────────────────────────────────────────────────────────────────┐
│  Azure Subscription                                              │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Resource Group: rg-mortgage-docprocess-prod               │   │
│  │                                                            │   │
│  │  ┌─────────────┐    ┌─────────────────────────────────┐   │   │
│  │  │ Azure Front  │    │ Azure App Service (Plan: P2v3)  │   │   │
│  │  │ Door + WAF   │───▶│ - .NET API (x2 instances)       │   │   │
│  │  │ + CDN        │    │ - React Static (or SWA)         │   │   │
│  │  └─────────────┘    └───────────────┬─────────────────┘   │   │
│  │                                      │                     │   │
│  │                      ┌───────────────▼─────────────────┐   │   │
│  │                      │  Azure Service Bus (Standard)    │   │   │
│  │                      │  Topics: doc.uploaded,            │   │   │
│  │                      │  ocr.completed, classified,       │   │   │
│  │                      │  extracted, validated              │   │   │
│  │                      └───────────────┬─────────────────┘   │   │
│  │                                      │                     │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │  Azure Container Apps Environment                     │  │   │
│  │  │  (Serverless containers with auto-scale)              │  │   │
│  │  │                                                       │  │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │  │   │
│  │  │  │ OCR      │ │ Classify │ │ Extract  │ │ Validate│ │  │   │
│  │  │  │ Service  │ │ Service  │ │ Service  │ │ Service │ │  │   │
│  │  │  │ min:1    │ │ min:1    │ │ min:1    │ │ min:1   │ │  │   │
│  │  │  │ max:10   │ │ max:5    │ │ max:10   │ │ max:3   │ │  │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │  │   │
│  │  │  ┌──────────┐                                        │  │   │
│  │  │  │Summarize │  (GPU workload profile for ML models)  │  │   │
│  │  │  │ Service  │                                        │  │   │
│  │  │  │ min:0    │                                        │  │   │
│  │  │  │ max:3    │                                        │  │   │
│  │  │  └──────────┘                                        │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  │                                                            │   │
│  │  ┌──────────────────┐  ┌────────────────┐                 │   │
│  │  │ Azure PostgreSQL │  │ Azure Cache    │                 │   │
│  │  │ Flexible Server  │  │ for Redis      │                 │   │
│  │  │ (General Purpose)│  │ (Standard C1)  │                 │   │
│  │  └──────────────────┘  └────────────────┘                 │   │
│  │                                                            │   │
│  │  ┌──────────────────┐  ┌────────────────┐                 │   │
│  │  │ Azure Blob       │  │ Azure Key Vault│                 │   │
│  │  │ Storage (LRS)    │  │                │                 │   │
│  │  └──────────────────┘  └────────────────┘                 │   │
│  │                                                            │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │ Azure Monitor + Application Insights                  │  │   │
│  │  │ - Distributed tracing (end-to-end per document)       │  │   │
│  │  │ - Custom metrics (processing time, confidence, cost)  │  │   │
│  │  │ - Alerting (SLA breach, error rate spike)             │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 16.2 Environment Strategy

| Environment | Purpose | Scale | Data |
|-------------|---------|-------|------|
| **Dev** | Development & testing | Single instance each | Synthetic data |
| **QA** | Integration testing | Minimal scale | Anonymized production data |
| **Staging** | Pre-production validation | Production-like | Anonymized production data |
| **Production** | Live system | Auto-scaled | Real data |

### 16.3 CI/CD Pipeline

```
Code Push → Build → Test → Security Scan → Deploy to Staging → Approval → Deploy to Prod

.NET Services:
  GitHub/Azure DevOps → dotnet build → dotnet test → SAST/DAST → App Service Deploy

Python Services:
  GitHub/Azure DevOps → Docker build → pytest → Container scan → Container Apps Deploy

React Frontend:
  GitHub/Azure DevOps → npm build → npm test → Lighthouse → Static Web App Deploy

ML Models:
  Separate pipeline — retrain → evaluate → A/B test → promote to production
```

---

## 17. Cost Optimization Strategy

### 17.1 Cost Model (Estimated Monthly — 100K documents/month)

| Component | Strategy | Est. Monthly Cost |
|-----------|----------|-------------------|
| **OCR** | 70% Tesseract/PaddleOCR (free), 30% Azure DI | ~$4,500 |
| **Classification** | Self-hosted DistilBERT on Container Apps | ~$200 |
| **Extraction (Tier 1)** | Template-based, self-hosted | ~$100 |
| **Extraction (Tier 2)** | LayoutLM on Container Apps (GPU) | ~$1,500 |
| **Extraction (Tier 3)** | Claude API (~20% of docs) | ~$3,000 |
| **Summarization** | Claude API (per loan, not per doc) | ~$800 |
| **Azure Infrastructure** | App Service, PostgreSQL, Blob, Service Bus | ~$2,500 |
| **Total Estimate** | | **~$12,600/month** |

vs. **Pure Azure AI approach**: ~$35,000-50,000/month (all docs through Azure DI + Azure OpenAI)

### 17.2 Cost Optimization Techniques

1. **Digital PDF detection**: Skip OCR entirely for born-digital PDFs (extract text directly) — often 30-40% of documents
2. **Tiered OCR**: Free engines first, paid engines only for failures
3. **Template extraction**: Zero marginal cost for known formats
4. **Text-based LLM calls**: Send OCR text to Claude, not images (10x fewer tokens)
5. **Claude Batches API**: 50% discount for non-urgent processing (use for overnight batch runs)
6. **Prompt caching**: Cache system prompts for Claude API calls across document types
7. **Auto-scaling to zero**: Python services scale to 0 during off-hours
8. **Blob storage tiers**: Move processed documents to Cool/Archive tier after 30 days

---

## 18. Phased Delivery Roadmap

### Phase 1: Foundation & Classifier Migration (Weeks 1-8)

**Goal**: Migrate classification to composed ensemble; basic extraction pipeline for core document types

- Infrastructure setup (Azure resources, CI/CD, blob storage restructuring)
- **Classifier Ensemble Migration (Conventional + Common)**
  - Partition 75 labels into 10 functional groups in `conventional_samples/` storage
  - Train 10 sub-classifiers per loan type
  - Compose into Master Classifier; validate label consistency
  - Deploy new `TrainEnsembleClassifier` API endpoint
- .NET API scaffolding (Document Service, basic Workflow)
- Python OCR service (Tesseract + PaddleOCR + Azure DI routing)
- Azure DI prebuilt tax extraction for Schedules B, C, D, E (MGIC Rows 1-16)
- Basic MGIC field mapping engine
- Basic React upload UI + simple review UI (side-by-side view)
- PostgreSQL + tax extraction data model setup

**Document types**: W-2, 1040, Schedule C, Schedule E, Bank Statement, Pay Stub

**Success**: Upload a tax package, system classifies individual forms, extracts MGIC fields for Schedules B/C/D/E, shows in review UI

### Phase 2: Business Entity Extraction & Multi-Bank (Weeks 9-16)

**Goal**: Custom extraction for K-1/1065/1120-S; multi-bank statement handling

- **Custom extraction models** for business entity forms (K-1, Form 1065, Form 1120-S)
  - Train Azure DI custom models on annotated K-1 and 1065/1120-S samples
  - LLM fallback (Claude API) for low-confidence business form extractions
  - MGIC Rows 24-47 (Partnership + S-Corp cash flow) implementation
- **Classifier Ensemble Migration (FHA, NANQ, VALoan)**
- Multi-bank statement handling via three-tier extraction strategy
- Bank identification service
- MGIC business rules engine (ownership %, mileage depreciation, two-year comparison)
- Cross-field validation rules (W-2 income vs. 1040 AGI)
- Confidence-based routing to review queues
- Enhanced review UI (field highlighting, MGIC worksheet view)
- Feedback loop: capture corrections, store for retraining

**Document types**: Add Schedule F, K-1 (1065 + 1120-S), Form 1065, Form 1120-S, 1099-NEC, 1099-R, driver's license

**Success**: Process self-employed borrower tax package (1040 + Schedule C + K-1 + Form 1065) end-to-end with MGIC worksheet populated

### Phase 3: Full Coverage & Production Hardening (Weeks 17-24)

**Goal**: All 75 document types classified; full MGIC worksheet automation; production-ready

- **Classifier Ensemble Migration (Correspondent)** — all 6 loan types migrated
- All 47 MGIC rows extractable across all business structures
- Schedule F (Farm Income) extraction refinement
- Form 1084 (Self-Employment Income Analysis) integration
- Summarization service (per-loan AI summary using Claude API)
- Loan package view (aggregate all documents for a loan)
- Cross-document validation (W-2 vs. 1040 vs. pay stubs vs. K-1)
- Admin dashboard (analytics, accuracy tracking, cost monitoring, ensemble health)
- LOS integration (export approved MGIC data to Encompass)
- Performance optimization and load testing
- Security audit, penetration testing, SOC 2 compliance documentation

**Success**: Process 1,000 loan packages (including self-employed/partnership/S-Corp borrowers) with 85%+ straight-through rate on MGIC worksheet

### Phase 4: Optimization & Expansion (Ongoing)

- Model retraining with accumulated correction data
- Ensemble sub-model accuracy monitoring and targeted retraining
- New bank template development based on volume analysis
- A/B testing of extraction strategies
- Cost optimization (shift more to Tier 1/2, reduce LLM usage)
- New document type onboarding as needed
- Tax year schema updates (annual IRS form changes)
- Accuracy improvement targeting 95%+ straight-through rate

---

## 19. Risks & Mitigations

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| 1 | **OCR accuracy on poor scans** | Cascading extraction errors | High | Multi-engine OCR, image preprocessing, human fallback |
| 2 | **Bank format changes** | Template breakage | Medium | Version-managed templates, Tier 2/3 fallback, monitoring |
| 3 | **LLM cost overrun** | Budget breach | Medium | Tiered strategy, usage quotas, Batches API, monitoring |
| 4 | **Model drift** | Gradual accuracy degradation | Medium | Continuous monitoring, scheduled retraining, A/B testing |
| 5 | **PII data breach** | Regulatory penalty, reputation | Low | Encryption, access controls, audit logs, security reviews |
| 6 | **Vendor lock-in** (Azure AI) | Cost leverage loss | Low | Open-source first strategy, abstraction layers |
| 7 | **Scale bottlenecks** | Processing delays at peak | Medium | Auto-scaling, queue-based async architecture, load testing |
| 8 | **Compliance gaps** | Audit failures | Low | SOC 2 prep from day 1, legal review, regular audits |
| 9 | **Python/.NET integration issues** | Development friction | Medium | Well-defined API contracts, shared schema definitions, integration tests |
| 10 | **Human review bottleneck** | Backlog growth | Medium | Confidence-based routing, batch approve high-confidence, staffing model |
| 11 | **Ensemble classifier label collision** | Wrong document classification if labels overlap across sub-models | Medium | Enforce unique labels across all 10 groups; automated validation during compose |
| 12 | **IRS form layout changes (annual)** | Extraction breaks on new tax year forms | High (annual) | `form_schemas` table with versioning; annual schema update process pre-tax-season |
| 13 | **K-1/1065/1120-S custom model accuracy** | MGIC rows 24-47 require manual correction | High (initially) | LLM fallback for low-confidence; prioritize training data collection; feedback loop |
| 14 | **Multi-entity borrower complexity** | Borrower owns multiple businesses across entity types | Medium | MGIC engine supports multiple entities per type; cross-entity validation rules |
| 15 | **Azure DI training capacity re-approached** | Even with 10x capacity, growth could hit new limits | Low | Monitor per-group usage; split into finer groups if needed; hybrid with custom ML models |

---

## 20. Appendix

### 20.1 Complete Document Type Catalog (75 Labels × 10 Groups)

| Group | Category | Labels (System IDs) |
|-------|----------|-------------------|
| **Grp 01** | Application & Initial | `app_1003_init`, `app_1008`, `ack_intent`, `elec_consent`, `borrower_auth`, `2015-service_provider`, `loan_toolkit`, `lsm_init_disc`, `app_scif` |
| **Grp 02** | Appraisal & Valuation | `appr`, `appr_1004d`, `appr_air_cert`, `appr_invoice`, `appr_pod`, `appr_rov_disc`, `appr_rov_req`, `appr_ssr`, `comp_report` |
| **Grp 03** | Income (Employment) | `paystubs`, `w2_1099`, `written_voe`, `income_uw_analysis`, `income-uw-analysis` |
| **Grp 04** | Income (Tax/Business) | `tax_returns_business`, `tax-returns-personal`, `curr_pl_bs`, `cpa_cert`, `4506c-corelogic`, `irs-4506-copy-processed` |
| **Grp 05** | Identity & Eligibility | `drivers_lic`, `passport`, `ead_card`, `perm_alien`, `res_alien`, `ssn_card`, `form_ssa89`, `patriot_act_disc`, `credit_report` |
| **Grp 06** | Assets & Banking | `bank_statements`, `mortgage_stmt`, `title_emd` |
| **Grp 07** | Compliance & Legal | `anti_steering`, `ecoa`, `loan-prd-adv`, `disc_borr_cert`, `nmls_check`, `homebuyers_counsel_cert`, `homeowner_counsel`, `homeowners_counseller`, `internal_lon_ids_comp_cert` |
| **Grp 08** | Purchase Contract | `purchasecontract-contract`, `purchasecontract-addendum`, `purchasecontract-counter`, `purchasecontract-disclosure` |
| **Grp 09** | Closing & Settlement | `title_cpl`, `title_prelim_commit`, `title_tax_cert`, `title_wiring`, `disc_closing_cd`, `coc_cd`, `fee_sheet_cd`, `hud1_settlement_stmt`, `sec_lock_conf` |
| **Grp 10** | Property & Insurance | `insurance`, `flood_cert`, `fema_disaster`, `rep-cost-est`, `app_geocoding`, `app_ldp_gsa`, `desktop_uw`, `loan_estimate`, `coc_le`, `fee_sheet_le`, `agent_info` |

**Loan Type Coverage**: Conventional, Common, FHA, NANQ, VALoan, Correspondent

### 20.2 Key Performance Indicators (KPIs)

| KPI | Definition | Target | Measurement Frequency |
|-----|-----------|--------|----------------------|
| Classification Accuracy | % correctly classified | >= 95% | Daily |
| Field Extraction Accuracy | % fields correct (no correction needed) | >= 90% | Daily |
| Straight-Through Rate | % docs approved without correction | >= 85% | Daily |
| Processing Latency (P95) | Time from upload to review-ready | < 60 sec | Real-time |
| Human Review Time (avg) | Time spent per document in review | < 2 min | Weekly |
| Cost Per Document | Total processing cost / documents processed | < $0.15 | Monthly |
| System Uptime | Availability | 99.9% | Monthly |
| Template Coverage | % docs matched to Tier 1 template | >= 60% | Monthly |

### 20.3 Glossary

| Term | Definition |
|------|-----------|
| **LOS** | Loan Origination System (e.g., Encompass, Byte) |
| **DTI** | Debt-to-Income ratio |
| **VOE** | Verification of Employment |
| **AGI** | Adjusted Gross Income |
| **DI** | Azure Document Intelligence (formerly Form Recognizer) |
| **STP** | Straight-Through Processing (no human intervention needed) |
| **TRID** | TILA-RESPA Integrated Disclosure |
| **GLBA** | Gramm-Leach-Bliley Act |
| **MGIC** | Mortgage Guaranty Insurance Corporation; also refers to the SAM Cash Flow Analysis Worksheet |
| **K-1** | Schedule K-1 — IRS form reporting partner/shareholder income share |
| **Form 1065** | U.S. Partnership Return of Income |
| **Form 1120-S** | U.S. Income Tax Return for an S Corporation |
| **Schedule C** | Profit/Loss from sole proprietorship (part of 1040) |
| **Schedule E** | Supplemental income from rental real estate, royalties, partnerships, S-corps |
| **Composed Classifier** | Azure DI feature that creates an ensemble of sub-classifiers as a single logical model |
| **Master Classifier** | The top-level composed model ID that routes documents across sub-classifiers |
| **4506-C** | IRS form allowing lenders to pull official tax transcripts for verification |
| **Form 1084** | Fannie Mae worksheet for self-employment income analysis |

---

*End of Architecture Document*
