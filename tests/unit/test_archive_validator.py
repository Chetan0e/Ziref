import os
import zipfile
import pytest
import tempfile
import shutil
from services.analyzer.archive_validator import ArchiveValidator, ArchiveSecurityError

@pytest.fixture
def temp_dirs():
    work_dir = tempfile.mkdtemp()
    dest_dir = tempfile.mkdtemp()
    yield work_dir, dest_dir
    shutil.rmtree(work_dir, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)

def test_valid_archive_extraction(temp_dirs):
    work_dir, dest_dir = temp_dirs
    zip_path = os.path.join(work_dir, "valid.zip")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("package.json", '{"name": "test-app"}')
        zf.writestr("src/index.js", 'console.log("hello");')

    validator = ArchiveValidator()
    success, msg, files = validator.validate_and_extract(zip_path, dest_dir)
    assert success is True
    assert "package.json" in files
    assert os.path.exists(os.path.join(dest_dir, "package.json"))
    assert os.path.exists(os.path.join(dest_dir, "src", "index.js"))

def test_zip_slip_traversal_detection(temp_dirs):
    work_dir, dest_dir = temp_dirs
    zip_path = os.path.join(work_dir, "traversal.zip")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.sh", 'malicious content')

    validator = ArchiveValidator()
    with pytest.raises(ArchiveSecurityError, match="Path traversal detected"):
        validator.validate_and_extract(zip_path, dest_dir)

def test_zip_bomb_ratio_detection(temp_dirs):
    work_dir, dest_dir = temp_dirs
    zip_path = os.path.join(work_dir, "bomb.zip")

    # Highly compressible zeroes
    large_zeros = b"\x00" * (10 * 1024 * 1024)  # 10 MB
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zeros.dat", large_zeros)

    # Set low max ratio to trigger detection
    validator = ArchiveValidator(max_compression_ratio=5)
    with pytest.raises(ArchiveSecurityError, match="Suspicious compression ratio"):
        validator.validate_and_extract(zip_path, dest_dir)

def test_file_count_limit_detection(temp_dirs):
    work_dir, dest_dir = temp_dirs
    zip_path = os.path.join(work_dir, "many_files.zip")

    with zipfile.ZipFile(zip_path, "w") as zf:
        for i in range(15):
            zf.writestr(f"file_{i}.txt", f"content {i}")

    # Set file count limit to 10
    validator = ArchiveValidator(max_file_count=10)
    with pytest.raises(ArchiveSecurityError, match="too many files"):
        validator.validate_and_extract(zip_path, dest_dir)
