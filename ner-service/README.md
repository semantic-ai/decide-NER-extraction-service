# Named Entity Recognition (NER) Service

A Flask-based microservice for Named Entity Recognition built on the `mu-python-template` framework. This service provides multiple NER methods including spaCy and regex-based extraction with support for multiple languages.

## Features

- **Multiple NER Methods**: spaCy, Regex, and Composite extraction
- **Multi-language Support**: Dutch, German, English with extensible configuration
- **Flexible Architecture**: Modular design with configurable regex patterns
- **SPARQL Integration**: Built-in support for triplestore operations
- **Demo Mode**: Test endpoints with mock data for development

## Quick Start

### Prerequisites

Create the shared Docker network (if not already created):
```bash
docker network create mu-python-network
```

### Using Docker Compose (Recommended)

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Using Docker Build

```bash
# Build the Docker container
docker build -t ner-service ./ner-service

# Run the service
docker run --rm -p 8080:80 ner-service
```

### Test the Service

```powershell
# Health check
Invoke-WebRequest -Uri "http://localhost:8080/hello"

# Test database connection
Invoke-WebRequest -Uri "http://localhost:8080/test_db_connection"

# Demo NER extraction (no database required)
Invoke-WebRequest -Uri "http://localhost:8080/ner/demo" -Method POST -ContentType "application/json" -Body '{"language": "dutch", "method": "regex"}'

# Process real documents from database
Invoke-WebRequest -Uri "http://localhost:8080/ner/process-jobs" -Method POST -ContentType "application/json"
```

## API Endpoints

### Core NER Endpoints

#### 1. Demo Endpoint (Database-Free Testing)
`POST /ner/demo` - Test NER extraction using mock data without database dependency.

**Parameters**:
- `language`: `"dutch"`, `"german"`, `"english"` (default: Dutch, configured in `ner_config.py`)
- `method`: `"regex"`, `"spacy"`, `"composite"` (default: Regex, configured in `ner_config.py`)

**Use Cases**: Quick testing, development, debugging, CI/CD tests

#### 2. Process Jobs (Production)
`POST /ner/process-jobs` - Process real LegalExpression documents from database.

**Features**: Queries for documents, fetches `eli-dl:decision_basis` text, extracts entities, processes 5 random documents per request

#### 3. Utility Endpoints
- `GET /hello` - Service health check
- `GET /test_db_connection` - Test SPARQL database connection

## Language Support

```powershell
# Dutch (default)
Invoke-WebRequest -Uri "http://localhost:8080/ner/demo" -Method POST -ContentType "application/json" -Body '{"language": "dutch", "method": "regex"}'

# German  
Invoke-WebRequest -Uri "http://localhost:8080/ner/demo" -Method POST -ContentType "application/json" -Body '{"language": "german", "method": "regex"}'

# English
Invoke-WebRequest -Uri "http://localhost:8080/ner/demo" -Method POST -ContentType "application/json" -Body '{"language": "english", "method": "spacy"}'
```

### View Extracted Entities (Formatted)

To see the extracted entities in a nice table format:

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8080/ner/demo" -Method POST -ContentType "application/json" -Body '{"language": "english", "method": "spacy"}'; $json = $response.Content | ConvertFrom-Json; Write-Host "`n=== NER EXTRACTION RESULTS ===" -ForegroundColor Cyan; Write-Host "Language: $($json.language)" -ForegroundColor Green; Write-Host "Method: $($json.method)" -ForegroundColor Green; Write-Host "Entities Found: $($json.entities_found)" -ForegroundColor Green; Write-Host "`n=== EXTRACTED ENTITIES ===" -ForegroundColor Cyan; $json.entities | Select-Object text, label, confidence | Format-Table -AutoSize
```

For processing real documents:

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8080/ner/process-jobs" -Method POST -ContentType "application/json"; $json = $response.Content | ConvertFrom-Json; Write-Host "`n=== PROCESSING SUMMARY ===" -ForegroundColor Cyan; Write-Host "Documents Processed: $($json.documents_processed)" -ForegroundColor Green; Write-Host "Successful: $($json.successful)" -ForegroundColor Green; Write-Host "Failed: $($json.failed)" -ForegroundColor Yellow; Write-Host "`n=== RESULTS ===" -ForegroundColor Cyan; $json.results | Format-Table -Property document_uri, success, entities_found, entities_saved -AutoSize
```

