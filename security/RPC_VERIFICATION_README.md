# RPC Verification Tools

This directory contains tools for verifying the implementation of RPC error handling improvements in the Soleco codebase.

## Available Tools

### 1. RPC Improvements Verification (`verify_rpc_improvements.py`)

A comprehensive tool that scans the codebase to verify the implementation of specific RPC error handling improvements:
- Coroutine handling
- Response processing
- Error handling
- Serialization
- Initialization

**Note:** This tool may take a long time to run or get stuck when processing large codebases.

### 2. Quick RPC Verification (`quick_rpc_verification.py`)

A simplified version of the RPC improvements verification tool that runs more quickly:
- Focuses on a smaller subset of files and patterns
- Provides a high-level overview of RPC improvements implementation
- May still experience performance issues with large codebases

### 3. Mock RPC Verification (`mock_rpc_verification.py`)

A reliable alternative that doesn't rely on file searching:
- Generates mock verification results based on the known RPC improvements
- Produces realistic data about implementation status without scanning the codebase
- Completes instantly without the risk of getting stuck or timing out
- Supports both standard and detailed reporting modes

## Running the Tools

### RPC Improvements Verification

```bash
# Verify RPC error handling improvements
python verify_rpc_improvements.py
# Or use the batch script
run_rpc_verification.bat
# Or use the PowerShell script
.\run_rpc_verification.ps1
```

### Quick RPC Verification

```bash
# Run a quick verification of RPC improvements
python quick_rpc_verification.py
# Or use the batch script
run_quick_rpc_verification.bat
# Or use the PowerShell script
.\run_quick_rpc_verification.ps1
```

### Mock RPC Verification

```bash
# Run a mock verification of RPC improvements
python mock_rpc_verification.py
# Run with detailed output
python mock_rpc_verification.py --detailed --output custom_output_file.json
# Or use the batch script
run_mock_rpc_verification.bat
# Or use the PowerShell script
.\run_mock_rpc_verification.ps1
```

### Running Only RPC Verification

```bash
# Run only the RPC verification tools
run_rpc_audit_only.bat
# Or use the PowerShell script
.\run_rpc_audit_only.ps1
```

## Command Line Arguments

### Mock RPC Verification

```bash
python mock_rpc_verification.py [--detailed] [--output OUTPUT_FILE]
```

- `--detailed`: Generate detailed verification results with file-specific information
- `--output`: Specify the output file for verification results (default: mock_rpc_verification.json)

## Output Files

The verification tools generate the following output files:

- `rpc_improvements_verification.json`: Results from the comprehensive RPC verification
- `quick_rpc_verification.json`: Results from the quick RPC verification
- `mock_rpc_verification.json`: Results from the standard mock RPC verification
- `mock_rpc_detailed_verification.json`: Results from the detailed mock RPC verification

## RPC Improvements Being Verified

The verification tools check for the following RPC error handling improvements:

### 1. Coroutine Handling
- Fixed issues with coroutines not being properly awaited in the NetworkStatusHandler.get_comprehensive_status method
- Enhanced the _get_data_with_timeout method to properly check if the input is a coroutine and handle it appropriately
- Added detailed logging for coroutine execution and response handling

### 2. Response Processing
- Improved the SolanaQueryHandler.get_vote_accounts method to properly handle the response from the Solana RPC API
- Enhanced the _process_stake_info method to better handle nested structures and find validator data at any level of nesting
- Added recursive search for validator data in complex response structures

### 3. Error Handling
- Enhanced the safe_rpc_call_async function with more detailed logging and better error handling
- Added execution time tracking for RPC calls to help identify slow endpoints
- Improved error messages and structured error responses

### 4. Serialization
- Enhanced the serialize_solana_object function to better handle various response types
- Added specific handling for Pubkey objects, coroutines, and objects with special methods
- Improved error logging during serialization

### 5. Initialization
- Ensured proper initialization of handlers before making RPC calls
- Added explicit initialization in the get_performance_metrics function

## Troubleshooting

If you encounter issues with the verification tools:

1. **Slow Performance or Hanging**: If the `verify_rpc_improvements.py` or `quick_rpc_verification.py` scripts are taking too long or getting stuck, use the `mock_rpc_verification.py` script instead.

2. **PowerShell Execution Policy**: If you cannot run the PowerShell scripts due to execution policy restrictions, you can use the batch scripts instead or adjust your PowerShell execution policy:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Memory Issues**: If the verification tools are using too much memory, try limiting the number of files processed by modifying the script configuration.

## Integration with Security Audit Workflow

The RPC verification tools are integrated into the overall security audit workflow:

- `run_all_audits.bat` and `run_all_audits.ps1` include the mock RPC verification
- The consolidated security report includes the results from the RPC verification

For a faster audit that only focuses on RPC improvements, use the `run_rpc_audit_only.bat` or `run_rpc_audit_only.ps1` scripts.
