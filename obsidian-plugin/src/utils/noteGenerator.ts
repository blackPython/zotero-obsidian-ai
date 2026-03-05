export function generateFilename(paper: any): string {
  const title = paper.title.replace(/[^\w\s-]/g, '').substring(0, 50);
  const year = paper.year || 'YYYY';
  const firstAuthor = paper.authors?.split(';')[0]?.split(' ').pop() || 'Unknown';
  return `${firstAuthor} ${year} - ${title}`.trim();
}

export function generateNoteContent(paper: any): string {
  const analysis = paper.analysis || {};
  const metadata = paper.metadata || {};

  let content = `# ${paper.title}\n\n`;

  // Metadata section
  content += `## Metadata\n`;
  content += `- **Authors**: ${paper.authors || 'Unknown'}\n`;
  content += `- **Year**: ${paper.year || 'Unknown'}\n`;
  content += `- **DOI**: ${metadata.doi || 'N/A'}\n`;
  content += `- **URL**: ${metadata.url || 'N/A'}\n`;
  content += `- **Collections**: ${paper.collections?.join(', ') || 'Uncategorized'}\n`;
  content += `- **Tags**: ${metadata.tags?.map((t: string) => `#${t.replace(/\s+/g, '-')}`).join(' ') || ''}\n\n`;

  // Summaries
  if (analysis.summaries) {
    content += `## Summary\n\n`;
    if (analysis.summaries.one_line) {
      content += `**One-line**: ${analysis.summaries.one_line}\n\n`;
    }
    if (analysis.summaries.technical) {
      content += `### Technical Summary\n${analysis.summaries.technical}\n\n`;
    }
  }

  // Main analysis
  if (analysis.main) {
    content += `## Analysis\n\n${analysis.main}\n\n`;
  }

  // Key concepts
  if (analysis.concepts) {
    content += `## Key Concepts\n\n${analysis.concepts}\n\n`;
  }

  // Original abstract
  if (paper.abstract) {
    content += `## Abstract\n\n${paper.abstract}\n\n`;
  }

  // Q&A section
  content += `## Questions & Answers\n\n`;
  content += `> Use the "Ask question about current paper" command to interact with this paper.\n\n`;

  // Metadata comment
  content += `---\n\n`;
  content += `<!-- Zotero AI Metadata\n`;
  content += `zotero_key: ${paper.zotero_key}\n`;
  content += `processed_date: ${new Date().toISOString()}\n`;
  content += `model_used: ${analysis.model_used || 'unknown'}\n`;
  content += `-->\n`;

  return content;
}

export function extractZoteroKey(content: string): string | null {
  const match = content.match(/zotero_key:\s*(\S+)/);
  return match ? match[1] : null;
}
