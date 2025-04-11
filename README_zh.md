# ColDataFresh - 冷数据刷新工具

专为 Windows 系统设计的智能冷数据刷新工具，通过分析文件访问模式和基准性能测试，优化存储性能。

## 功能特性

- 智能冷数据识别（基于访问时间和性能分析）
- 多线程文件处理（可配置线程数）
- 自适应缓冲区管理（4KB 块操作）
- 基准性能测试（大/中/小文件速度分析）
- 安全文件校验（CRC32 校验和验证）
- 断点续传支持（JSON 日志记录）
- 管理员权限自动检测

## 系统要求

- Windows 10/11 64 位
- Python 3.11 (推荐使用官方安装包)

## 以 Python 脚本运行

1. 如果需要管理员权限可以取消注释 `from elevate import elevate` 与 `elevate()` 调用权限（当然使用管理员身份运行 Python 后执行也行）
2. 使用 Python 运行

## 编译为 EXE 文件

### 准备工具

1. 安装 Cython：`pip install cython`
2. 安装 MinGW-w64 (勾选添加 PATH 环境变量)
3. 确认 Python 安装路径 (示例中使用 Python3.11)

### 编译步骤

```bash
cython --embed -o ColDataFresh.c ColDataFresh.py
gcc ColDataFresh.c -o ColDataFresh.exe ^
-DMS_WIN64 ^
-IC:\Python路径\include ^
-LC:\Python路径\libs ^
-lpython311 ^
-municode
```

_替换说明：_

- `C:\Python路径` 替换为实际 Python 安装路径
  - 典型路径：`C:\Users\你的用户名\AppData\Local\Programs\Python\Python311`
- 确保`python311.dll`存在于系统 PATH 或 exe 同级目录

## 使用说明

1. 以管理员身份运行 CMD/PowerShell
2. 执行程序并按照提示操作：

```bash
ColDataFresh.exe
请输入要扫描的目录: D:\
请输入冷数据最小天数: 30
```

3. 使用 Ctrl+C 可安全中断操作

## 技术参数

| 配置项            | 默认值 | 说明                   |
| ----------------- | ------ | ---------------------- |
| BUFFER_SIZE       | 4 KB   | 文件操作缓冲区大小     |
| THREAD_COUNT      | 4      | 多线程处理数（需启用） |
| RATIO             | 0.3    | 冷数据速度判定阈值     |
| BENCHMARK_SIZE_GB | 1      | 基准测试文件大小       |

## 注意事项

- 建议在系统空闲时段运行
- 处理系统文件需管理员权限
- 固态硬盘(SSD)用户建议设置 RATIO=0.5
- 首次运行可能触发 Windows Defender 警告（需手动放行）

**常见问题解决：**

1. **编译时找不到 Python 头文件**

   - 检查 Python 安装路径是否正确
   - 确认`python3.11.dll`存在于 libs 目录

2. **运行时提示缺少 DLL**

   - 安装[VC++ 2015-2022 运行库](https://aka.ms/vs/17/release/vc_redist.x64.exe)
   - 复制`python311.dll`到 exe 同级目录

3. **多线程模式不稳定**

   - 修改源码设置`ENABLE_MULTITHREADING = False`
   - 降低`THREAD_COUNT`值至 2-4 之间

4. **无法处理网络驱动器**
   - 映射网络驱动器为本地盘符
   - 使用 UNC 路径时需配置身份验证
