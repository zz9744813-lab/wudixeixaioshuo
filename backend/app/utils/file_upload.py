"""
File Upload Utils - 安全的文件上传处理
"""

import os
import shutil
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile

# 允许的文件扩展名白名单
ALLOWED_EXTENSIONS = {".txt", ".md", ".epub", ".docx", ".pdf"}
# 最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


async def save_upload_file_safely(
    file: UploadFile,
    upload_dir: str,
    allowed_extensions: set = None,
    max_bytes: int = None
) -> dict:
    """
    安全地保存上传文件

    安全措施:
    1. 不信任原始文件名，服务端生成 UUID 文件名
    2. 限制扩展名白名单
    3. 限制文件大小
    4. 使用异步分块写入
    5. 失败时清理临时文件

    Args:
        file: FastAPI UploadFile
        upload_dir: 上传目录路径
        allowed_extensions: 允许的扩展名集合 (默认 ALLOWED_EXTENSIONS)
        max_bytes: 最大文件字节数 (默认 MAX_FILE_SIZE)

    Returns:
        dict: {
            "original_filename": 原始文件名,
            "stored_filename": 存储的文件名,
            "size_bytes": 文件大小,
            "extension": 扩展名,
            "relative_path": 相对路径,
            "absolute_path": 绝对路径,
        }

    Raises:
        HTTPException: 400 (不支持的类型), 413 (文件过大)
    """
    allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
    max_bytes = max_bytes or MAX_FILE_SIZE

    # 获取原始文件名和扩展名
    original_name = file.filename or "unnamed"
    ext = Path(original_name).suffix.lower()

    # 验证扩展名
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。允许的类型: {', '.join(allowed_extensions)}"
        )

    # 生成安全的文件名 (UUID + 原始扩展名)
    safe_filename = f"{uuid4().hex}{ext}"

    # 确保上传目录存在
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    # 目标路径
    target_path = upload_path / safe_filename

    # 异步写入文件，同时检查大小
    size = 0
    try:
        async with aiofiles.open(target_path, "wb") as out:
            while True:
                # 分块读取 (1MB)
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break

                size += len(chunk)

                # 检查大小限制
                if size > max_bytes:
                    # 删除已写入的部分文件
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件过大，最大允许 {max_bytes // (1024 * 1024)}MB"
                    )

                await out.write(chunk)

    except HTTPException:
        raise
    except Exception as e:
        # 清理失败时可能存在的部分文件
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"文件保存失败: {str(e)}"
        )

    return {
        "original_filename": original_name,
        "stored_filename": safe_filename,
        "size_bytes": size,
        "extension": ext,
        "relative_path": safe_filename,
        "absolute_path": str(target_path.resolve()),
    }


def delete_upload_file(upload_dir: str, filename: str) -> bool:
    """
    删除上传的文件

    Args:
        upload_dir: 上传目录
        filename: 文件名 (必须是相对路径，不能包含 ..)

    Returns:
        bool: 是否成功删除
    """
    # 安全检查：防止路径穿越
    if ".." in filename or "/" in filename or "\\" in filename:
        return False

    file_path = Path(upload_dir) / filename

    # 确保文件在 upload_dir 内
    try:
        file_path.resolve().relative_to(Path(upload_dir).resolve())
    except ValueError:
        return False

    if file_path.exists():
        file_path.unlink()
        return True
    return False
