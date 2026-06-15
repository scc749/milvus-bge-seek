from pathlib import Path

from agent.services.document_parser_service import DocumentParserService


def test_parse_csv_file_to_markdown(tmp_path: Path) -> None:
    service = DocumentParserService()
    csv_file = tmp_path / "table.csv"
    csv_file.write_text("name,score\nrag,95\nagent,90\n", encoding="utf-8")

    result = service.parse_file(csv_file)

    assert result is not None
    assert result["metadata"]["parser_name"] == "simple"
    assert "| name | score |" in result["content"]
    assert "| rag | 95 |" in result["content"]


def test_parse_json_file_to_markdown(tmp_path: Path) -> None:
    service = DocumentParserService()
    json_file = tmp_path / "doc.json"
    json_file.write_text('{"topic":"rag","level":"advanced"}', encoding="utf-8")

    result = service.parse_file(json_file)

    assert result is not None
    assert result["metadata"]["file_extension"] == "json"
    assert '"topic": "rag"' in result["content"]


def test_parse_html_file_to_text(tmp_path: Path) -> None:
    service = DocumentParserService()
    html_file = tmp_path / "page.html"
    html_file.write_text(
        "<html><body><h1>RAG</h1><p>Pipeline design</p></body></html>",
        encoding="utf-8",
    )

    result = service.parse_file(html_file)

    assert result is not None
    assert "RAG" in result["content"]
    assert "Pipeline design" in result["content"]


def test_parse_image_file_returns_placeholder(tmp_path: Path) -> None:
    service = DocumentParserService()
    image_file = tmp_path / "diagram.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    result = service.parse_file(image_file)

    assert result is not None
    assert result["metadata"]["parser_name"] == "multimodal_placeholder"
    assert "[IMAGE file]" in result["content"]


def test_parse_directory_collects_supported_files(tmp_path: Path) -> None:
    service = DocumentParserService()
    (tmp_path / "a.md").write_text("# Intro", encoding="utf-8")
    (tmp_path / "b.csv").write_text("name\nrag\n", encoding="utf-8")
    (tmp_path / "c.bin").write_bytes(b"\x00\x01")

    results = service.parse_directory(tmp_path)

    assert len(results) == 2
    assert {item["title"] for item in results} == {"a.md", "b.csv"}
