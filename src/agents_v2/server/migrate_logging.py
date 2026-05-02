"""
日志系统迁移脚本

将项目中的 logging 模块迁移到新的 loguru 日志系统

使用方法:
    python -m src.agents_v2.migrate_logging --dry-run  # 预览
    python -m src.agents_v2.migrate_logging           # 执行迁移
"""
import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

# 迁移模式定义
REPLACE_PATTERNS = [
    # Pattern 1: import logging + logger = get_logging_logger(__name__)
    (
        r"^import logging\s*$",
        r"from src.agents_v2.logging_config import get_logging_logger"
    ),
    (
        r"^from logging import\s+.*$",
        r""
    ),
    (
        r"(logger\s*=\s*)logging\.getLogger\(__name__\)",
        r"\1get_logging_logger(__name__)"
    ),
    (
        r"(logger\s*=\s*)logging\.getLogger\(([^)]+)\)",
        r"\1get_logging_logger(\2)"
    ),
    # logger.method() 保持不变，loguru 的方法名是兼容的
]

# 需要添加导入的文件（如果没有 logging_config 的导入）
ADD_IMPORT_PATTERN = re.compile(r"from src\.agents_v2\.logging_config import")


def scan_files(directory: str, extensions: List[str] = [".py"]) -> List[Path]:
    """扫描目录下的所有 Python 文件"""
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                files.append(Path(root) / filename)
    return files


def has_logging_import(file_path: Path) -> bool:
    """检查文件是否使用了 logging 模块"""
    try:
        content = file_path.read_text(encoding="utf-8")
        # 检查是否有 logging 相关导入
        patterns = [
            r"^import logging\s*$",
            r"^from logging import",
            r"from src\.agents_v2\.logging_config import",
        ]
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False
    except Exception:
        return False


def needs_loguru_import(file_path: Path) -> bool:
    """检查文件是否需要添加 loguru 导入"""
    try:
        content = file_path.read_text(encoding="utf-8")
        return not bool(ADD_IMPORT_PATTERN.search(content))
    except Exception:
        return True


def migrate_file(
    file_path: Path,
    dry_run: bool = False,
    verbose: bool = False
) -> Tuple[bool, List[str]]:
    """
    迁移单个文件

    Returns:
        (是否修改, 修改列表)
    """
    changes = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"读取失败: {e}"]

    original_content = content

    # 检查是否有 get_logging_logger 的导入
    has_import = "from src.agents_v2.logging_config import" in content

    # 1. 处理 import logging 语句
    # 移除: import logging
    content = re.sub(r"^import logging\s*$", "", content, flags=re.MULTILINE)

    # 移除: from logging import ...
    content = re.sub(r"^from logging import [^\n]+\n?", "", content, flags=re.MULTILINE)

    # 移除: import logging as xxx
    content = re.sub(r"^import logging as \w+\s*$", "", content, flags=re.MULTILINE)

    if content != original_content:
        changes.append("移除了 logging 相关导入")

    # 2. 处理 logger = get_logging_logger(...)
    # logger = get_logging_logger(__name__) -> logger = get_logging_logger(__name__)
    content = re.sub(
        r"logger\s*=\s*logging\.getLogger\(__name__\)",
        "logger = get_logging_logger(__name__)",
        content
    )

    # logger = get_logging_logger("xxx") -> logger = get_logging_logger("xxx")
    content = re.sub(
        r"(logger\s*=\s*)logging\.getLogger\(([^)]+)\)",
        r"\1get_logging_logger(\2)",
        content
    )

    if content != original_content:
        changes.append("转换了 logging.getLogger 为 get_logging_logger")

    # 3. 添加 logging_config 导入（如果需要）
    if not has_import:
        # 找到第一个非空行或第一个 import 语句
        # 首先尝试找第一个 import 语句的位置
        import_match = re.search(r"^(import |from )", content, re.MULTILINE)
        if import_match:
            # 在第一个 import 之前插入
            insert_pos = import_match.start()
            import_line = "from src.agents_v2.logging_config import get_logging_logger\n\n"
            content = content[:insert_pos] + import_line + content[insert_pos:]
        else:
            # 如果没有 import，在文件开头插入
            import_line = "from src.agents_v2.logging_config import get_logging_logger\n\n"
            content = import_line + content

        # 标记为已添加导入
        has_import = True
        changes.append("添加了 logging_config 导入")

    # 4. 处理 logger.error() -> logger.error() (loguru 不支持 exception)
    content = re.sub(
        r"(\s)logger\.exception\(",
        r"\1logger.error(",
        content
    )

    if "logger.exception(" in original_content:
        changes.append("转换了 logger.exception 为 logger.error")

    # 5. 处理 logging.basicConfig -> 移除（loguru 自动配置）
    content = re.sub(
        r"logging\.basicConfig\([^)]*\)\s*\n?",
        "",
        content
    )

    if "logging.basicConfig" in original_content:
        changes.append("移除了 logging.basicConfig 调用")

    # 6. 处理 logging 相关的其他引用（如 logger = logging.getLogger()）
    # 这个已经在步骤2处理了

    # 写入文件
    if not dry_run and content != original_content:
        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            return False, [f"写入失败: {e}"]

    return content != original_content, changes


