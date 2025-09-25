# LangConnect CLI

A powerful command-line interface to interact with the LangConnect API, designed for managing collections, documents, and performing various operations on your LangConnect instance.

## Features

- **Authentication**: Sign in, sign up, sign out, and token management
- **Collection Management**: Create, list, get, and delete collections
- **Document Operations**: Search documents with semantic, keyword, or hybrid search
- **Data Processing**: Split CSV files into individual documents for ingestion
- **API Operations**: Perform GET, POST, DELETE requests to any endpoint
- **Health Monitoring**: Check API health status
- **User Management**: Get current user information

## Installation

1. **Clone and setup the environment**:
   ```bash
   git clone <repository-url>
   cd langconnect-cli
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   Create a `.env` file in the project root with your LangConnect credentials:
   ```env
   LANGCONNECT_BASE_URL=https://your-langconnect-instance.com
   LANGCONNECT_API_KEY=your-api-key
   LANGCONNECT_ADMIN_EMAIL=your-admin@email.com
   LANGCONNECT_ADMIN_PASSWORD=your-password
   ```

## Usage

### Basic Command Structure

```bash
python -m langconnect_cli [COMMAND] [OPTIONS] [ARGUMENTS]
```

### Global Options

- `-v, --verbose`: Increase verbosity (can be repeated: `-v`, `-vv`, `-vvv`)
- `--help`: Show help message

### Authentication Commands

#### Sign In
Authenticate with LangConnect using admin credentials from `.env`:
```bash
python -m langconnect_cli signin
```

#### Sign Up
Create a new user account:
```bash
python -m langconnect_cli signup --email user@example.com --password
```
*Note: Password will be prompted securely*

#### Sign Out
Sign out the current user:
```bash
python -m langconnect_cli signout
```

#### Refresh Token
Refresh the current access token:
```bash
python -m langconnect_cli refresh-token
```

#### Get Current User
Get information about the currently authenticated user:
```bash
python -m langconnect_cli me
```

### Collection Management

#### List Collections
Display all available collections:
```bash
python -m langconnect_cli list-collections
```

#### Create Collection
Create a new collection with optional metadata:
```bash
# Basic collection
python -m langconnect_cli create-collection "My Collection"

# With metadata
python -m langconnect_cli create-collection "Medical Data" --metadata '{"description": "Medical records collection", "version": "1.0"}'
```

#### Get Collection Details
Retrieve details of a specific collection:
```bash
python -m langconnect_cli get-collection <collection-uuid>
```

#### Delete Collection
Remove a collection permanently:
```bash
python -m langconnect_cli delete-collection <collection-uuid>
```

### Document Operations

#### Search Documents
Search for documents within a collection using different search types:

```bash
# Semantic search (default)
python -m langconnect_cli search-documents <collection-uuid> "diabetes treatment" --limit 5

# Keyword search
python -m langconnect_cli search-documents <collection-uuid> "insulin" --type keyword --limit 10

# Hybrid search
python -m langconnect_cli search-documents <collection-uuid> "patient symptoms" --type hybrid --limit 20
```

**Search Options:**
- `--limit, -l`: Maximum number of results (default: 10)
- `--type, -t`: Search type - `semantic`, `keyword`, or `hybrid` (default: semantic)

### Data Processing

#### Split CSV Files
Convert CSV files into individual document files for easier ingestion:

```bash
# Split a single CSV file
python -m langconnect_cli split data.csv

# Custom output directory
python -m langconnect_cli split data.csv --output my_documents

# Split all CSV files in a folder
python -m langconnect_cli split ./csv_files/

# Custom file pattern
python -m langconnect_cli split ./data/ --pattern "*.csv"
```

**Split Options:**
- `--output, -o`: Output directory for split documents (default: "split_documents")
- `--pattern, -p`: File pattern to match when input is a folder (default: "*.csv")

Each output document will contain:
- The original CSV header row
- One data row from the CSV file
- Numbered sequentially (e.g., `document_00001.txt`, `document_00002.txt`)

### Generic API Operations

#### GET Requests
Perform GET requests to any API endpoint:
```bash
# Simple GET
python -m langconnect_cli get projects

# With query parameters
python -m langconnect_cli get users --param status=active --param limit=50

# Nested endpoints
python -m langconnect_cli get auth/me
```

#### POST Requests
Create resources using POST requests:
```bash
# With JSON payload
python -m langconnect_cli post users --json '{"email": "user@example.com", "name": "John Doe"}'

# With form data
python -m langconnect_cli post projects --data name="New Project" --data status=active
```

#### DELETE Requests
Remove resources using DELETE requests:
```bash
# Simple delete
python -m langconnect_cli delete users/123

# With parameters
python -m langconnect_cli delete projects/456 --param force=true
```

### System Commands

#### Health Check
Check the API health status:
```bash
python -m langconnect_cli health
```

## Advanced Usage

### Verbosity Levels
Control the amount of logging output:
```bash
# Warning level (default)
python -m langconnect_cli signin

# Info level
python -m langconnect_cli signin -v

# Debug level
python -m langconnect_cli signin -vv
```

### Chaining Commands
You can chain multiple operations in scripts:
```bash
#!/bin/bash
# Authenticate and create a collection
python -m langconnect_cli signin
python -m langconnect_cli create-collection "Medical Records"
python -m langconnect_cli list-collections
```

### Working with JSON Responses
All responses are formatted as JSON for easy parsing:
```bash
# Save response to file
python -m langconnect_cli list-collections > collections.json

# Pipe to jq for processing
python -m langconnect_cli search-documents <uuid> "query" | jq '.results[].content'
```

## Common Workflows

### 1. Setting up a new collection with data
```bash
# 1. Authenticate
python -m langconnect_cli signin

# 2. Create collection
python -m langconnect_cli create-collection "Medical Data"

# 3. Split CSV data into documents
python -m langconnect_cli split medical_data.csv --output medical_docs

# 4. Upload documents (using upload script or API calls)
# 5. Search the collection
python -m langconnect_cli search-documents <collection-id> "diabetes"
```

### 2. Data exploration and search
```bash
# Check what collections exist
python -m langconnect_cli list-collections

# Get details of a specific collection
python -m langconnect_cli get-collection <uuid>

# Perform different types of searches
python -m langconnect_cli search-documents <uuid> "patient symptoms" --type semantic
python -m langconnect_cli search-documents <uuid> "diabetes" --type keyword
python -m langconnect_cli search-documents <uuid> "treatment options" --type hybrid
```

## Error Handling

The CLI provides clear error messages and appropriate exit codes:
- **Exit code 0**: Success
- **Exit code 1**: Error (authentication, network, validation, etc.)

Common error scenarios:
- Missing or invalid `.env` configuration
- Network connectivity issues
- Invalid JSON payloads
- Authentication failures
- Invalid UUIDs or endpoints

## Troubleshooting

1. **Authentication Issues**:
   - Verify `.env` file exists and contains correct credentials
   - Check if the base URL is accessible
   - Try the `health` command to test connectivity

2. **Command Not Found**:
   - Ensure you're in the correct directory
   - Verify virtual environment is activated
   - Check that dependencies are installed

3. **JSON Parsing Errors**:
   - Validate JSON syntax using online tools
   - Ensure proper escaping of quotes in shell commands

4. **File Processing Issues**:
   - Check file permissions and paths
   - Verify CSV file format and encoding
   - Ensure sufficient disk space for output files

## Contributing

This CLI tool is built with:
- **Typer**: For the command-line interface
- **httpx**: For HTTP client functionality  
- **python-dotenv**: For environment variable management

For development, install in editable mode:
```bash
pip install -e .
```
