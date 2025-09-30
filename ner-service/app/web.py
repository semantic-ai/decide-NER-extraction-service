import random
from flask import jsonify, request
from datetime import datetime
import helpers as helpers
from web import app

@app.route("/hello")
def hello():
    """
    Health check endpoint for the NER service.
    
    Returns:
        JSON: Simple greeting message to verify service is running
        
    Example:
        GET /hello
        Response: {"message": "Hello from NER service!"}
    """
    return jsonify(message="Hello from NER service!")

@app.route("/test_db_connection")
def test_db_connection():
    """
    Test the database connection by running a SPARQL query.
    
    This endpoint tests the connection to the Virtuoso SPARQL database
    by executing a query for LegalExpression resources.
    
    Returns:
        JSON: Database connection test results
        
    Example:
        GET /test_db_connection
        Response: {
            "success": true,
            "message": "Database connection successful",
            "query_results": [...],
            "results_count": 5
        }
    """
    try:
        query_string = """SELECT * WHERE {
            ?s a <http://data.europa.eu/eli/ontology#LegalExpression> .
            ?s ?p ?o.
        } order by ?s limit 100"""
        
        helpers.log("Testing database connection with SPARQL query")
        result = helpers.query(query_string)
        
        if result and 'results' in result and 'bindings' in result['results']:
            bindings = result['results']['bindings']
            
            # Log the full result for debugging
            helpers.log(f"SPARQL query returned {len(bindings)} results")
            helpers.log(f"Full result structure: {result}")
            
            # Print first few results to console for inspection
            if bindings:
                helpers.log("First few results:")
                for i, binding in enumerate(bindings[:5]):  # Show first 5 results
                    helpers.log(f"Result {i+1}: {binding}")
            
            return jsonify({
                'success': True,
                'message': 'Database connection successful',
                'query_results': bindings,
                'results_count': len(bindings),
                'query': query_string.strip(),
                'full_result_structure': result,  # Include full result structure
                'sample_results': bindings[:10] if bindings else []  # Show first 10 results
            })
        else:
            helpers.log(f"No results found. Full result: {result}")
            return jsonify({
                'success': True,
                'message': 'Database connection successful but no results found',
                'query_results': [],
                'results_count': 0,
                'query': query_string.strip(),
                'full_result_structure': result
            })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        helpers.log(f"Database connection test failed: {str(e)}")
        helpers.log(f"Full error traceback: {error_details}")
        return jsonify({
            'success': False,
            'message': f'Database connection failed: {str(e)}',
            'error_details': error_details,
            'query': query_string.strip() if 'query_string' in locals() else 'N/A'
        }), 500

# =============================================================================
# NER WORKFLOW FUNCTIONS
# =============================================================================

def query_open_jobs():
    """
    Query the SPARQL triplestore for LegalExpression documents to process.
    
    PLACEHOLDER: This function retrieves actual LegalExpression documents from the database
    and randomly selects 5 for NER processing.
    
    Returns:
        list: List of document URIs to process
            
    Returns empty list if no documents found or if database connection fails.
    """
    try:
        # Query for LegalExpression documents
        sparql_query = """
        PREFIX eli: <http://data.europa.eu/eli/ontology#>
        
        SELECT DISTINCT ?document
        WHERE {
            ?document a eli:LegalExpression .
        }
        LIMIT 100
        """
        
        result = helpers.query(sparql_query)
        
        if result and 'results' in result and 'bindings' in result['results']:
            all_documents = [binding['document']['value'] for binding in result['results']['bindings']]
            
            # Randomly select 5 documents
            selected_docs = random.sample(all_documents, min(5, len(all_documents)))
            
            helpers.log(f"[PLACEHOLDER] Selected {len(selected_docs)} random documents for NER processing")
            return selected_docs
        
        return []
        
    except Exception as e:
        helpers.log(f"Error querying documents: {str(e)}")
        return []

