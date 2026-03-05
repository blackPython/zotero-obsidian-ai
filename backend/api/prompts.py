"""
Prompt management API routes
"""

from typing import Optional
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api", tags=["prompts"])


class UpdatePromptsRequest(BaseModel):
    analysis: Optional[str] = None
    qa: Optional[str] = None
    summary: Optional[str] = None


@router.post("/update-prompts")
async def update_prompts(request: UpdatePromptsRequest):
    """Update prompt templates and persist to YAML"""
    from main import bedrock_processor, config

    try:
        prompt_file = Path(config.config_dir) / "prompts" / "paper_analysis.yaml"

        # Load current prompts
        if prompt_file.exists():
            with open(prompt_file, "r") as f:
                prompts = yaml.safe_load(f) or {}
        else:
            prompts = {}

        updated = []

        if request.analysis:
            prompts.setdefault("initial_analysis", {})["main_prompt"] = request.analysis
            updated.append("analysis")

        if request.qa:
            prompts.setdefault("qa_system", {})["qa_prompt"] = request.qa
            updated.append("qa")

        if request.summary:
            prompts.setdefault("summary_types", {}).setdefault("technical", {})["prompt"] = request.summary
            updated.append("summary")

        # Persist to YAML
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prompt_file, "w") as f:
            yaml.dump(prompts, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Updated and saved prompts: {updated}")

        # Reload prompts in processor
        bedrock_processor.prompts = bedrock_processor._load_prompts()

        return {
            "status": "success",
            "updated": updated,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Prompt update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts")
async def get_prompts():
    """Get current prompt templates"""
    from main import config

    try:
        prompt_file = Path(config.config_dir) / "prompts" / "paper_analysis.yaml"

        if prompt_file.exists():
            with open(prompt_file, "r") as f:
                prompts = yaml.safe_load(f) or {}
        else:
            prompts = {}

        return {"status": "success", "prompts": prompts}

    except Exception as e:
        logger.error(f"Prompt fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
