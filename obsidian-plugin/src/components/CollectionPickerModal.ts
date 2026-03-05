import { App, Modal, Notice } from 'obsidian';
import type ZoteroAIPlugin from '../main';

interface CollectionItem {
  key: string;
  name: string;
  path: string;
  parent: string | null;
  depth: number;
}

export class CollectionPickerModal extends Modal {
  plugin: ZoteroAIPlugin;
  private onSave: () => void;

  constructor(app: App, plugin: ZoteroAIPlugin, onSave: () => void) {
    super(app);
    this.plugin = plugin;
    this.onSave = onSave;
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('zotero-ai-collection-picker');

    contentEl.createEl('h2', { text: 'Select Collections' });
    contentEl.createEl('p', {
      text: 'Choose which Zotero collections to sync. Only papers in selected collections (and their sub-collections) will be processed.',
      cls: 'setting-item-description',
    });

    const loadingEl = contentEl.createEl('p', { text: 'Loading collections from Zotero...' });

    let collections: Record<string, any>;
    try {
      const result = await this.plugin.api.getCollections();
      collections = result.collections;
    } catch (error) {
      loadingEl.setText('Failed to load collections. Is the backend running?');
      console.error('Collection fetch error:', error);
      return;
    }

    loadingEl.remove();

    if (!collections || Object.keys(collections).length === 0) {
      contentEl.createEl('p', { text: 'No collections found in your Zotero library.' });
      return;
    }

    // Build sorted tree
    const items = this.buildTree(collections);

    // Currently selected keys
    const selectedKeys = new Set(
      this.plugin.settings.selectedCollections.map((c) => c.key),
    );

    // Create scrollable list
    const listContainer = contentEl.createDiv({
      attr: { style: 'max-height: 400px; overflow-y: auto; border: 1px solid var(--background-modifier-border); border-radius: 4px; padding: 8px; margin: 12px 0;' },
    });

    const checkboxes: Map<string, HTMLInputElement> = new Map();

    for (const item of items) {
      const row = listContainer.createDiv({
        attr: { style: `display: flex; align-items: center; padding: 4px 0; padding-left: ${item.depth * 20}px;` },
      });

      const checkbox = row.createEl('input', {
        type: 'checkbox',
        attr: { style: 'margin-right: 8px; flex-shrink: 0;' },
      });
      checkbox.checked = selectedKeys.has(item.key);
      checkboxes.set(item.key, checkbox);

      row.createEl('span', { text: item.name });
    }

    // Buttons
    const buttonRow = contentEl.createDiv({
      attr: { style: 'display: flex; justify-content: space-between; margin-top: 12px;' },
    });

    const leftButtons = buttonRow.createDiv();

    const selectAllBtn = leftButtons.createEl('button', { text: 'Select All' });
    selectAllBtn.setAttribute('style', 'margin-right: 8px;');
    selectAllBtn.onclick = () => {
      checkboxes.forEach((cb) => (cb.checked = true));
    };

    const clearBtn = leftButtons.createEl('button', { text: 'Clear All' });
    clearBtn.onclick = () => {
      checkboxes.forEach((cb) => (cb.checked = false));
    };

    const rightButtons = buttonRow.createDiv();

    const saveBtn = rightButtons.createEl('button', { text: 'Save', cls: 'mod-cta' });
    saveBtn.onclick = async () => {
      const selected: { key: string; name: string; path: string }[] = [];
      for (const item of items) {
        const cb = checkboxes.get(item.key);
        if (cb && cb.checked) {
          selected.push({ key: item.key, name: item.name, path: item.path });
        }
      }

      this.plugin.settings.selectedCollections = selected;
      await this.plugin.saveSettings();

      const count = selected.length;
      new Notice(
        count > 0
          ? `Saved ${count} collection${count > 1 ? 's' : ''}. Sync will only process papers in these collections.`
          : 'No collections selected. Sync is disabled until you select at least one.',
      );

      this.onSave();
      this.close();
    };
  }

  private buildTree(collections: Record<string, any>): CollectionItem[] {
    // Build parent → children map
    const childrenOf: Map<string | null, CollectionItem[]> = new Map();

    for (const [key, coll] of Object.entries(collections)) {
      const item: CollectionItem = {
        key,
        name: coll.name,
        path: coll.path,
        parent: coll.parent || null,
        depth: 0,
      };
      const parentKey = item.parent;
      if (!childrenOf.has(parentKey)) {
        childrenOf.set(parentKey, []);
      }
      childrenOf.get(parentKey)!.push(item);
    }

    // Sort each level alphabetically
    childrenOf.forEach((children) => children.sort((a, b) => a.name.localeCompare(b.name)));

    // DFS to produce ordered list with depths
    const result: CollectionItem[] = [];
    const visit = (parentKey: string | null, depth: number) => {
      const children = childrenOf.get(parentKey) || [];
      for (const child of children) {
        child.depth = depth;
        result.push(child);
        visit(child.key, depth + 1);
      }
    };
    visit(null, 0);

    return result;
  }

  onClose() {
    this.contentEl.empty();
  }
}
