"""
Tests for services/bedrock_processor.py (with mocked Bedrock client)
"""

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def processor(mock_config, sample_prompts_yaml):
    """Create a BedrockProcessor with mocked boto3"""
    with patch("services.bedrock_processor.boto3") as mock_boto:
        mock_client = MagicMock()
        mock_boto.client.return_value = mock_client

        # Mock invoke_model response
        mock_response_body = MagicMock()
        mock_response_body.read.return_value = json.dumps({
            "content": [{"text": "This paper presents a novel approach."}]
        }).encode()
        mock_client.invoke_model.return_value = {"body": mock_response_body}

        from services.bedrock_processor import BedrockProcessor

        bp = BedrockProcessor(mock_config)
        bp.bedrock = mock_client
        yield bp, mock_client


def test_init(processor):
    bp, _ = processor
    assert bp.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
    assert bp.max_tokens == 4096
    assert bp.prompts is not None


def test_load_prompts(processor):
    bp, _ = processor
    assert "initial_analysis" in bp.prompts
    assert "qa_system" in bp.prompts
    assert "concept_extraction" in bp.prompts


@pytest.mark.asyncio
async def test_invoke_claude(processor):
    bp, mock_client = processor
    result = await bp.invoke_claude("Test prompt", "System prompt")
    assert result == "This paper presents a novel approach."
    mock_client.invoke_model.assert_called_once()

    # Verify request format
    call_args = mock_client.invoke_model.call_args
    body = json.loads(call_args[1]["body"])
    assert body["messages"][0]["content"] == "Test prompt"
    assert body["system"] == "System prompt"


def test_extract_text_from_pdf(processor, tmp_path):
    bp, _ = processor
    # Create a fake PDF — extraction will fail gracefully
    fake_pdf = tmp_path / "test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    # Should not raise, returns empty on failure
    text = bp.extract_text_from_pdf(fake_pdf)
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_analyze_paper(processor, sample_paper):
    bp, _ = processor
    result = await bp.analyze_paper(sample_paper, pdf_path=None)

    assert result["zotero_key"] == "ABC123"
    assert result["title"] == "Attention Is All You Need"
    assert "analysis" in result
    assert "main" in result["analysis"]
    assert "concepts" in result["analysis"]
    assert "summaries" in result["analysis"]


@pytest.mark.asyncio
async def test_answer_question(processor, sample_paper):
    bp, _ = processor
    answer = await bp.answer_question(sample_paper, "What is the main contribution?")
    assert isinstance(answer, str)
    assert len(answer) > 0


@pytest.mark.asyncio
async def test_find_connections_empty(processor, sample_paper):
    bp, _ = processor
    result = await bp.find_connections(sample_paper, [])
    assert result["connections"] == []
    assert result["themes"] == []


@pytest.mark.asyncio
async def test_find_connections(processor, sample_paper):
    bp, _ = processor
    existing = [{"title": "BERT", "year": "2018", "summary": "Pre-training of language models"}]
    result = await bp.find_connections(sample_paper, existing)
    assert "connections" in result


@pytest.mark.asyncio
async def test_custom_analysis(processor, sample_paper):
    bp, _ = processor
    result = await bp.custom_analysis(sample_paper, "research_gap")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_custom_analysis_unknown_type(processor, sample_paper):
    bp, _ = processor
    with pytest.raises(ValueError, match="Unknown analysis type"):
        await bp.custom_analysis(sample_paper, "nonexistent_type")


@pytest.mark.asyncio
async def test_batch_process(processor, sample_paper):
    bp, _ = processor
    results = await bp.batch_process_papers([sample_paper])
    assert len(results) == 1
    assert results[0]["zotero_key"] == "ABC123"
