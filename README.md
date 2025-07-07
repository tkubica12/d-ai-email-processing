# AI Email Processing System

An Azure-based email processing system that uses AI to analyze incoming submission requests, extract information from documents, and assist operators with generating responses. The system supports both email triggers and web form submissions with file attachments.

## Architecture

The system offers two architectural approaches:
- **Workflow Orchestration**: Using Azure Logic Apps for centralized orchestration
- **Event Sourcing**: Using event-driven architecture with Cosmos DB

See [Design.md](docs/Design.md) for detailed architecture comparison and implementation options.