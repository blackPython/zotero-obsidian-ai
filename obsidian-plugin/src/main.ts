import { App, Plugin, Notice, TFile, TFolder } from 'obsidian';
import { ZoteroAISettings, DEFAULT_SETTINGS } from './types';
import { BackendAPI } from './services/api';
import { generateFilename, generateNoteContent, extractZoteroKey } from './utils/noteGenerator';
import { QAModal } from './components/QAModal';
import { CustomAnalysisModal } from './components/CustomAnalysisModal';
import { PromptEditorModal } from './components/PromptEditorModal';
import { ZoteroAISettingTab } from './components/SettingsTab';
import { CollectionPickerModal } from './components/CollectionPickerModal';

export default class ZoteroAIPlugin extends Plugin {
  settings: ZoteroAISettings;
  syncIntervalId: number | null = null;
  statusBar: HTMLElement;
  api: BackendAPI;

  async onload() {
    await this.loadSettings();
    this.initAPI();

    // Status bar
    this.statusBar = this.addStatusBarItem();
    this.updateStatusBar('Zotero AI: Ready');

    // Ribbon icon
    this.addRibbonIcon('sync', 'Sync Zotero Papers', async () => {
      await this.syncPapers();
    });

    // Commands
    this.addCommand({
      id: 'ask-about-paper',
      name: 'Ask question about current paper',
      editorCallback: async (_editor, view) => {
        const file = view.file;
        if (file) {
          new QAModal(this.app, this, file).open();
        }
      },
    });

    this.addCommand({
      id: 'custom-analysis',
      name: 'Run custom analysis on paper',
      editorCallback: async (_editor, view) => {
        const file = view.file;
        if (file) {
          await this.runCustomAnalysis(file);
        }
      },
    });

    this.addCommand({
      id: 'edit-prompts',
      name: 'Edit analysis prompts',
      callback: () => {
        new PromptEditorModal(this.app, this).open();
      },
    });

    this.addCommand({
      id: 'sync-papers',
      name: 'Sync papers from Zotero',
      callback: async () => {
        await this.syncPapers();
      },
    });

    this.addCommand({
      id: 'refresh-paper-analysis',
      name: 'Refresh analysis for current paper',
      editorCallback: async (_editor, view) => {
        const file = view.file;
        if (file) {
          await this.refreshPaperAnalysis(file);
        }
      },
    });

    this.addCommand({
      id: 'reprocess-paper',
      name: 'Reprocess current paper',
      editorCallback: async (_editor, view) => {
        const file = view.file;
        if (file) {
          await this.reprocessPaper(file);
        }
      },
    });

    this.addCommand({
      id: 'choose-collections',
      name: 'Choose Zotero collections to sync',
      callback: () => {
        new CollectionPickerModal(this.app, this, () => {}).open();
      },
    });

    // Settings tab
    this.addSettingTab(new ZoteroAISettingTab(this.app, this));

    // Auto-sync
    if (this.settings.autoSync) {
      this.startAutoSync();
    }

    console.log('Zotero AI Research Assistant loaded');
  }

  onunload() {
    if (this.syncIntervalId) {
      window.clearInterval(this.syncIntervalId);
    }
  }

  initAPI() {
    this.api = new BackendAPI(this.settings.backendUrl);
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  updateStatusBar(message: string) {
    this.statusBar.setText(message);
  }

  startAutoSync() {
    if (this.syncIntervalId) {
      window.clearInterval(this.syncIntervalId);
    }
    this.syncIntervalId = window.setInterval(async () => {
      await this.syncPapers();
    }, this.settings.syncInterval * 1000);
  }

  async syncPapers() {
    if (this.settings.selectedCollections.length === 0) {
      new Notice('No collections selected. Use "Choose Zotero collections to sync" first.');
      return;
    }

    this.updateStatusBar('Zotero AI: Syncing...');

    try {
      const collectionKeys = this.settings.selectedCollections.map((c) => c.key);
      const result = await this.api.syncPapers(
        this.settings.zoteroLibraryId,
        this.settings.zoteroApiKey,
        collectionKeys,
      );

      if (result.new_papers && result.new_papers.length > 0) {
        for (const paper of result.new_papers) {
          await this.createPaperNote(paper);
        }
        new Notice(`Synced ${result.new_papers.length} new papers from Zotero`);
      } else {
        new Notice('No new papers to sync');
      }

      this.updateStatusBar('Zotero AI: Sync complete');
    } catch (error) {
      console.error('Sync error:', error);
      new Notice('Error syncing with Zotero. Check console for details.');
      this.updateStatusBar('Zotero AI: Sync error');
    }
  }

  async createPaperNote(paper: any) {
    let folderPath = this.settings.notesFolder;

    if (this.settings.maintainLibraryStructure && paper.collections?.length > 0) {
      folderPath = `${this.settings.notesFolder}/${paper.collections[0]}`;
    }

    await this.ensureFolderExists(folderPath);

    const filename = generateFilename(paper);
    const filePath = `${folderPath}/${filename}.md`;

    const existingFile = this.app.vault.getAbstractFileByPath(filePath);
    if (existingFile instanceof TFile) {
      console.log(`Note already exists: ${filePath}`);
      return;
    }

    const content = generateNoteContent(paper);
    await this.app.vault.create(filePath, content);
    console.log(`Created note: ${filePath}`);
  }

  async ensureFolderExists(folderPath: string) {
    const folders = folderPath.split('/');
    let currentPath = '';

    for (const folder of folders) {
      currentPath = currentPath ? `${currentPath}/${folder}` : folder;
      const existingFolder = this.app.vault.getAbstractFileByPath(currentPath);
      if (!existingFolder) {
        await this.app.vault.createFolder(currentPath);
      }
    }
  }

  async runCustomAnalysis(file: TFile) {
    const content = await this.app.vault.read(file);
    const zoteroKey = extractZoteroKey(content);

    if (!zoteroKey) {
      new Notice('This note does not appear to be a Zotero paper');
      return;
    }

    new CustomAnalysisModal(this.app, this, zoteroKey, file).open();
  }

  async refreshPaperAnalysis(file: TFile) {
    const content = await this.app.vault.read(file);
    const zoteroKey = extractZoteroKey(content);

    if (!zoteroKey) {
      new Notice('This note does not appear to be a Zotero paper');
      return;
    }

    try {
      this.updateStatusBar('Zotero AI: Fetching analysis...');
      const result = await this.api.getAnalysis(zoteroKey);

      if (result.status === 'pending') {
        new Notice('Analysis is still processing. Try again later.');
        this.updateStatusBar('Zotero AI: Ready');
        return;
      }

      const analysis = result.analysis;
      const updatedContent = generateNoteContent({
        ...analysis,
        zotero_key: zoteroKey,
      });
      await this.app.vault.modify(file, updatedContent);
      new Notice('Paper note updated with analysis');
      this.updateStatusBar('Zotero AI: Ready');
    } catch (error) {
      console.error('Refresh error:', error);
      new Notice('Error fetching analysis. Check console for details.');
      this.updateStatusBar('Zotero AI: Ready');
    }
  }

  async reprocessPaper(file: TFile) {
    const content = await this.app.vault.read(file);
    const zoteroKey = extractZoteroKey(content);

    if (!zoteroKey) {
      new Notice('This note does not appear to be a Zotero paper');
      return;
    }

    try {
      await this.api.reprocessPaper(zoteroKey);
      new Notice('Paper queued for reprocessing. Use "Refresh analysis" to update the note.');
    } catch (error) {
      console.error('Reprocess error:', error);
      new Notice('Error reprocessing paper. Check console for details.');
    }
  }
}