def migrate_directory(
    directory: str,
    dry_run: bool = False,
    verbose: bool = False,
    exclude_patterns: Optional[List[str]] = None
) -> Tuple[int, int, List[str]]:
    """
    迁移目录下所有文件

    Returns:
        (修改文件数, 总文件数, 错误列表)
    """
    exclude_patterns = exclude_patterns or [
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__init__.py",  # 跳过 __init__.py 避免循环导入
    ]

    modified_count = 0
    error_files = []

    # 扫描文件
    files = scan_files(directory)

    # 过滤排除目录
    files = [
        f for f in files
        if not any(excl in str(f) for excl in exclude_patterns)
    ]

    if verbose:
        print(f"扫描到 {len(files)} 个 Python 文件")

    for file_path in files:
        if not has_logging_import(file_path):
            continue

        if verbose:
            print(f"处理: {file_path.relative_to(directory)}")

        try:
            modified, changes = migrate_file(file_path, dry_run, verbose)
            if modified:
                modified_count += 1
                if verbose:
                    for change in changes:
                        print(f"  - {change}")
        except Exception as e:
            error_files.append(str(file_path))
            if verbose:
                print(f"  错误: {e}")

    return modified_count, len(files), error_files


def revert_file(file_path: Path) -> bool:
    """回滚单个文件的修改（需要 git）"""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "checkout", str(file_path)],
            capture_output=True,
            text=True,
            cwd=file_path.parent
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="日志系统迁移脚本")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际修改文件"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "--directory",
        "-d",
        default="src",
        help="要迁移的目录，默认为 src"
    )
    parser.add_argument(
        "--revert",
        action="store",
        help="回滚指定文件"
    )

    args = parser.parse_args()

    if args.revert:
        file_path = Path(args.revert)
        if file_path.exists():
            if revert_file(file_path):
                print(f"已回滚: {file_path}")
            else:
                print(f"回滚失败: {file_path}")
        else:
            print(f"文件不存在: {file_path}")
        return

    print("=" * 60)
    print("日志系统迁移工具 (logging -> loguru)")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN MODE] - 不会实际修改文件\n")

    # 执行迁移
    print(f"\n开始迁移目录: {args.directory}\n")

    modified_count, total_count, error_files = migrate_directory(
        args.directory,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    # 输出结果
    print("\n" + "=" * 60)
    print(f"迁移完成!")
    print(f"  - 修改文件: {modified_count}/{total_count}")
    print("=" * 60)

    if error_files:
        print(f"\n错误文件 ({len(error_files)}):")
        for f in error_files:
            print(f"  - {f}")

    if args.dry_run:
        print("\n提示: 使用不带 --dry-run 参数的命令来实际执行迁移")


if __name__ == "__main__":
    main()