def fetch_extracted_text(document_uri):
    """
    Fetch text content from a LegalExpression document in the database.
    
    This function retrieves the eli:decision_basis field from a LegalExpression document,
    which contains the full legal text with reasoning, background, and decision details.
    
    Args:
        document_uri (str): URI of the LegalExpression document
        
    Returns:
        dict: Result dictionary with the following structure:
            - success (bool): Whether the text was successfully retrieved
            - text (str): The extracted decision_basis text content
            - error (str): Error message (if unsuccessful)
    """
    try:
        # Query for the decision_basis text from the document
        # Note: Using the eli-dl namespace for decision_basis
        sparql_query = f"""
        PREFIX eli: <http://data.europa.eu/eli/ontology#>
        PREFIX eli-dl: <http://data.europa.eu/eli/eli-dl#>
        
        SELECT ?text
        WHERE {{
            <{document_uri}> eli-dl:decision_basis ?text .
        }}
        LIMIT 1
        """
        
        result = helpers.query(sparql_query)
        
        if result and 'results' in result and 'bindings' in result['results']:
            bindings = result['results']['bindings']
            if bindings and 'text' in bindings[0]:
                text_content = bindings[0]['text']['value']
                helpers.log(f"Fetched text from document {document_uri} ({len(text_content)} characters)")
                return {
                    'success': True,
                    'text': text_content
                }
        
        # If no decision_basis found, return error
        helpers.log(f"No text content found for document {document_uri}")
        return {
            'success': False,
            'error': 'No decision_basis text found in document'
        }
        
    except Exception as e:
        helpers.log(f"Error fetching text from {document_uri}: {str(e)}")
        return {'success': False, 'error': str(e)}

def extract_ner_entities(text, language='dutch', method='composite'):
    """
    Extract Named Entity Recognition (NER) entities from text using NLP models.
    
    This function processes the input text to identify and classify named entities
    such as persons, organizations, locations, dates, etc. It uses the refactored
    NER system with support for multiple languages and extraction methods.
    
    Args:
        text (str): The input text to process for named entity extraction
        language (str): Language of the text ('dutch', 'german', 'english')
        method (str): Extraction method ('composite', 'spacy', 'flair', 'regex')
        
    Returns:
        dict: Result dictionary with the following structure:
            - success (bool): Whether NER extraction was successful
            - entities (list): List of extracted entities (if successful)
            - processed_at (str): ISO timestamp of when processing occurred
            - language (str): Language used for extraction
            - method (str): Method used for extraction
            - error (str): Error message (if unsuccessful)
            
    Each entity in the entities list contains:
        - text (str): The actual entity text found
        - label (str): Entity type/category (PERSON, ORG, GPE, DATE, etc.)
        - start (int): Character position where entity starts in text
        - end (int): Character position where entity ends in text
        - confidence (float): Confidence score (0.0 to 1.0)
        
    Example return (success):
        {
            "success": True,
            "entities": [
                {"text": "John Doe", "label": "PERSON", "start": 65, "end": 73, "confidence": 0.95},
                {"text": "Microsoft", "label": "ORG", "start": 75, "end": 84, "confidence": 0.98}
            ],
            "processed_at": "2025-09-23T10:30:15.123456",
            "language": "dutch",
            "method": "composite"
        }
        
    Example return (failure):
        {
            "success": False,
            "error": "NLP model failed to load",
            "language": "dutch",
            "method": "composite"
        }
    """
    try:
        # Import the new NER functions
        from .ner_functions import extract_entities
        
        # Extract entities using the new system
        entities = extract_entities(text, language=language, method=method)
        
        helpers.log(f"Extracted {len(entities)} entities from text using {method} method for {language}")
        return {
            'success': True,
            'entities': entities,
            'processed_at': datetime.now().isoformat(),
            'language': language,
            'method': method
        }
        
    except Exception as e:
        helpers.log(f"Error extracting NER entities ({language}/{method}): {str(e)}")
        return {
            'success': False, 
            'error': str(e),
            'language': language,
            'method': method
        }

