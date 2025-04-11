import os
import time
import threading
import signal
import json
import zlib
import shutil
# from elevate import elevate # 如果需要管理员权限，可以取消注释 L269
from concurrent.futures import ThreadPoolExecutor
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    MofNCompleteColumn,
)

version = "1.4t"
LOG_FILE = "refresh_log.json"
BUFFER_SIZE = 4 * 1024  # 缓冲区大小
ENABLE_MULTITHREADING = False  # 设置为 False 时禁用多线程
THREAD_COUNT = 4  # 线程数
BENCHMARK_SIZE_GB = 1  # 基准速度测试大小 (GB)
RATIO = 0.3  # 冷数据判定比例
SKIP_SIZE = 1 * 1024**2  # 小于该值的文件会被跳过（0表示禁用）
EXIT_FLAG = False  # 程序终止标志


def is_admin():
    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def signal_handler(sig, frame):
    global EXIT_FLAG
    print("\n正在终止程序...")
    EXIT_FLAG = True


signal.signal(signal.SIGINT, signal_handler)


def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {"pending": [], "completed": []}


def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def benchmark_speed(directory, progress, size_in_gb=BENCHMARK_SIZE_GB):
    size_in_bytes = size_in_gb * 1024**3
    benchmark_results = {
        "large": {"speed": 0, "file_size": size_in_bytes},
        "medium": {"speed": 0, "file_size": 100 * 1024**2},
        "small": {"speed": 0, "file_size": 1 * 1024**2},
    }

    with progress:
        # 大文件测试
        task = progress.add_task("[cyan]大文件基准测试...", total=size_in_bytes)
        try:
            test_file = os.path.join(directory, "benchmark_large.bin")
            # 写入测试文件
            with open(test_file, "wb") as f:
                for _ in range(size_in_bytes // BUFFER_SIZE):
                    f.write(os.urandom(BUFFER_SIZE))
                    progress.update(task, advance=BUFFER_SIZE)

            # 读取测试
            start = time.time()
            with open(test_file, "rb") as f:
                while f.read(BUFFER_SIZE):
                    pass
            elapsed = time.time() - start
            benchmark_results["large"]["speed"] = size_in_bytes / elapsed / 1024**2
            os.remove(test_file)
        except Exception as e:
            progress.print(f"大文件基准测试出错: {e}")
        finally:
            progress.remove_task(task)

        # 中小文件测试
        for category in ["medium", "small"]:
            file_size = 100 * 1024**2 if category == "medium" else 1 * 1024**2
            file_count = 10
            total_size = file_size * file_count
            task = progress.add_task(
                f"[cyan]{'中等' if category == 'medium' else '小'}文件基准测试...",
                total=total_size,
            )

            try:
                files = []
                # 创建测试文件
                for i in range(file_count):
                    file_path = os.path.join(directory, f"benchmark_{category}_{i}.bin")
                    with open(file_path, "wb") as f:
                        f.write(os.urandom(file_size))
                    files.append(file_path)
                    progress.update(task, advance=file_size)

                # 读取测试
                start = time.time()
                for file_path in files:
                    with open(file_path, "rb") as f:
                        while f.read(BUFFER_SIZE):
                            pass
                elapsed = time.time() - start
                benchmark_results[category]["speed"] = total_size / elapsed / 1024**2
            except Exception as e:
                progress.print(f"{category}文件基准测试出错: {e}")
            finally:
                for f in files:
                    if os.path.exists(f):
                        os.remove(f)
                progress.remove_task(task)

    return benchmark_results


def refresh_file(file_path, benchmark_speed_results, progress):
    if EXIT_FLAG:
        return

    temp_path = file_path + ".temp"
    try:
        file_size = os.path.getsize(file_path)

        # 判断文件大小类别
        if file_size > 100 * 1024**2:
            base_speed = benchmark_speed_results["large"]["speed"]
        elif file_size > 10 * 1024**2:
            base_speed = benchmark_speed_results["medium"]["speed"]
        else:
            base_speed = benchmark_speed_results["small"]["speed"]

        progress.print(f"正在处理: {file_path} 大小: {file_size//1024**2}MB")

        # 跳过小文件
        if SKIP_SIZE and file_size <= SKIP_SIZE:
            return

        # 计算抽样读取大小（1%文件大小，至少10MB，最多100MB）
        sample_size = int(file_size * 0.01)
        sample_size = max(10 * 1024**2, sample_size)  # 最低10MB
        sample_size = min(sample_size, 100 * 1024**2)  # 最高100MMB
        sample_size = min(sample_size, file_size)  # 不超过文件实际大小

        # 执行抽样速度测试
        start_time = time.time()
        total_read = 0
        with open(file_path, "rb") as f:
            while total_read < sample_size:
                remaining = sample_size - total_read
                chunk = f.read(min(BUFFER_SIZE, remaining))
                if not chunk:
                    break
                total_read += len(chunk)

        time_taken = time.time() - start_time
        if time_taken > 0:
            actual_speed = total_read / time_taken / 1024**2
        else:
            actual_speed = float("inf")

        progress.print(
            f"抽样测试 {total_read//1024**2}MB, 速度: {actual_speed:.1f}MB/s, 基准: {base_speed:.1f}MB/s"
        )

        if actual_speed < base_speed * RATIO:
            progress.print(f"正在刷新冷数据: {file_path}")
            # 执行完整文件刷新
            checksum = 0
            with open(file_path, "rb") as src, open(temp_path, "wb") as dest:
                while chunk := src.read(BUFFER_SIZE):
                    checksum = zlib.crc32(chunk, checksum)
                    dest.write(chunk)

            # 验证并替换文件
            if checksum == zlib.crc32(open(temp_path, "rb").read()):
                stat = os.stat(file_path)
                shutil.move(temp_path, file_path)
                os.utime(file_path, (stat.st_atime, stat.st_mtime))
                progress.print(f"文件已刷新: {file_path}")
            else:
                progress.print(f"文件校验失败: {file_path}")
        else:
            progress.print(f"跳过非冷数据: {file_path}")

    except Exception as e:
        progress.print(f"处理文件出错 {file_path}: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def refresh_files(pending_files, benchmark_results, progress):
    log = load_log()
    lock = threading.Lock()

    with progress:
        task_id = progress.add_task("[green]刷新进度", total=len(pending_files))

        def worker(file_path):
            if EXIT_FLAG:
                return
            try:
                refresh_file(file_path, benchmark_results, progress)
                with lock:
                    log["completed"].append(file_path)
                    save_log(log)
                progress.update(task_id, advance=1)
            except Exception as e:
                progress.print(f"线程错误: {e}")

        if ENABLE_MULTITHREADING:
            with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
                futures = [executor.submit(worker, f) for f in pending_files]
                for future in futures:
                    if EXIT_FLAG:
                        executor.shutdown(wait=False)
                        break
                    future.result()
        else:
            for file_path in pending_files:
                if EXIT_FLAG:
                    break
                worker(file_path)


def scan_files(directory, min_days, progress):
    now = time.time()
    cold_files = []
    total_files = 0

    with progress:
        scan_task = progress.add_task("[yellow]扫描目录...", total=None)
        for root, _, files in os.walk(directory):
            for file in files:
                if EXIT_FLAG:
                    return []
                file_path = os.path.join(root, file)
                total_files += 1
                try:
                    stat = os.stat(file_path)
                    if (now - stat.st_atime) > min_days * 86400:
                        cold_files.append(file_path)
                    progress.update(
                        scan_task,
                        description=f"[yellow]已扫描 {total_files} 文件，找到 {len(cold_files)} 冷数据",
                    )
                except Exception as e:
                    progress.print(f"访问文件出错 {file_path}: {e}")
        progress.remove_task(scan_task)
    return cold_files


def main():
    # elevate() # 如果需要管理员权限，可以取消注释
    print(f"ColDataFresh v{version} - 冷数据刷新工具")
    print("Jex Zucker")
    if not is_admin():
        print("警告：部分文件可能需要管理员权限才能刷新")
    else:
        print("已获取管理员权限")

    directory = input("请输入要扫描的目录: ").strip('"')
    min_days = int(input("请输入冷数据最小天数: "))
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        expand=True,
    ) as progress:
        # 基准测试
        progress.print("[bold]开始基准性能测试...")
        benchmark_results = benchmark_speed(directory, progress)

        # 扫描冷数据
        progress.print("[bold]开始扫描冷数据...")
        cold_files = scan_files(directory, min_days, progress)

        if not cold_files:
            progress.print("[bold green]未找到需要处理的冷数据")
            return

        # 过滤已完成的文件
        log = load_log()
        pending_files = list(set(cold_files) - set(log["completed"]))
        progress.print(f"[bold]找到 {len(pending_files)} 个需要刷新的文件")

        # 执行刷新
        if pending_files:
            refresh_files(pending_files, benchmark_results, progress)
            progress.print("[bold green]所有操作已完成！")
        else:
            progress.print("[bold green]没有需要刷新的文件")


if __name__ == "__main__":
    main()
