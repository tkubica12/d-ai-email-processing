# Company APIs Service

Business-specific APIs providing internal company data and functionality for AI agents. This service generates mock data for demonstration purposes and exposes internal company information through RESTful APIs.

## Features

- **User Products API**: Retrieve user's active products and subscriptions
- **Financial Score API**: Get user's financial health scores with multiple scoring types
- **Income Data API**: Access aggregated income data with configurable time periods and granularity
- **Mock Data Generation**: Consistent, realistic mock data for testing and demonstration
- **OpenAPI Documentation**: Full API documentation with interactive testing interface

## API Endpoints

### Health Check
- `GET /health` - Service health status

### User Products
- `GET /api/v1/users/{userId}/products` - Get user's products and subscriptions

### Financial Score
- `GET /api/v1/users/{userId}/financial-score` - Get user's financial score
  - Query parameters:
    - `scoreType`: `composite` (default), `creditworthiness`, `liquidity`, `stability`, `growth`

### Income Data
- `GET /api/v1/users/{userId}/income` - Get user's income data
  - Query parameters:
    - `startDate`: Start date (ISO 8601 format)
    - `endDate`: End date (ISO 8601 format)
    - `granularity`: `daily`, `weekly`, `monthly` (default), `yearly`

## Running the Service

### Prerequisites
- Python 3.12 or higher
- UV package manager (recommended) or pip

### Installation
```bash
# Install dependencies
uv sync

# Or with pip
pip install -r requirements.txt
```

### Development
```bash
# Run with auto-reload
uv run python main.py

# Or with uvicorn directly
uv run uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### Configuration
Set environment variables in `.env` file:
```bash
LOG_LEVEL=DEBUG
PORT=8003
```

## API Documentation

When running locally, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc

## Testing

Use the provided `test-api.http` file with VS Code REST Client extension or similar tools.

### Example Requests

```bash
# Get user products
curl -X GET "http://localhost:8003/api/v1/users/john.doe@example.com/products" \
  -H "Authorization: Bearer test-token-123"

# Get financial score
curl -X GET "http://localhost:8003/api/v1/users/john.doe@example.com/financial-score?scoreType=composite" \
  -H "Authorization: Bearer test-token-123"

# Get income data
curl -X GET "http://localhost:8003/api/v1/users/john.doe@example.com/income?startDate=2025-01-01T00:00:00Z&endDate=2025-07-31T23:59:59Z&granularity=monthly" \
  -H "Authorization: Bearer test-token-123"
```

## Mock Data

The service generates consistent, realistic mock data using the following approach:

- **Seeded Random Generation**: Uses user ID as seed for consistent results per user
- **Realistic Product Pools**: Predefined product names and features by category
- **Financial Score Factors**: Category-specific scoring factors with weighted impacts
- **Income Patterns**: Realistic income patterns with multiple sources and growth trends

## Authentication

The service uses Bearer token authentication. For development/testing, any token is accepted. In production, this would integrate with Azure AD for JWT validation.

## Error Handling

The API returns structured error responses with appropriate HTTP status codes:
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not Found (user not found)
- `500` - Internal Server Error

## Integration

This service is designed to be consumed by AI agents in the submission analysis process, providing business context and user-specific data for intelligent decision making.