def save_ner_results(document_uri, entities):
    """
    Save extracted NER entities and results to the SPARQL triplestore.
    
    PLACEHOLDER: This function currently only logs the entities that would be saved.
    Actual database storage will be implemented when the NER entity schema is defined.
    
    Args:
        document_uri (str): URI of the LegalExpression document that was processed
        entities (list): List of entity dictionaries from extract_ner_entities()
        
    Returns:
        dict: Result dictionary with structure:
            - success (bool): Always True (placeholder)
            - entities_saved (int): Number of entities that would be saved
    """
    try:
        # Log the entities for now (placeholder for actual saving)
        helpers.log(f"[PLACEHOLDER] Would save {len(entities)} NER entities for document {document_uri}")
        
        # Log a sample of entities for debugging
        if entities:
            helpers.log(f"[PLACEHOLDER] Sample entities: {entities[:3]}")
        
        return {'success': True, 'entities_saved': len(entities)}
        
    except Exception as e:
        helpers.log(f"Error in save_ner_results placeholder: {str(e)}")
        return {'success': False, 'error': str(e)}

def notify_job_completion(document_uri, success=True, error_message=None):
    """
    Notify about document processing completion status.
    
    PLACEHOLDER: This function currently only logs the completion status.
    Actual job status tracking will be implemented when the job management schema is defined.
    
    Args:
        document_uri (str): URI of the LegalExpression document that was processed
        success (bool, optional): Whether processing completed successfully
        error_message (str, optional): Error message if processing failed
        
    Returns:
        dict: Result dictionary with structure:
            - success (bool): Always True (placeholder)
            - status (str): "completed" or "failed"
    """
    try:
        status = "completed" if success else "failed"
        
        if success:
            helpers.log(f"[PLACEHOLDER] Document {document_uri} processing completed successfully")
        else:
            helpers.log(f"[PLACEHOLDER] Document {document_uri} processing failed: {error_message}")
        
        return {'success': True, 'status': status}
        
    except Exception as e:
        helpers.log(f"Error in notify_job_completion placeholder: {str(e)}")
        return {'success': False, 'error': str(e)}

# =============================================================================
# NER WORKFLOW ENDPOINTS
# =============================================================================

