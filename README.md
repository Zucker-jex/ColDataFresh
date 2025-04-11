[中文](README_zh.md)

# ColDataFresh - Cold Data Refresh Tool

A smart cold data refresh tool designed for Windows systems, optimizing storage performance through file access pattern analysis and benchmark performance testing.

## Features

- Intelligent Cold Data Identification (based on access time and performance analysis)
- Multi-threaded File Processing (configurable thread count)
- Adaptive Buffer Management (4KB block operations)
- Benchmark Performance Testing (speed analysis for large/medium/small files)
- Secure File Verification (CRC32 checksum validation)
- Resume Support (JSON log recording)
- Automatic Admin Privilege Detection

## System Requirements

- Windows 10/11 64-bit
- Python 3.11 (recommended official installer)

## Run as Python Script

1. Uncomment `from elevate import elevate` and `elevate()` calls if admin privileges are required (or run Python directly as administrator)
2. Execute using Python

## Compile to EXE

### Preparation

1. Install Cython: `pip install cython`
2. Install MinGW-w64 (check "Add to PATH" during installation)
3. Confirm Python installation path (examples use Python3.11)

### Compilation Steps

```bash
cython --embed -o ColDataFresh.c ColDataFresh.py
gcc ColDataFresh.c -o ColDataFresh.exe ^
-DMS_WIN64 ^
-IC:\Python_path\include ^
-LC:\Python_path\libs ^
-lpython311 ^
-municode
```

_Replacement Notes:_

- `C:\Python_path` should be replaced with actual Python installation path
  - Typical path: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311`
- Ensure `python311.dll` exists in system PATH or exe directory

## Usage

1. Run CMD/PowerShell as administrator
2. Execute program and follow prompts:

```bash
ColDataFresh.exe
Enter target directory: D:\
Enter minimum cold data days: 30
```

3. Use Ctrl+C to safely interrupt operation

## Technical Parameters

| Configuration     | Default | Description                   |
| ----------------- | ------- | ----------------------------- |
| BUFFER_SIZE       | 4 KB    | File operation buffer size    |
| THREAD_COUNT      | 4       | Multi-thread processing count |
| RATIO             | 0.3     | Cold data speed threshold     |
| BENCHMARK_SIZE_GB | 1       | Benchmark test file size      |

## Notes

- Recommended to run during system idle time
- Admin privileges required for system files
- SSD users suggested to set RATIO=0.5
- First run may trigger Windows Defender warning (manual approval required)

**Troubleshooting:**

1. **Missing Python headers during compilation**

   - Verify Python installation path
   - Confirm `python3.11.dll` exists in libs directory

2. **Runtime missing DLL error**

   - Install [VC++ 2015-2022 Redist](https://aka.ms/vs/17/release/vc_redist.x64.exe)
   - Copy `python311.dll` to exe directory

3. **Multi-thread instability**

   - Set `ENABLE_MULTITHREADING = False` in source code
   - Reduce `THREAD_COUNT` to 2-4

4. **Network drive processing failure**
   - Map network drive as local disk
   - Configure authentication when using UNC paths
