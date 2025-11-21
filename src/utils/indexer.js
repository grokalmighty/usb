const fs = require('fs').promises;
const path = require('path');

class FileIndexer {
    constructor() {
        this.index = new Map();
        this.isIndexing = false;
        this.indexVersion = 1;
        this.supportedFileTypes = new Set([
            'txt', 'md', 'js', 'html', 'css', 'json', 'xml', 'csv',
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
            'jpg', 'jpeg', 'png', 'gif', 'svg', 'mp3', 'mp4', 'avi',
            'mov', 'wav', 'zip', 'rar', '7z'
        ]);
    }

    async initialize(userDataPath) {
        this.indexPath = path.join(userDataPath, 'search-index.json');
        await this.loadIndex();
    }

    async loadIndex() {
        try {
            const data = await fs.readFile(this.indexPath, 'utf8');
            const savedIndex = JSON.parse(data);

            if (savedIndex.version === this.indexVersion) {
                this.index = new Map(savedIndex.index);
                console.log(`Loaded index with ${this.index.size} files`);
                return true;
            }
        } catch (error) {
            console.log('No existing index found, creating new one');
        }
        return false;
    }

    async saveIndex() {
        try {
            const indexData = {
                version: this.indexVersion,
                index: Array.from(this.index.entries()),
                lastUpdated: new Date().toISOSring()
            };

            await fs.writeFile(this.indexPath, JSON.stringify(indexData, null, 2));
            console.log(`Saved index with ${this.index.size} files`);
            return true;
        } catch (error) {
            console.error('Failed to save index:', error);
            return false; 
        }
    }
}