@app.route("/ner/process-jobs", methods=['POST'])
def process_ner_jobs():
    """
    Main workflow endpoint to process all pending NER jobs.
    
    This is the core endpoint that orchestrates the complete NER workflow:
    1. Queries the triplestore for pending NER jobs
    2. For each job, fetches the extracted text from the document service
    3. Processes the text through NER models to extract named entities
    4. Saves the extracted entities back to the triplestore
    5. Updates the job status to completed or failed
    
    This endpoint processes jobs in sequence and provides detailed results
    for each job including success/failure status and any errors encountered.
    
    HTTP Method: POST
    Content-Type: application/json (optional, no request body needed)
    
    Returns:
        JSON: Comprehensive processing results with structure:
            - message (str): Summary message
            - jobs_processed (int): Total number of jobs found and processed
            - successful (int): Number of jobs that completed successfully
            - failed (int): Number of jobs that failed processing
            - results (list): Detailed results for each processed job
            
    Each job result in the results array contains:
        - document_uri (str): URI of the processed document
        - success (bool): Whether the job completed successfully
        - entities_found (int): Number of entities extracted (if successful)
        - entities_saved (int): Number of entities saved to database (if successful)
        - error (str): Error message (if unsuccessful)
        
    Example successful response:
        {
            "message": "Processed 2 NER jobs",
            "jobs_processed": 2,
            "successful": 2,
            "failed": 0,
            "results": [
                {
                    "document_uri": "abc123",
                    "success": true,
                    "entities_found": 3,
                    "entities_saved": 3
                }
            ]
        }
        
    Example response with no jobs:
        {
            "message": "No pending NER jobs found",
            "jobs_processed": 0
        }
        
    Error responses:
        HTTP 500: {"errors": [{"detail": "Failed to process NER jobs: <error>", "status": 500}]}
        
    Note:
        This endpoint requires a running SPARQL triplestore database. Jobs that
        fail individual steps (text fetching, NER extraction, saving) will be
        marked as failed in the database and reported in the results.
    """
    try:
        # Step 1: Query for documents to process
        documents = query_open_jobs()
        
        if not documents:
            return jsonify({
                'message': 'No documents found to process',
                'documents_processed': 0
            })
        
        processed_documents = []
        
        # Process each document
        for document_uri in documents:
            doc_result = {'document_uri': document_uri, 'success': False}
            
            try:
                # Step 2: Fetch text content
                text_result = fetch_extracted_text(document_uri)
                if not text_result['success']:
                    notify_job_completion(document_uri, False, text_result.get('error'))
                    doc_result['error'] = f"Failed to fetch text: {text_result.get('error')}"
                    processed_documents.append(doc_result)
                    continue
                
                # Step 3: Extract NER entities (using configured defaults)
                from .ner_config import DEFAULT_SETTINGS
                ner_result = extract_ner_entities(
                    text_result['text'], 
                    language=DEFAULT_SETTINGS['language'], 
                    method=DEFAULT_SETTINGS['method']
                )
                if not ner_result['success']:
                    notify_job_completion(document_uri, False, ner_result.get('error'))
                    doc_result['error'] = f"Failed to extract entities: {ner_result.get('error')}"
                    processed_documents.append(doc_result)
                    continue
                
                # Step 4: Save results (placeholder for now)
                save_result = save_ner_results(document_uri, ner_result['entities'])
                if not save_result['success']:
                    notify_job_completion(document_uri, False, save_result.get('error'))
                    doc_result['error'] = f"Failed to save results: {save_result.get('error')}"
                    processed_documents.append(doc_result)
                    continue
                
                # Step 5: Mark as completed
                notify_job_completion(document_uri, True)
                
                doc_result['success'] = True
                doc_result['entities_found'] = len(ner_result['entities'])
                doc_result['entities_saved'] = save_result['entities_saved']
                
            except Exception as e:
                helpers.log(f"Error processing document {document_uri}: {str(e)}")
                notify_job_completion(document_uri, False, str(e))
                doc_result['error'] = str(e)
            
            processed_documents.append(doc_result)
        
        successful = [d for d in processed_documents if d['success']]
        
        return jsonify({
            'message': f'Processed {len(documents)} documents',
            'documents_processed': len(documents),
            'successful': len(successful),
            'failed': len(documents) - len(successful),
            'results': processed_documents
        })
        
    except Exception as e:
        helpers.log(f"Error in process_ner_jobs: {str(e)}")
        return helpers.error(f"Failed to process documents: {str(e)}", 500)

# NOTE: /ner/jobs endpoint removed - will be implemented when job tracking schema is defined

