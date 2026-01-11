# Flask API Setup Instructions

## Prerequisites

1. Python 3.8 or higher
2. Node.js and npm (for the React frontend)

## Setup Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
# OR
VITE_MY_API_KEY=your_gemini_api_key_here
```

The API server will use either `GEMINI_API_KEY` or `VITE_MY_API_KEY` from the environment.

### 3. Ensure Database is Indexed

Make sure you've run the indexer to populate the SQLite database:

```bash
python indexer.py
```

This will create `transfer_data.db` with all agreements from the `assist_data/` directory.

### 4. Start the Flask API Server

```bash
python api_server.py
```

The API will run on `http://localhost:5000`

### 5. Configure Frontend API URL (Optional)

If your Flask API is running on a different port or URL, set the environment variable:

```env
VITE_API_URL=http://localhost:5000
```

The frontend defaults to `http://localhost:5000` if not specified.

## API Endpoints

- `POST /api/analyze-transcript` - Analyze transcript and compare against agreements
  - Form data: `file`, `university`, `major`
  - Returns: Student courses, matching agreements, and comparison results

- `GET /api/search-agreements` - Search agreements by university and major
  - Query params: `university`, `major`, `source_college` (optional)
  - Returns: List of matching agreements

- `GET /api/agreement/<agreement_key>` - Get full agreement details
  - Returns: Full agreement JSON data

- `GET /api/health` - Health check endpoint

## Troubleshooting

1. **Database not found**: Run `python indexer.py` to create and populate the database
2. **API key error**: Make sure your `.env` file has the correct Gemini API key
3. **CORS errors**: The Flask server has CORS enabled, but make sure it's running on the expected port
4. **File upload errors**: Ensure the file is a valid PDF, TXT, or CSV file

