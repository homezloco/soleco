# Soleco Installation Guide

## Prerequisites

Before installing Soleco, ensure you have the following prerequisites:

- **Python**: Version 3.9 or higher
- **Git**: For cloning the repository
- **pip**: For installing Python dependencies
- **Node.js and npm**: For the frontend components (if using the frontend)
- **Solana CLI** (optional): For local testing with Solana

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/soleco.git
cd soleco
```

### 2. Set Up Python Virtual Environment

#### For Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

#### For macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```
# API Keys
HELIUS_API_KEY=your_helius_api_key_here

# RPC Configuration
POOL_SIZE=5
DEFAULT_TIMEOUT=30
DEFAULT_MAX_RETRIES=3
DEFAULT_RETRY_DELAY=1

# Logging
LOG_LEVEL=DEBUG

# Server
PORT=8000
HOST=0.0.0.0
```

Replace `your_helius_api_key_here` with your actual Helius API key. You can obtain a Helius API key by signing up at [https://helius.xyz/](https://helius.xyz/).

### 5. Install Frontend Dependencies (Optional)

If you want to use the frontend:

```bash
cd ../frontend
npm install
```

## Running the Application

### Running the Backend

From the `backend` directory:

```bash
python run.py
```

This will start the FastAPI server on the port specified in your `.env` file (default: 8000).

### Running the Frontend (Optional)

From the `frontend` directory:

```bash
npm start
```

## Verifying the Installation

### Backend Verification

1. Open your browser and navigate to `http://localhost:8000/docs`
2. You should see the FastAPI Swagger documentation interface
3. Test an endpoint, such as `/api/soleco/solana/network/status`

### Frontend Verification (Optional)

If you're using the frontend, navigate to `http://localhost:3000` in your browser.

## Docker Installation (Alternative)

If you prefer to use Docker:

### Prerequisites

- Docker
- Docker Compose

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/soleco.git
cd soleco
```

2. Create a `.env` file as described above

3. Build and run the Docker containers:

```bash
docker-compose up -d
```

This will start both the backend and frontend services.

## Troubleshooting

### Common Issues

#### 1. Missing Dependencies

If you encounter errors about missing dependencies:

```bash
pip install -r requirements.txt
```

#### 2. Connection Errors to Solana RPC

If you're experiencing connection errors to Solana RPC endpoints:

- Check your internet connection
- Verify your Helius API key is correct
- Try using a different RPC endpoint by modifying the `DEFAULT_RPC_ENDPOINTS` list in `app/utils/solana_rpc.py`

#### 3. Port Already in Use

If the port is already in use:

- Change the `PORT` in your `.env` file
- Alternatively, find and stop the process using the port:
  - Windows: `netstat -ano | findstr :8000`
  - Linux/macOS: `lsof -i :8000`

#### 4. Python Version Issues

If you encounter compatibility issues with Python:

- Ensure you're using Python 3.9 or higher
- Check your virtual environment is activated

## Updating

To update to the latest version:

```bash
git pull
cd backend
pip install -r requirements.txt
cd ../frontend
npm install
```

## Development Setup

For development, you may want to install additional tools:

```bash
pip install -r requirements-dev.txt
```

This will install development tools like:

- pytest for testing
- black for code formatting
- flake8 for linting
- mypy for type checking

## Next Steps

After installation, you might want to:

1. Explore the [API Documentation](api.md)
2. Read about the [Solana Connection Pool](solana_connection_pool.md)
3. Learn about the [RPC Node Extractor](solana_rpc_node_extractor.md)
4. Understand the [Mint Extraction System](mint_extraction_system.md)
