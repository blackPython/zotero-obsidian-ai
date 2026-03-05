import { App, Modal, Notice } from 'obsidian';
import type ZoteroAIPlugin from '../main';

export class PromptEditorModal extends Modal {
  plugin: ZoteroAIPlugin;

  constructor(app: App, plugin: ZoteroAIPlugin) {
    super(app);
    this.plugin = plugin;
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();

    contentEl.createEl('h2', { text: 'Edit Analysis Prompts' });
    contentEl.createEl('p', { text: 'Loading current prompts...' });

    // Load current prompts from backend
    let serverPrompts: any = {};
    try {
      const result = await this.plugin.api.getPrompts();
      serverPrompts = result.prompts || {};
    } catch {
      // Fall back to local settings
    }

    contentEl.empty();
    contentEl.createEl('h2', { text: 'Edit Analysis Prompts' });

    const analysisValue =
      this.plugin.settings.promptTemplates.analysis ||
      serverPrompts?.initial_analysis?.main_prompt ||
      '';
    const qaValue =
      this.plugin.settings.promptTemplates.qa ||
      serverPrompts?.qa_system?.qa_prompt ||
      '';
    const summaryValue =
      this.plugin.settings.promptTemplates.summary ||
      serverPrompts?.summary_types?.technical?.prompt ||
      '';

    contentEl.createEl('h3', { text: 'Analysis Prompt' });
    const analysisTextarea = contentEl.createEl('textarea', {
      value: analysisValue,
      attr: { rows: '6', style: 'width: 100%;' },
    });

    contentEl.createEl('h3', { text: 'Q&A System Prompt' });
    const qaTextarea = contentEl.createEl('textarea', {
      value: qaValue,
      attr: { rows: '4', style: 'width: 100%;' },
    });

    contentEl.createEl('h3', { text: 'Summary Prompt' });
    const summaryTextarea = contentEl.createEl('textarea', {
      value: summaryValue,
      attr: { rows: '4', style: 'width: 100%;' },
    });

    const saveButton = contentEl.createEl('button', { text: 'Save Prompts' });
    saveButton.onclick = async () => {
      this.plugin.settings.promptTemplates.analysis = analysisTextarea.value;
      this.plugin.settings.promptTemplates.qa = qaTextarea.value;
      this.plugin.settings.promptTemplates.summary = summaryTextarea.value;

      await this.plugin.saveSettings();
      await this.plugin.api.updatePrompts(this.plugin.settings.promptTemplates);

      new Notice('Prompts saved');
      this.close();
    };
  }

  onClose() {
    this.contentEl.empty();
  }
}
