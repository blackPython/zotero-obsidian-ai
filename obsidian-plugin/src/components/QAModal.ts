import { App, Modal, Notice, TFile } from 'obsidian';
import type ZoteroAIPlugin from '../main';
import { extractZoteroKey } from '../utils/noteGenerator';

export class QAModal extends Modal {
  plugin: ZoteroAIPlugin;
  file: TFile;

  constructor(app: App, plugin: ZoteroAIPlugin, file: TFile) {
    super(app);
    this.plugin = plugin;
    this.file = file;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();

    contentEl.createEl('h2', { text: 'Ask a Question' });

    const inputContainer = contentEl.createDiv();
    const input = inputContainer.createEl('textarea', {
      placeholder: 'What would you like to know about this paper?',
      attr: { rows: '4', style: 'width: 100%; margin: 10px 0;' },
    });

    const buttonContainer = contentEl.createDiv({ attr: { style: 'text-align: right;' } });
    const askButton = buttonContainer.createEl('button', { text: 'Ask' });

    askButton.onclick = async () => {
      const question = input.value.trim();
      if (!question) return;

      askButton.disabled = true;
      askButton.textContent = 'Thinking...';

      try {
        const noteContent = await this.app.vault.read(this.file);
        const zoteroKey = extractZoteroKey(noteContent);
        if (!zoteroKey) {
          new Notice('Cannot find Zotero key in note');
          return;
        }

        const answer = await this.plugin.api.askQuestion(
          zoteroKey,
          question,
          noteContent.substring(0, 5000),
        );

        // Append Q&A to the note
        const content = await this.app.vault.read(this.file);
        const newQA = `\n### Q: ${question}\n\n**A**: ${answer}\n\n---\n`;

        const qaSection = content.indexOf('## Questions & Answers');
        if (qaSection !== -1) {
          const afterQAHeader = content.substring(qaSection);
          const insertPoint = afterQAHeader.indexOf('\n\n') + qaSection + 2;
          const newContent = content.substring(0, insertPoint) + newQA + content.substring(insertPoint);
          await this.app.vault.modify(this.file, newContent);
        }

        new Notice('Answer added to note');
        this.close();
      } catch (error) {
        console.error('Q&A error:', error);
        new Notice('Error getting answer. Check console for details.');
        askButton.disabled = false;
        askButton.textContent = 'Ask';
      }
    };
  }

  onClose() {
    this.contentEl.empty();
  }
}