## Expected Results

### Regex Method (Recommended)
The regex method works excellently for Dutch date extraction:

```json
{
  "entities": [
    {
      "confidence": 1.0,
      "end": 106,
      "label": "DATE",
      "start": 93,
      "text": "februari 2025"
    },
    {
      "confidence": 1.0,
      "end": 448,
      "label": "DATE", 
      "start": 435,
      "text": "december 2017"
    }
  ],
  "language": "dutch",
  "method": "regex",
  "success": true
}
```

### Demo Workflow
Complete workflow processing with all steps:

```json
{
  "demo_mode": true,
  "jobs_processed": 1,
  "successful": 1,
  "failed": 0,
  "results": [
    {
      "job_id": "demo-job-1",
      "success": true,
      "entities_found": 4,
      "steps_completed": [
        "Query open jobs",
        "Fetch extracted text", 
        "Extract NER entities",
        "Save results (simulated)",
        "Mark job completed (simulated)"
      ]
    }
  ]
}
```

## Configuration

### Environment Variables

The service is configured via environment variables in `docker-compose.yml`:

| Variable | Description | Default/Example |
|----------|-------------|-----------------|
| `MODE` | Development or production mode | `development` |
| `APP_ENTRYPOINT` | Entry point module name | `web` |
| `MU_APPLICATION_GRAPH` | SPARQL application graph URI | `http://mu.semte.ch/application` |
| `MU_SPARQL_ENDPOINT` | SPARQL query endpoint URL | `http://app-decide-virtuoso-1:8890/sparql` |
| `MU_SPARQL_UPDATE_ENDPOINT` | SPARQL update endpoint URL | `http://app-decide-virtuoso-1:8890/sparql` |

**Note**: Update the SPARQL endpoint URLs to match your Virtuoso database container name.

### Network Configuration

The service connects to other microservices via the `mu-python-network` Docker network:

```yaml
networks:
  mu-python-network:
    external: true
```

**Setup**: Create the network before starting the service:
```bash
docker network create mu-python-network
```

### Default NER Settings
The service uses centralized configuration in `ner_config.py`:
- **Default Language**: `"dutch"`
- **Default Method**: `"regex"`
- **Deduplication**: `true` (removes duplicate entities)
- **Min Confidence**: `0.5` (minimum confidence threshold)
- **Max Entities**: `1000` (maximum entities per request)

### Supported NER Methods
- **regex**: Pattern-based extraction (excellent for dates)
- **spacy**: ML-based comprehensive entity recognition
- **composite**: Combines spaCy + regex for best results

### Supported Entity Types
- **DATE**: Dates in various formats (regex/spaCy)
- **PERSON**: Person names (spaCy)
- **ORG**: Organizations (spaCy)
- **GPE**: Geopolitical entities (spaCy)
- **CARDINAL**: Numbers (spaCy)
- **EVENT**: Events (spaCy)

### Language-Specific Regex Patterns
- **Dutch dates**: `\d{1,2}\s+(?:januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)\s+\d{4}`
- **German dates**: `\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}`
- **English dates**: `(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}`

## Development

### Project Structure
```
ner-service/
├── app/
│   ├── web.py              # Main Flask application
│   ├── ner_config.py       # Configuration and regex patterns
│   ├── ner_models.py       # Model loading and caching
│   ├── ner_extractors.py   # Extraction logic
│   ├── ner_functions.py    # High-level NER functions
│   └── mock_data.py        # Test data
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
└── README.md              # This file
```
### Mock Data
The service includes a mock Gemeente Zonnedorp municipal decision document (Dutch) for testing.

## Troubleshooting

### Common Issues

1. **Container not starting**: Check if port 8080 is available
2. **Database connection failed**: 
   - Verify Virtuoso database is running and accessible
   - Check `MU_SPARQL_ENDPOINT` environment variable matches your database container name
   - Ensure both services are on the same Docker network (`mu-python-network`)
   - Test connection: `curl http://localhost:8080/test_db_connection`
3. **Network error**: 
   - Create the network: `docker network create mu-python-network`
   - Verify network exists: `docker network ls`
   - Check services are connected: `docker network inspect mu-python-network`
4. **spaCy returns 0 entities**: The model may need specific configuration for your use case
5. **Regex not matching**: Check language-specific patterns in `ner_config.py`
