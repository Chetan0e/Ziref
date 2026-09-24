import os
import zipfile
import shutil
import logging
from typing import Tuple, List
from services.api.core.config import settings

logger = logging.getLogger("ziref.validator")

class ArchiveSecurityError(Exception):
    pass

class ArchiveValidator:
    def __init__(
        self,
        max_file_size: int = settings.MAX_UPLOAD_SIZE_BYTES,
        max_extracted_size: int = settings.MAX_EXTRACTED_SIZE_BYTES,
        max_file_count: int = settings.MAX_ARCHIVE_FILE_COUNT,
        max_compression_ratio: int = 100
    ):
        self.max_file_size = max_file_size
        self.max_extracted_size = max_extracted_size
        self.max_file_count = max_file_count
        self.max_compression_ratio = max_compression_ratio

    def validate_and_extract(self, zip_path: str, destination_dir: str) -> Tuple[bool, str, List[str]]:
        """
        Validates zip integrity and security boundaries, then extracts securely.
        Returns: (success: bool, message: str, extracted_files: List[str])
        """
        if not os.path.exists(zip_path):
            raise ArchiveSecurityError("Archive file does not exist")

        archive_size = os.path.getsize(zip_path)
        if archive_size > self.max_file_size:
            raise ArchiveSecurityError(
                f"Archive exceeds maximum allowed size ({archive_size} > {self.max_file_size} bytes)"
            )

        if not zipfile.is_zipfile(zip_path):
            raise ArchiveSecurityError("File is not a valid ZIP archive")

        total_extracted_size = 0
        file_count = 0
        extracted_files = []

        abs_dest_dir = os.path.abspath(destination_dir)
        os.makedirs(abs_dest_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                infolist = zf.infolist()
                file_count = len(infolist)

                if file_count > self.max_file_count:
                    raise ArchiveSecurityError(
                        f"Archive contains too many files ({file_count} > {self.max_file_count})"
                    )

                for member in infolist:
                    # 1. Path traversal check (Zip Slip)
                    filename = member.filename
                    # Normalize and strip dangerous characters
                    norm_path = os.path.normpath(filename)
                    if norm_path.startswith("..") or norm_path.startswith("/") or norm_path.startswith("\\"):
                        raise ArchiveSecurityError(f"Path traversal detected in archive entry: {filename}")

                    target_path = os.path.abspath(os.path.join(abs_dest_dir, norm_path))
                    if not target_path.startswith(abs_dest_dir):
                        raise ArchiveSecurityError(f"Entry resolves outside target extraction root: {filename}")

                    # 2. Decompression bomb ratio check
                    total_extracted_size += member.file_size
                    if total_extracted_size > self.max_extracted_size:
                        raise ArchiveSecurityError(
                            f"Total uncompressed size exceeds limit ({total_extracted_size} > {self.max_extracted_size} bytes)"
                        )

                    if member.compress_size > 0:
                        ratio = member.file_size / member.compress_size
                        if ratio > self.max_compression_ratio:
                            raise ArchiveSecurityError(
                                f"Suspicious compression ratio on {filename}: {ratio:.1f}x (limit: {self.max_compression_ratio}x)"
                            )

                    # 3. Check for symlinks pointing outside
                    # Unix symlinks are encoded in external_attr
                    if (member.external_attr >> 16) & 0o120000 == 0o120000:
                        # Symlink detected: do not extract dangerous symlinks
                        logger.warning(f"Skipping dangerous symlink in archive: {filename}")
                        continue

                    # Safe to extract
                    zf.extract(member, abs_dest_dir)
                    extracted_files.append(norm_path)

            return True, f"Successfully validated and extracted {file_count} files", extracted_files

        except zipfile.BadZipFile as e:
            raise ArchiveSecurityError(f"Corrupted ZIP archive: {str(e)}")
        except Exception as e:
            if os.path.exists(abs_dest_dir):
                shutil.rmtree(abs_dest_dir, ignore_errors=True)
            raise ArchiveSecurityError(f"Extraction failed: {str(e)}")

archive_validator = ArchiveValidator()