@app.route("/ner/demo", methods=['POST'])
def demo_ner_workflow():
    """
    Test NER extraction using mock data without database dependency.
    
    This endpoint allows you to test the NER extraction functionality independently
    from the database. It uses a real Gemeente Zonnedorp municipal document as mock
    data, making it perfect for development, testing, and demonstrations.
    
    **Use Cases:**
    - Quick NER testing without Virtuoso database running
    - Testing different NER methods (regex, spacy, composite) and languages
    - Development and debugging of NER extraction logic
    - Demonstrations with predictable, controlled results
    - CI/CD automated tests without database setup
    - API documentation examples
    
    **Comparison with `/ner/process-jobs`:**
    - `/ner/process-jobs`: Processes real documents from the database
    - `/ner/demo`: Uses mock document, no database required
    
    HTTP Method: POST
    Content-Type: application/json
    
    Request body (optional):
        {
            "language": "dutch",  // Language for NER extraction (dutch, german, english)
            "method": "regex"     // NER method (regex, spacy, flair, composite)
        }
    
    Returns:
        JSON: Complete workflow demonstration results with structure:
            - message (str): Success message
            - demo_mode (bool): Always true, indicates this is a demonstration
            - workflow_completed (bool): Whether the full workflow completed
            - job_id (str): Mock job identifier
            - steps_completed (list): List of workflow steps that completed
            - entities_found (int): Number of entities extracted
            - entities (list): Full list of extracted entities with details
            - text_processed (str): The mock document text that was processed
            - language (str): Language used for extraction
            - method (str): NER method used
            - processed_at (str): ISO timestamp
            
    Example successful response:
        {
            "message": "Complete NER Workflow Demo Successful",
            "demo_mode": true,
            "workflow_completed": true,
            "job_id": "demo-job-1",
            "entities_found": 4,
            "entities": [
                {"text": "12 februari 2025", "label": "DATE", "start": 93, "end": 106},
                {"text": "22 december 2017", "label": "DATE", "start": 435, "end": 448}
            ],
            "text_processed": "Gemeente Zonnedorp...",
            "language": "dutch",
            "method": "regex",
            "processed_at": "2025-01-15T10:30:00.123456"
        }
        
    Error responses:
        HTTP 500: {"errors": [{"detail": "Demo workflow failed: <error>", "status": 500}]}
        
    Note:
        This endpoint uses mock Gemeente Zonnedorp municipal document as mock data,
        providing realistic NER extraction results. It does not require any external
        dependencies and demonstrates the complete production workflow.
    """
    try:
        # Get request parameters for NER configuration
        from .ner_config import DEFAULT_SETTINGS
        data = request.get_json() or {}
        language = data.get('language', DEFAULT_SETTINGS['language'])
        method = data.get('method', DEFAULT_SETTINGS['method'])
        
        helpers.log("[DEMO] Starting complete NER workflow demonstration")
        
        # Step 1: Create NER job (simulated)
        mock_job = {
            'job_uri': 'http://mu.semte.ch/services/ner-jobs/demo-job-1',
            'job_id': 'demo-job-1',
            'text_source': 'http://mu.semte.ch/services/documents/gent-besluit-1',
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        helpers.log(f"[DEMO] Step 1: Created NER job {mock_job['job_id']}")
        
        # Step 2: Delta notify change - dispatch trigger (simulated)
        helpers.log("[DEMO] Step 2: Delta notify change - workflow triggered")
        
        # Step 3: Query open jobs (finds our mock job)
        helpers.log("[DEMO] Step 3: Querying for open jobs - found 1 pending job")
        
        # Step 4: Fetch extracted text (use real mock data)
        helpers.log(f"[DEMO] Step 4: Fetching extracted text for job {mock_job['job_id']}")
        from .mock_data import GENT_BESLUIT
        
        # Step 5: Write NER annotations (extract entities)
        helpers.log(f"[DEMO] Step 5: Extracting NER entities using {method} method for {language}")
        ner_result = extract_ner_entities(GENT_BESLUIT, language=language, method=method)
        
        if not ner_result['success']:
            return helpers.error(f"NER extraction failed: {ner_result.get('error', 'Unknown error')}", 500)
        
        entities_count = len(ner_result['entities'])
        helpers.log(f"[DEMO] Step 5: Extracted {entities_count} entities, simulating database save")
        
        # Step 6: Job done (mark as completed)
        helpers.log(f"[DEMO] Step 6: Marking job {mock_job['job_id']} as completed")
        
        # Step 7: Dispatch completion notification (simulated)
        helpers.log("[DEMO] Step 7: Dispatching job completion notification")
        
        return jsonify({
            'message': 'Complete NER Workflow Demo Successful',
            'demo_mode': True,
            'workflow_completed': True,
            'job_id': mock_job['job_id'],
            'entities_found': entities_count,
            'entities': ner_result['entities'],
            'text_processed': GENT_BESLUIT,
            'language': language,
            'method': method,
            'processed_at': ner_result.get('processed_at', datetime.now().isoformat()),
            'document_type': 'Municipal decision from Gemeente Zonnedorp'
        })
        
    except Exception as e:
        helpers.log(f"[DEMO] Error in workflow demonstration: {str(e)}")
        return helpers.error(f"Demo workflow failed: {str(e)}", 500)
