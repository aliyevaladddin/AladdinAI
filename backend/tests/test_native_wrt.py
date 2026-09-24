# NOTICE: This file is protected under RCF-PL
"""Test native C WRT engine via compiled C test programs.

These tests compile and run the standalone C test programs to verify
the native C WRT engine implementation independently of the Python service layer.
"""

import os
import subprocess
import pytest
from pathlib import Path


# Paths
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
WRT_DIR = WORKSPACE_ROOT / "backend" / "native" / "wrt"
TEST_WRT_C = WRT_DIR / "test_wrt.c"
TEST_STANDALONE_C = WRT_DIR / "test_standalone.c"
WRT_ENGINE_BINARY = WRT_DIR / "wrt-engine"
TEST_WRT_BINARY = WRT_DIR / "test_wrt"
TEST_STANDALONE_BINARY = WRT_DIR / "test_standalone"


def compile_wrt_engine():
    """Ensure the wrt-engine binary is compiled."""
    if WRT_ENGINE_BINARY.exists() and os.access(WRT_ENGINE_BINARY, os.X_OK):
        return True

    result = subprocess.run(
        ["make", "-C", str(WRT_DIR), "wrt-engine"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Failed to compile wrt-engine: {result.stderr}")
        return False
    return WRT_ENGINE_BINARY.exists()


def compile_test_wrt():
    """Compile the test_wrt.c test program linked with wrt-engine objects."""
    if TEST_WRT_BINARY.exists() and os.access(TEST_WRT_BINARY, os.X_OK):
        # Check if source is newer
        if TEST_WRT_C.stat().st_mtime < TEST_WRT_BINARY.stat().st_mtime:
            return True

    # Compile with all the engine source files
    result = subprocess.run(
        [
            "gcc", "-O2", "-Wall", "-Wextra", "-std=c11",
            "-D_POSIX_C_SOURCE=200809L", "-D_DEFAULT_SOURCE", "-D_GNU_SOURCE",
            "-DWRT_ENGINE_NO_MAIN",
            str(TEST_WRT_C),
            str(WRT_DIR / "wrt_engine.c"),
            str(WRT_DIR / "wrt_docx.c"),
            str(WRT_DIR / "wrt_markdown.c"),
            str(WRT_DIR / "wrt_odt.c"),
            str(WRT_DIR / "wrt_pptx.c"),
            "-o", str(TEST_WRT_BINARY),
            "-lzip", "-lz"
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Failed to compile test_wrt: {result.stderr}")
        return False
    return TEST_WRT_BINARY.exists()


def compile_test_standalone():
    """Compile the test_standalone.c test program (self-contained)."""
    if TEST_STANDALONE_BINARY.exists() and os.access(TEST_STANDALONE_BINARY, os.X_OK):
        if TEST_STANDALONE_C.stat().st_mtime < TEST_STANDALONE_BINARY.stat().st_mtime:
            return True

    result = subprocess.run(
        [
            "gcc", "-O2", "-Wall", "-Wextra", "-std=c11",
            "-D_POSIX_C_SOURCE=200809L", "-D_DEFAULT_SOURCE", "-D_GNU_SOURCE",
            str(TEST_STANDALONE_C),
            "-o", str(TEST_STANDALONE_BINARY),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Failed to compile test_standalone: {result.stderr}")
        return False
    return TEST_STANDALONE_BINARY.exists()


@pytest.fixture(scope="session", autouse=True)
def setup_c_tests():
    """Compile all C test binaries before running tests."""
    print("\n=== Compiling C test binaries ===")
    assert compile_wrt_engine(), "Failed to compile wrt-engine"
    assert compile_test_wrt(), "Failed to compile test_wrt"
    assert compile_test_standalone(), "Failed to compile test_standalone"
    print("=== All C test binaries compiled successfully ===\n")


def run_c_test(binary_path: Path, test_name: str):
    """Run a C test binary and return stdout, stderr, returncode."""
    result = subprocess.run(
        [str(binary_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"\n--- {test_name} stdout ---")
    print(result.stdout)
    if result.stderr:
        print(f"--- {test_name} stderr ---")
        print(result.stderr)
    return result


class TestWRTEngineC:
    """Test the full WRT engine via the compiled test_wrt binary."""

    def test_c_validation_valid(self):
        """Test C validation with valid WRT content."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt validation valid")
        assert result.returncode == 0, f"test_wrt failed: {result.stderr}"
        assert "PASS: Valid document should pass validation" in result.stdout
        assert "PASS: Should count 6 tags" in result.stdout
        assert "PASS: Should have no issues" in result.stdout

    def test_c_validation_invalid_unclosed(self):
        """Test C validation with unclosed tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt validation unclosed")
        assert result.returncode == 0
        assert "PASS: Unclosed tag should fail validation" in result.stdout
        assert "PASS: Should have at least one issue" in result.stdout
        assert "PASS: Issue should be about 'b' tag" in result.stdout

    def test_c_validation_empty_tag(self):
        """Test C validation rejects empty tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt validation empty tag")
        assert result.returncode == 0
        assert "PASS: Empty tag should fail validation" in result.stdout

    def test_c_validation_unknown_tag(self):
        """Test C validation rejects unknown tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt validation unknown tag")
        assert result.returncode == 0
        assert "PASS: Unknown tag should fail validation" in result.stdout
        assert "PASS: Issue should mention unknown tag" in result.stdout

    def test_c_validation_mismatched_tags(self):
        """Test C validation catches mismatched tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt validation mismatched")
        assert result.returncode == 0
        assert "PASS: Mismatched tags should fail validation" in result.stdout

    def test_c_fix_unclosed(self):
        """Test C fix closes unclosed tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt fix unclosed")
        assert result.returncode == 0
        assert "PASS: Fix should return non-NULL" in result.stdout
        assert "PASS: Fixed content should have closing [/b]" in result.stdout

    def test_c_fix_empty_tag(self):
        """Test C fix removes empty tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt fix empty tag")
        assert result.returncode == 0
        assert "PASS: Fixed content should not have empty tags" in result.stdout

    def test_c_to_html_basic(self):
        """Test C HTML conversion for basic tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt to_html basic")
        assert result.returncode == 0
        assert "PASS: Should convert h1" in result.stdout
        assert "PASS: Should convert quote" in result.stdout

    def test_c_to_html_inline_tags(self):
        """Test C HTML conversion for inline tags."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt to_html inline")
        assert result.returncode == 0
        assert "PASS: Should convert [b] to <strong>" in result.stdout
        assert "PASS: Should convert [i] to <em>" in result.stdout
        assert "PASS: Should convert [u] to <u>" in result.stdout
        assert "PASS: Should convert [s] to <s>" in result.stdout
        assert "PASS: Should convert [code] to <code>" in result.stdout

    def test_c_to_html_table(self):
        """Test C HTML conversion for tables."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt to_html table")
        assert result.returncode == 0
        assert "PASS: Should convert table" in result.stdout
        assert "PASS: Should have header cells" in result.stdout
        assert "PASS: Should have data cells" in result.stdout

    def test_c_to_html_list(self):
        """Test C HTML conversion for lists."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt to_html list")
        assert result.returncode == 0
        assert "PASS: Should convert list to ul" in result.stdout
        assert "PASS: Should have list items" in result.stdout

    def test_c_to_editable_html(self):
        """Test C editable HTML conversion."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt to_editable_html")
        assert result.returncode == 0
        assert "PASS: Should have wrt-editable wrapper" in result.stdout
        assert "PASS: Should have heading" in result.stdout
        assert "PASS: Should close wrapper div" in result.stdout

    def test_c_from_editable_html(self):
        """Test C editable HTML to WRT conversion."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt from_editable_html")
        assert result.returncode == 0
        assert "PASS: Should convert h1" in result.stdout
        assert "PASS: Should convert strong to [b]" in result.stdout

    def test_c_from_editable_html_entities(self):
        """Test C HTML entity decoding."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt from_editable_html entities")
        assert result.returncode == 0
        assert "PASS: Should decode HTML entities" in result.stdout

    def test_c_stats(self):
        """Test C stats calculation."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt stats")
        assert result.returncode == 0
        assert "PASS: Should count 6 words" in result.stdout

    def test_c_report_to_json(self):
        """Test C JSON report generation."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt report to_json")
        assert result.returncode == 0
        assert "PASS: JSON should be generated" in result.stdout
        assert "PASS: JSON should have valid=true" in result.stdout

    def test_c_json_escaping(self):
        """Test C JSON escaping in reports."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt json escaping")
        assert result.returncode == 0
        assert "PASS: Should escape quotes in JSON" in result.stdout
        assert "PASS: Should escape backslash in JSON" in result.stdout

    def test_c_empty_input(self):
        """Test C handling of empty input."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt empty input")
        assert result.returncode == 0
        assert "PASS: Empty input should be valid" in result.stdout
        assert "PASS: Fix empty should return empty" in result.stdout

    def test_c_unicode_content(self):
        """Test C handling of Unicode content."""
        result = run_c_test(TEST_WRT_BINARY, "test_wrt unicode")
        assert result.returncode == 0
        assert "PASS: Unicode content should be valid" in result.stdout
        assert "PASS: Should preserve Cyrillic" in result.stdout
        assert "PASS: Should preserve Chinese" in result.stdout


class TestStandaloneWRT:
    """Test the standalone WRT HTML-to-WRT conversion logic."""

    def test_standalone_basic_conversion(self):
        """Test basic HTML to WRT conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone basic")
        assert result.returncode == 0
        assert "PASS: Should contain 'Hello'" in result.stdout
        assert "PASS: Should contain 'World'" in result.stdout

    def test_standalone_strong_to_bold(self):
        """Test <strong> to [b] conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone strong")
        assert result.returncode == 0
        assert "PASS: Should convert <strong> to [b][/b]" in result.stdout

    def test_standalone_em_to_italic(self):
        """Test <em> to [i] conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone em")
        assert result.returncode == 0
        assert "PASS: Should convert <em> to [i][/i]" in result.stdout

    def test_standalone_underline(self):
        """Test <u> to [u] conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone underline")
        assert result.returncode == 0
        assert "PASS: Should convert <u> to [u][/u]" in result.stdout

    def test_standalone_strikethrough(self):
        """Test  to [s] conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone strikethrough")
        assert result.returncode == 0
        assert "PASS: Should convert <s> to [s][/s]" in result.stdout

    def test_standalone_code(self):
        """Test <code> to [code] conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone code")
        assert result.returncode == 0
        assert "PASS: Should convert <code> to [code][/code]" in result.stdout

    def test_standalone_headings(self):
        """Test heading conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone headings")
        assert result.returncode == 0
        assert "PASS: Should convert h1" in result.stdout
        assert "PASS: Should convert h2" in result.stdout
        assert "PASS: Should convert h3" in result.stdout

    def test_standalone_blockquote(self):
        """Test blockquote conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone blockquote")
        assert result.returncode == 0
        assert "PASS: Should convert blockquote" in result.stdout

    def test_standalone_unordered_list(self):
        """Test unordered list conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone list")
        assert result.returncode == 0
        assert "PASS: Should have [list] tag" in result.stdout
        assert "PASS: Should have list items" in result.stdout
        assert "PASS: Should close list" in result.stdout

    def test_standalone_table(self):
        """Test table conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone table")
        assert result.returncode == 0
        assert "PASS: Should have [table] tag" in result.stdout
        assert "PASS: Should have header row" in result.stdout
        assert "PASS: Should have data row" in result.stdout
        assert "PASS: Should close table" in result.stdout

    def test_standalone_br(self):
        """Test <br> to newline conversion."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone br")
        assert result.returncode == 0
        assert "PASS: Should have newline after Line1" in result.stdout
        assert "PASS: Should have Line2" in result.stdout

    def test_standalone_html_entities(self):
        """Test HTML entity decoding."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone entities")
        assert result.returncode == 0
        assert "PASS: Should decode entities" in result.stdout

    def test_standalone_with_attributes(self):
        """Test handling of tags with attributes."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone attributes")
        assert result.returncode == 0
        assert "PASS: Should extract text even with attributes" in result.stdout

    def test_standalone_empty_input(self):
        """Test empty input handling."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone empty")
        assert result.returncode == 0
        assert "PASS: Result should not be NULL" in result.stdout
        assert "PASS: Empty input should give empty output" in result.stdout

    def test_standalone_nested_tags(self):
        """Test nested tag handling."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone nested")
        assert result.returncode == 0
        assert "PASS: Should have bold open" in result.stdout
        assert "PASS: Should have italic" in result.stdout
        assert "PASS: Should have bold close" in result.stdout

    def test_standalone_multiline_paragraphs(self):
        """Test multiple paragraphs."""
        result = run_c_test(TEST_STANDALONE_BINARY, "test_standalone multiline")
        assert result.returncode == 0
        assert "PASS: Should have newline after First" in result.stdout
        assert "PASS: Should have newline after Second" in result.stdout
        assert "PASS: Should have newline after Third" in result.stdout


class TestWRTEngineCLI:
    """Test the wrt-engine binary via CLI (integration test)."""

    @pytest.fixture(autouse=True)
    def ensure_binary(self):
        assert compile_wrt_engine(), "wrt-engine binary not available"

    def test_cli_validate(self):
        """Test CLI validate command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "validate", "-"],
            input="[h1]Title[/h1]\n[b]Bold[/b]",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert '"valid":true' in result.stdout

    def test_cli_validate_invalid(self):
        """Test CLI validate with invalid content."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "validate", "-"],
            input="[b]Unclosed",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 2  # Invalid returns 2
        assert '"valid":false' in result.stdout

    def test_cli_fix(self):
        """Test CLI fix command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "fix", "-"],
            input="[b]Unclosed",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "[/b]" in result.stdout

    def test_cli_to_html(self):
        """Test CLI to-html command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "to-html", "-"],
            input="[h1]Title[/h1]",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "<h1 class=\"wrt-heading\">Title</h1>" in result.stdout

    def test_cli_to_editable_html(self):
        """Test CLI to-editable-html command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "to-editable-html", "-"],
            input="[h1]Title[/h1]",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "wrt-editable" in result.stdout
        assert "wrt-heading" in result.stdout

    def test_cli_from_editable_html(self):
        """Test CLI from-editable-html command."""
        html = '<div class="wrt-editable"><p>Hello <strong>World</strong></p></div>'
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "from-editable-html", "-"],
            input=html,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "[b]World[/b]" in result.stdout

    def test_cli_stats(self):
        """Test CLI stats command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "stats", "-"],
            input="One two three",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Words:      3" in result.stdout

    def test_cli_list_files(self):
        """Test CLI list-files command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "list-files", str(WRT_DIR)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert '"success":true' in result.stdout
        assert "wrt_engine.c" in result.stdout

    def test_cli_read_file(self):
        """Test CLI read-file command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "read-file", str(TEST_WRT_C)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert '"success":true' in result.stdout
        assert "test_validate_valid" in result.stdout

    def test_cli_save_file(self):
        """Test CLI save-file command."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wrt", delete=False) as tf:
            temp_path = tf.name

        try:
            result = subprocess.run(
                [str(WRT_ENGINE_BINARY), "save-file", temp_path, "-"],
                input="[h1]Test[/h1]",
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0
            assert '"success":true' in result.stdout

            # Verify file was written
            with open(temp_path) as f:
                content = f.read()
            assert content == "[h1]Test[/h1]"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_cli_recent_files(self):
        """Test CLI recent-files command."""
        result = subprocess.run(
            [str(WRT_ENGINE_BINARY), "recent-files"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert '"type":"recent_files_result"' in result.stdout


# Run the C tests directly if executed as script
if __name__ == "__main__":
    pytest.main([__file__, "-v"])