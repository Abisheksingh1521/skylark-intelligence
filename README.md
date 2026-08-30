# Skylark Intelligence

An AI-powered business intelligence assistant that allows users to query live business data using natural language.

Skylark Intelligence combines **Google Gemini**, **Monday.com**, and **Streamlit** to provide conversational analytics over Deals and Work Orders data.

---

## 🚀 Features

- Natural-language business analytics
- Live data retrieval from Monday.com
- Gemini-powered reasoning and response generation
- Gemini function/tool calling
- Manual tool execution through `AnalyticsToolExecutor`
- Pipeline and work-order analytics
- Accounts receivable and risk analysis
- Conversational query history
- Streamlit-based interactive dashboard
- Data-quality caveats in analytical responses
- Graceful handling of API and authentication failures

---

## 🏗️ Architecture

```text
                    ┌──────────────────────┐
                    │      User Query      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Streamlit       │
                    │       Web App        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    SkylarkBIAgent    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Google Gemini    │
                    │   Function Calling   │
                    └──────────┬───────────┘
                               │
                         Tool Call
                               │
                               ▼
                    ┌──────────────────────┐
                    │ AnalyticsToolExecutor│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Monday.com      │
                    │    Live Business     │
                    │        Data          │
                    └──────────┬───────────┘
                               │
                         Analytics
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Gemini Response    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Streamlit UI      │
                    └──────────────────────┘
