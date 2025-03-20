### run tests with coverage
python -m pytest tests --cov=app --cov-report=xml -p no:anchorpy

### run comprehensive solana diagnostic
python backend/comprehensive_solana_diagnostic.py

### run security checks
python -m security/scan.py

### run performance checks
python -m performance/scan.py

### run code quality checks
python -m code_quality/scan.py

### run documentation checks
python -m documentation/scan.py

### run accessibility checks
python -m accessibility/scan.py

### start server
sh restart_server.sh

### start frontend
sh start-dev.sh
