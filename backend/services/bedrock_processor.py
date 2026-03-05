"""
AWS Bedrock Integration for Paper Processing
Uses Claude via Bedrock for intelligent paper analysis
"""

import json
import yaml
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import PyPDF2
import pdfplumber

from utils.config import Config
from utils.text_splitter import TextSplitter


class BedrockProcessor:
    """Processes papers using AWS Bedrock Claude models"""

    def __init__(self, config: Config):
        self.config = config

        # Initialize Bedrock client
        bedrock_config = BotoConfig(
            region_name=config.aws_region,
            read_timeout=300,
            retries={'max_attempts': 3}
        )

        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=config.aws_region,
            config=bedrock_config
        )

        # Load prompt templates
        self.prompts = self._load_prompts()

        # Text splitter for large documents
        self.text_splitter = TextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )

        # Model configuration
        self.model_id = config.bedrock_model_id  # e.g., "anthropic.claude-3-sonnet-20240229-v1:0"
        self.max_tokens = config.max_tokens

    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompt templates from configuration"""
        prompt_file = Path(self.config.config_dir) / "prompts" / "paper_analysis.yaml"

        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Prompt file not found: {prompt_file}")
            return self._get_default_prompts()

    def _get_default_prompts(self) -> Dict[str, Any]:
        """Return default prompts if config file not found"""
        return {
            'initial_analysis': {
                'system_prompt': 'You are an expert research assistant.',
                'main_prompt': 'Analyze this paper: {title}\n\n{content}'
            }
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def invoke_claude(self, prompt: str, system_prompt: str = None) -> str:
        """Invoke Claude model via Bedrock"""
        try:
            # Prepare the request
            messages = [{"role": "user", "content": prompt}]

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.95
            }

            if system_prompt:
                request_body["system"] = system_prompt

            # Invoke the model
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except Exception as e:
            logger.error(f"Error invoking Bedrock: {e}")
            raise

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from PDF file"""
        text = ""

        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            # Fallback to PyPDF2 if pdfplumber fails
            if not text.strip():
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"

        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""

        return text.strip()

    async def analyze_paper(self, paper_data: Dict, pdf_path: Optional[Path] = None) -> Dict:
        """
        Perform comprehensive analysis of a paper
        Returns structured analysis results
        """
        logger.info(f"Analyzing paper: {paper_data['title'][:50]}...")

        # Extract full text if PDF available
        full_text = ""
        if pdf_path and pdf_path.exists():
            full_text = self.extract_text_from_pdf(pdf_path)
            logger.info(f"Extracted {len(full_text)} characters from PDF")

        # Prepare context
        context = {
            'title': paper_data['title'],
            'authors': paper_data['authors'],
            'abstract': paper_data.get('abstract', ''),
            'year': paper_data.get('year', ''),
            'full_text': full_text[:50000] if full_text else paper_data.get('abstract', '')
        }

        # Get initial analysis
        analysis_prompt = self.prompts['initial_analysis']['main_prompt'].format(**context)
        system_prompt = self.prompts['initial_analysis']['system_prompt']

        initial_analysis = await self.invoke_claude(analysis_prompt, system_prompt)

        # Extract key concepts
        concept_prompt = self.prompts['concept_extraction']['prompt'].format(
            content=full_text[:20000] if full_text else paper_data.get('abstract', '')
        )
        concepts = await self.invoke_claude(concept_prompt)

        # Generate different summary types
        summaries = {}
        for summary_type, summary_config in self.prompts.get('summary_types', {}).items():
            summary_prompt = summary_config['prompt'].format(
                title=paper_data['title'],
                abstract=paper_data.get('abstract', '')
            )
            summaries[summary_type] = await self.invoke_claude(summary_prompt)

        # Compile results
        analysis_result = {
            'zotero_key': paper_data['zotero_key'],
            'title': paper_data['title'],
            'authors': paper_data['authors'],
            'year': paper_data.get('year'),
            'collections': paper_data.get('collections', []),
            'analysis': {
                'main': initial_analysis,
                'concepts': concepts,
                'summaries': summaries,
                'analyzed_at': datetime.now().isoformat(),
                'model_used': self.model_id
            },
            'metadata': {
                'doi': paper_data.get('doi', ''),
                'url': paper_data.get('url', ''),
                'tags': paper_data.get('tags', []),
                'publication': paper_data.get('publication', ''),
                'pdf_processed': bool(full_text)
            }
        }

        logger.info(f"Analysis complete for: {paper_data['title'][:50]}...")
        return analysis_result

    async def answer_question(self, paper_data: Dict, question: str, context: str = "") -> str:
        """
        Answer a specific question about a paper
        Used for Q&A feature in Obsidian
        """
        qa_prompt = self.prompts['qa_system']['qa_prompt'].format(
            title=paper_data['title'],
            question=question,
            context=context or paper_data.get('abstract', '')
        )

        system_prompt = self.prompts['qa_system']['system_prompt'].format(
            title=paper_data['title']
        )

        answer = await self.invoke_claude(qa_prompt, system_prompt)
        return answer

    async def find_connections(self, paper_data: Dict, existing_notes: List[Dict]) -> Dict:
        """
        Find connections between new paper and existing library
        """
        if not existing_notes:
            return {'connections': [], 'themes': []}

        # Prepare context about existing papers
        existing_context = "\n".join([
            f"- {note['title']} ({note.get('year', 'N/A')}): {note.get('summary', 'No summary')[:200]}"
            for note in existing_notes[:20]  # Limit to 20 most recent
        ])

        connection_prompt = self.prompts['literature_connections']['prompt'].format(
            paper_info=f"{paper_data['title']}\n{paper_data.get('abstract', '')}",
            existing_notes=existing_context
        )

        connections = await self.invoke_claude(connection_prompt)

        return {
            'connections': connections,
            'analyzed_against': len(existing_notes)
        }

    async def custom_analysis(self, paper_data: Dict, analysis_type: str, **kwargs) -> str:
        """
        Run custom analysis using user-defined prompts
        """
        custom_prompts = self.prompts.get('custom_analysis', {})

        if analysis_type not in custom_prompts:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        prompt_template = custom_prompts[analysis_type]['prompt']

        # Prepare context
        context = {
            'title': paper_data['title'],
            'content': paper_data.get('abstract', ''),
            **kwargs
        }

        prompt = prompt_template.format(**context)
        result = await self.invoke_claude(prompt)

        return result

    async def batch_process_papers(self, papers: List[Dict], pdf_paths: Dict[str, Path] = None) -> List[Dict]:
        """
        Process multiple papers in batch with rate limiting
        """
        results = []
        pdf_paths = pdf_paths or {}

        for paper in papers:
            try:
                pdf_path = pdf_paths.get(paper['zotero_key'])
                result = await self.analyze_paper(paper, pdf_path)
                results.append(result)

                # Rate limiting - wait between requests
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error processing paper {paper['title']}: {e}")
                results.append({
                    'zotero_key': paper['zotero_key'],
                    'title': paper['title'],
                    'error': str(e)
                })

        return results