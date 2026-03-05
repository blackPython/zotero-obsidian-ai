import { requestUrl } from 'obsidian';

export class BackendAPI {
  constructor(private backendUrl: string) {}

  private url(path: string): string {
    return `${this.backendUrl}${path}`;
  }

  async syncPapers(libraryId: string, apiKey: string, collectionKeys?: string[]): Promise<any> {
    const payload: any = { library_id: libraryId, api_key: apiKey };
    if (collectionKeys && collectionKeys.length > 0) {
      payload.collection_keys = collectionKeys;
    }
    const response = await requestUrl({
      url: this.url('/api/sync'),
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return JSON.parse(response.text);
  }

  async askQuestion(zoteroKey: string, question: string, context: string): Promise<string> {
    const response = await requestUrl({
      url: this.url('/api/qa'),
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zotero_key: zoteroKey, question, context }),
    });
    return JSON.parse(response.text).answer;
  }

  async runCustomAnalysis(zoteroKey: string, analysisType: string): Promise<any> {
    const response = await requestUrl({
      url: this.url('/api/custom-analysis'),
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zotero_key: zoteroKey, analysis_type: analysisType }),
    });
    return JSON.parse(response.text);
  }

  async updatePrompts(prompts: { analysis: string; qa: string; summary: string }): Promise<void> {
    await requestUrl({
      url: this.url('/api/update-prompts'),
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prompts),
    });
  }

  async getCollections(): Promise<any> {
    const response = await requestUrl({
      url: this.url('/api/collections'),
      method: 'GET',
    });
    return JSON.parse(response.text);
  }

  async getPaper(zoteroKey: string): Promise<any> {
    const response = await requestUrl({
      url: this.url(`/api/paper/${zoteroKey}`),
      method: 'GET',
    });
    return JSON.parse(response.text);
  }

  async reprocessPaper(zoteroKey: string): Promise<any> {
    const response = await requestUrl({
      url: this.url(`/api/reprocess/${zoteroKey}`),
      method: 'POST',
    });
    return JSON.parse(response.text);
  }

  async getAnalysis(zoteroKey: string): Promise<any> {
    const response = await requestUrl({
      url: this.url(`/api/paper/${zoteroKey}/analysis`),
      method: 'GET',
    });
    return JSON.parse(response.text);
  }

  async getPrompts(): Promise<any> {
    const response = await requestUrl({
      url: this.url('/api/prompts'),
      method: 'GET',
    });
    return JSON.parse(response.text);
  }
}
