# API Testing with Schemathesis 🚀

Hey there! This is a README for testing our advertising platform API using Schemathesis. We've put together everything you need for automated OpenAPI specification testing - from simple checks to complex scenarios.

## 📋 What We Have

### 🗺️ OpenAPI Specification (`openapi.yaml`)
This is the heart of our API - detailed documentation of all endpoints, parameters, responses, and errors. The specification describes:

- **Campaigns**: creation, updates, pause/resume operations
- **Landing Pages**: management with A/B testing capabilities
- **Offers**: configuration with weights and payouts
- **Analytics**: detailed metrics for traffic and conversions
- **Clicks**: traffic tracking with fraud detection and 5-level sub-tracking

### 🖥️ Mock Server (`mock_server_g.py`)
A Flask application that simulates the real API. Fully compliant with OpenAPI specification:

- ✅ All endpoints implemented
- ✅ Correct HTTP response codes
- ✅ Data validation according to schemas
- ✅ Authentication support (Bearer, Basic, API-Key)
- ✅ Fraud detection for clicks
- 🔄 CORS support for browser testing

## 🧪 Testing with Schemathesis

Schemathesis is a tool for property-based testing of REST APIs. It:

1. **Reads** the OpenAPI specification
2. **Generates** test requests based on the schemas
3. **Sends** requests to the API
4. **Validates** that responses match the specification

### 🎯 Schemathesis Benefits

- **Automatic generation** of thousands of test cases
- **Edge case detection** (empty strings, null values, boundary conditions)
- **Property-based testing** - finds bugs that regular tests miss
- **CI/CD integration** with pytest
- **Detailed reports** about specification violations

## 🚀 Quick Start

### 1. Start the Mock Server

```bash
# From the goservik/ directory
python run_server_g.py
```

The server will start at `http://127.0.0.1:8000`

### 2. Install Schemathesis

```bash
pip install schemathesis
```

### 3. Basic Testing

```bash
# Test all endpoints
schemathesis run openapi.yaml --base-url=http://127.0.0.1:8000/v1

# Test only health check (quick verification)
schemathesis run openapi.yaml --base-url=http://127.0.0.1:8000/v1 --endpoint="/health"

# Test campaigns
schemathesis run openapi.yaml --base-url=http://127.0.0.1:8000/v1 --endpoint="/campaigns"
```

## 📊 Test Examples

### Health Check
```bash
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --endpoint="/health" \
  --checks=all
```

### Campaigns
```bash
# Create campaigns with various data
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --endpoint="/campaigns" \
  --checks=all \
  --hypothesis-max-examples=50
```

### Click Tracking
```bash
# Test clicks with sub-tracking
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --endpoint="/click" \
  --checks=all
```

## 🔧 Advanced Options

### Authentication
```bash
# With Bearer token
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --header="Authorization: Bearer test_jwt_token_12345"

# With API Key
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --header="X-API-Key: test_api_key_abcdef123"
```

### Filters and Limits
```bash
# GET requests only
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --method=GET

# Maximum 100 examples per endpoint
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --hypothesis-max-examples=100

# Skip certain checks
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --checks=not response_schema_conformance
```

### Reports
```bash
# JUnit XML for CI/CD
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --junit-xml=schemathesis-report.xml

# JSON report
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --output=schemathesis-report.json
```

## 🎪 What Schemathesis Checks

### ✅ Response Schema
- JSON structure matches OpenAPI schema
- Data types are correct (string, number, boolean, etc.)
- Required fields are present
- Formats are valid (email, date-time, UUID)

### ✅ HTTP Status Codes
- Correct codes for successful responses
- Proper error codes (400, 401, 404, 500)
- Headers match specification

### ✅ Parameter Validation
- Query parameters in correct format
- Path parameters are valid
- Request body matches schema

### ✅ Edge Cases
- Empty strings and null values
- Boundary values (min/max)
- Special characters
- Very long strings

## 🚨 Common Issues and Solutions

### Issue: `Connection refused`
```bash
# Server not running - start it!
python run_server_g.py
```

### Issue: `401 Unauthorized`
```bash
# Add authentication for protected endpoints
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --header="Authorization: Bearer test_jwt_token_12345"
```

### Issue: Too many tests
```bash
# Limit the number of examples
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --hypothesis-max-examples=20
```

## 📈 CI/CD Integration

### GitHub Actions Example
```yaml
name: API Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install schemathesis flask gunicorn

      - name: Start mock server
        run: |
          python run_server_g.py &
          sleep 5

      - name: Run Schemathesis tests
        run: |
          schemathesis run openapi.yaml \
            --base-url=http://127.0.0.1:8000/v1 \
            --junit-xml=schemathesis-report.xml \
            --hypothesis-max-examples=50

      - name: Upload test results
        uses: actions/upload-artifact@v2
        if: always()
        with:
          name: schemathesis-results
          path: schemathesis-report.xml
```

## 🎯 Best Practices

### 1. Start Small
```bash
# Test one endpoint first
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --endpoint="/health"
```

### 2. Use Different Authentication Levels
```bash
# Public endpoints (no auth)
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --endpoint="/health"

# Bearer token endpoints
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --endpoint="/campaigns" \
  --header="Authorization: Bearer test_jwt_token_12345"

# API Key endpoints
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --endpoint="/clicks" \
  --header="X-API-Key: test_api_key_abcdef123"
```

### 3. Monitor Coverage
```bash
# See which endpoints were tested
schemathesis run openapi.yaml \
  --base-url=http://127.0.0.1:8000/v1 \
  --show-errors-tracebacks \
  --verbosity=verbose
```

## 🎉 Conclusion

Schemathesis is a powerful tool for automated API testing. It finds bugs that are easy to miss with manual testing and ensures your API truly complies with the OpenAPI specification.

The mock server in this project is perfect for:
- API development (TDD approach)
- Client testing
- Demos and presentations
- CI/CD pipelines

Good luck with your testing! If something goes wrong - check the server logs and use `--show-errors-tracebacks` for detailed information. 🚀
