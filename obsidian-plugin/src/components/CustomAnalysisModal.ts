import { App, Modal, Notice, TFile } from 'obsidian';
import type ZoteroAIPlugin from '../main';

export class CustomAnalysisModal extends Modal {
  plugin: ZoteroAIPlugin;
  zoteroKey: string;
  file: TFile;

  constructor(app: App, plugin: ZoteroAIPlugin, zoteroKey: string, file: TFile) {
    super(app);
    this.plugin = plugin;
    this.zoteroKey = zoteroKey;
    this.file = file;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();

    contentEl.createEl('h2', { text: 'Custom Analysis' });

    const analysisTypes = [
      { id: 'research_gap', name: 'Research Gaps' },
      { id: 'practical_applications', name: 'Practical Applications' },
      { id: 'critique', name: 'Methodological Critique' },
      { id: 'future_work', name: 'Future Work Suggestions' },
    ];

    const select = contentEl.createEl('select', {
      attr: { style: 'width: 100%; margin: 10px 0;' },
    });

    analysisTypes.forEach((type) => {
      select.createEl('option', { text: type.name, value: type.id });
    });

    const runButton = contentEl.createEl('button', { text: 'Run Analysis' });
    runButton.onclick = async () => {
      runButton.disabled = true;
      runButton.textContent = 'Analyzing...';

      try {
        const result = await this.plugin.api.runCustomAnalysis(this.zoteroKey, select.value);
        const content = await this.app.vault.read(this.file);
        const newSection = `\n## Custom Analysis: ${select.selectedOptions[0].text}\n\n${result.analysis}\n\n`;
        await this.app.vault.modify(this.file, content + newSection);

        new Notice('Analysis added to note');
        this.close();
      } catch (error) {
        console.error('Analysis error:', error);
        new Notice('Error running analysis');
        runButton.disabled = false;
        runButton.textContent = 'Run Analysis';
      }
    };
  }

  onClose() {
    this.contentEl.empty();
  }
}
