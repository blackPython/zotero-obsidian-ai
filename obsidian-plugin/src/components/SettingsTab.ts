import { App, PluginSettingTab, Setting } from 'obsidian';
import type ZoteroAIPlugin from '../main';
import { CollectionPickerModal } from './CollectionPickerModal';

export class ZoteroAISettingTab extends PluginSettingTab {
  plugin: ZoteroAIPlugin;

  constructor(app: App, plugin: ZoteroAIPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: 'Zotero AI Research Assistant Settings' });

    // Backend settings
    containerEl.createEl('h3', { text: 'Backend Configuration' });

    new Setting(containerEl)
      .setName('Backend URL')
      .setDesc('URL of the Python backend service')
      .addText((text) =>
        text
          .setPlaceholder('http://localhost:8000')
          .setValue(this.plugin.settings.backendUrl)
          .onChange(async (value) => {
            this.plugin.settings.backendUrl = value;
            await this.plugin.saveSettings();
            this.plugin.initAPI();
          }),
      );

    // Zotero settings
    containerEl.createEl('h3', { text: 'Zotero Configuration' });

    new Setting(containerEl)
      .setName('Zotero API Key')
      .setDesc('Your Zotero API key (get from zotero.org/settings/keys)')
      .addText((text) =>
        text
          .setPlaceholder('Enter your API key')
          .setValue(this.plugin.settings.zoteroApiKey)
          .onChange(async (value) => {
            this.plugin.settings.zoteroApiKey = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName('Library ID')
      .setDesc('Your Zotero library ID')
      .addText((text) =>
        text
          .setPlaceholder('Enter library ID')
          .setValue(this.plugin.settings.zoteroLibraryId)
          .onChange(async (value) => {
            this.plugin.settings.zoteroLibraryId = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName('Library Type')
      .setDesc('Type of Zotero library')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('user', 'User Library')
          .addOption('group', 'Group Library')
          .setValue(this.plugin.settings.zoteroLibraryType)
          .onChange(async (value) => {
            this.plugin.settings.zoteroLibraryType = value;
            await this.plugin.saveSettings();
          }),
      );

    // Collection filtering
    containerEl.createEl('h3', { text: 'Collections' });

    const collectionSetting = new Setting(containerEl)
      .setName('Active Collections')
      .addButton((btn) =>
        btn.setButtonText('Choose Collections').onClick(() => {
          new CollectionPickerModal(this.app, this.plugin, () => {
            this.display(); // refresh to show updated selection
          }).open();
        }),
      );

    const selected = this.plugin.settings.selectedCollections;
    if (selected.length === 0) {
      collectionSetting.setDesc('No collections selected. Sync is disabled until you choose at least one.');
    } else {
      const names = selected.map((c) => c.path || c.name).join(', ');
      collectionSetting.setDesc(`Syncing ${selected.length} collection${selected.length > 1 ? 's' : ''}: ${names}`);
    }

    // Note organization
    containerEl.createEl('h3', { text: 'Note Organization' });

    new Setting(containerEl)
      .setName('Notes Folder')
      .setDesc('Folder where paper notes will be created')
      .addText((text) =>
        text
          .setPlaceholder('Research Papers')
          .setValue(this.plugin.settings.notesFolder)
          .onChange(async (value) => {
            this.plugin.settings.notesFolder = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName('Maintain Library Structure')
      .setDesc('Create subfolders based on Zotero collections')
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.maintainLibraryStructure).onChange(async (value) => {
          this.plugin.settings.maintainLibraryStructure = value;
          await this.plugin.saveSettings();
        }),
      );

    // Sync settings
    containerEl.createEl('h3', { text: 'Sync Settings' });

    new Setting(containerEl)
      .setName('Auto Sync')
      .setDesc('Automatically sync with Zotero')
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.autoSync).onChange(async (value) => {
          this.plugin.settings.autoSync = value;
          await this.plugin.saveSettings();

          if (value) {
            this.plugin.startAutoSync();
          } else if (this.plugin.syncIntervalId) {
            window.clearInterval(this.plugin.syncIntervalId);
            this.plugin.syncIntervalId = null;
          }
        }),
      );

    new Setting(containerEl)
      .setName('Sync Interval')
      .setDesc('Interval between syncs in seconds')
      .addText((text) =>
        text
          .setPlaceholder('300')
          .setValue(String(this.plugin.settings.syncInterval))
          .onChange(async (value) => {
            const interval = parseInt(value);
            if (!isNaN(interval) && interval > 0) {
              this.plugin.settings.syncInterval = interval;
              await this.plugin.saveSettings();
              if (this.plugin.settings.autoSync) {
                this.plugin.startAutoSync();
              }
            }
          }),
      );
  }
}
