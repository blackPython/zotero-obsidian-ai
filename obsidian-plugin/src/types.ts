export interface ZoteroCollection {
  key: string;
  name: string;
  path: string;
  parent: string | null;
}

export interface ZoteroAISettings {
  backendUrl: string;
  notesFolder: string;
  maintainLibraryStructure: boolean;
  autoSync: boolean;
  syncInterval: number;
  promptTemplates: {
    analysis: string;
    qa: string;
    summary: string;
  };
  zoteroApiKey: string;
  zoteroLibraryId: string;
  zoteroLibraryType: string;
  selectedCollections: { key: string; name: string; path: string }[];
}

export const DEFAULT_SETTINGS: ZoteroAISettings = {
  backendUrl: 'http://localhost:8000',
  notesFolder: 'Research Papers',
  maintainLibraryStructure: true,
  autoSync: true,
  syncInterval: 300,
  promptTemplates: {
    analysis: '',
    qa: '',
    summary: '',
  },
  zoteroApiKey: '',
  zoteroLibraryId: '',
  zoteroLibraryType: 'user',
  selectedCollections: [],
};
