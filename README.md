# Zotero-Obsidian AI Research Assistant

An intelligent automation system that processes research papers from Zotero using AWS Bedrock LLMs and creates structured notes in Obsidian.

## Features

- 🔄 **Automatic Paper Processing**: Monitors Zotero for new papers and processes them automatically
- 📚 **Library Grouping**: Maintains Zotero's library/collection structure in Obsidian
- 🤖 **AI-Powered Analysis**: Uses AWS Bedrock (Claude) for intelligent paper analysis
- 💬 **Interactive Q&A**: Ask questions about any paper directly in Obsidian
- 🎨 **Customizable Prompts**: Easily modify analysis prompts for different research needs
- 📊 **Rich Metadata**: Extracts and preserves all paper metadata
- 🔗 **Knowledge Graph**: Automatically identifies connections between papers

## Architecture

```
Zotero Library
    ↓
Python Backend Service (Monitor)
    ↓
AWS Bedrock (Claude)
    ↓
Processing Pipeline
    ↓
Obsidian Plugin (UI/Q&A)
```

## Components

### 1. Python Backend (`/backend`)
- Zotero API integration
- Paper extraction and processing
- AWS Bedrock integration
- RESTful API for Obsidian plugin

### 2. Obsidian Plugin (`/obsidian-plugin`)
- Note creation and management
- Q&A interface
- Library structure visualization
- Settings and prompt customization

### 3. Configuration (`/config`)
- Customizable prompt templates
- AWS credentials
- Processing rules

## Setup

See [SETUP.md](./SETUP.md) for detailed installation instructions.

## Usage

1. Add papers to Zotero
2. Papers are automatically processed
3. Notes appear in Obsidian with AI-generated summaries
4. Use Q&A feature for deeper analysis

## Customization

Edit prompt templates in `/config/prompts/` to customize the analysis for your research domain.