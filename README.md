# 🚀 Skylark Intelligence

### AI-Powered Business Intelligence Assistant

Skylark Intelligence is an AI-powered business intelligence application that enables users to interact with live business data using natural language.

Instead of manually searching through business records, users can ask questions such as:

> "What is our open and weighted pipeline?"

> "How many active work orders do we have?"

> "Which sectors have high AR risk and outstanding receivables?"

The application uses **Google Gemini** to understand the user's question and determine which business analytics function should be executed. The requested information is retrieved from **Monday.com**, processed by the application's analytics layer, and returned as a concise natural-language response through the Streamlit interface.

---

# 📌 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Application Workflow](#-application-workflow)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [AI and Function Calling](#-ai-and-function-calling)
- [Monday.com Integration](#-mondaycom-integration)
- [Analytics Layer](#-analytics-layer)
- [Data Quality](#-data-quality)
- [Error Handling](#-error-handling)
- [Environment Configuration](#-environment-configuration)
- [Local Installation](#-local-installation)
- [Running the Application](#-running-the-application)
- [Testing](#-testing)
- [Integration Verification](#-integration-verification)
- [Example Queries](#-example-queries)
- [Deployment](#-deployment)
- [Security](#-security)
- [Verification Status](#-verification-status)
- [Future Improvements](#-future-improvements)

---

# 📖 Overview

Skylark Intelligence provides a conversational interface for business analytics.

The application connects three major components:

1. **Streamlit** – Provides the interactive web interface.
2. **Google Gemini** – Provides natural-language understanding and function calling.
3. **Monday.com** – Provides live business data for analytics.

The application also contains an analytics and tool-execution layer that acts as the bridge between Gemini and Monday.com.

This architecture allows the AI model to reason about the user's request without giving the model direct access to the underlying business system.

---

# ✨ Key Features

## 🤖 Natural Language Analytics

Users can ask business questions using normal conversational language instead of writing queries or navigating through multiple dashboards.

Example:

```text
What is our open and weighted pipeline?
