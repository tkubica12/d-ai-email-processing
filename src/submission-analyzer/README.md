# Submission Analyzer Service

## Overview
The Submission Analyzer service performs the final AI-powered analysis of complete submissions. It evaluates all processed documents together to generate insights, identify missing information, and provide recommendations for operators.

## Architecture Decisions

### Event Sourcing Pattern
- **Event Consumption**: Listens to Cosmos DB Change Feed for `SubmissionDocumentsCompleteEvent`
- **Event Publishing**: Emits `SubmissionAnalysisCompleteEvent` after analysis completion
- **Complete Context**: Accesses all processed documents for comprehensive analysis

### Data Storage
- **Analysis Results**: Stores final analysis in Cosmos DB `submissions` container
- **Document Access**: Reads processed documents from `documents` container
- **AI Integration**: Uses Azure OpenAI or other LLM services for analysis

## Analysis Capabilities

### Comprehensive Document Review
1. **Cross-Document Analysis**: Analyzes all documents in submission together
2. **Information Extraction**: Identifies key data points across multiple sources
3. **Consistency Checking**: Detects contradictions between documents
4. **Completeness Assessment**: Identifies missing required information

### AI-Powered Insights
1. **Content Classification**: Categorizes submission type and purpose
2. **Risk Assessment**: Evaluates potential issues or concerns
3. **Recommendation Generation**: Suggests next steps for operators
4. **Confidence Scoring**: Provides reliability metrics for analysis

## Responsibilities

1. **Event Processing**
   - Monitors Change Feed for `SubmissionDocumentsCompleteEvent`
   - Retrieves all processed documents for the submission
   - Accesses submission metadata and context

2. **Document Aggregation**
   - Collects processed text from all documents
   - Combines results from both processing pipelines (markitdown and foundry)
   - Builds comprehensive document corpus for analysis

3. **AI Analysis**
   - Performs intelligent analysis using LLM services
   - Generates structured insights and recommendations
   - Identifies gaps, inconsistencies, and action items
   - Produces confidence scores for findings

4. **Result Storage**
   - Stores analysis results in submission record
   - Updates submission status to completed
   - Provides structured output for operator interfaces

5. **Event Emission**
   - Emits `SubmissionAnalysisCompleteEvent` with results
   - Signals completion of processing pipeline
   - Enables operator notification and workflow triggers

## Analysis Output Schema

```json
{
  "analysisResults": {
    "submissionType": "loan_application|insurance_claim|support_request",
    "completenessScore": 0.85,
    "missingInformation": [
      "tax_identification_number",
      "supporting_financial_documents",
      "identity_verification"
    ],
    "extractedData": {
      "applicantName": "John Doe",
      "applicationAmount": 50000,
      "applicationDate": "2025-07-07"
    },
    "riskFactors": [
      "incomplete_documentation",
      "inconsistent_information"
    ],
    "recommendations": [
      "request_additional_documentation", 
      "verify_identity_information",
      "schedule_follow_up_call"
    ],
    "confidence": 0.92,
    "processingTime": "45.2s"
  },
  "status": "completed",
  "timestamp": "2025-07-07T10:00:00Z"
}
```

## Event Flow

```
SubmissionDocumentsCompleteEvent → Document Retrieval → AI Analysis
                                                            ↓
                                                    Result Storage
                                                            ↓
                                            SubmissionAnalysisCompleteEvent
```

## Technology Stack
- **Framework**: FastAPI for health checks and monitoring
- **AI Services**: Azure OpenAI for intelligent analysis
- **Event Store**: Cosmos DB Change Feed
- **Document Access**: Cosmos DB document queries
- **Authentication**: DefaultAzureCredential with Managed Identity
- **Port**: 8005 (for local development)

## Key Features
- **Intelligent Analysis**: Advanced AI-powered document understanding
- **Cross-Reference Capability**: Analyzes relationships between multiple documents
- **Structured Output**: Produces actionable insights for operators
- **Scalable Processing**: Handles varying submission sizes and complexity
- **Quality Metrics**: Provides confidence scores and processing statistics
