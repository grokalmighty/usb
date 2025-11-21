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

    async indexDirectory(rootDir, options = {}) {
        if (this.isIndexing) {
            console.log('Indexing already in progress');
            return;
        }

        this.isIndexing = true;
        const startTime = Date.now();

        try {
            const defaultOptions = {
                maxDepth = 6,
                excludePatterns: [
                    'node_modules', '.git', '.vscode', '.idea',
                    'Library', 'AppData', 'Temp', 'tmp', 
                    'cache', 'Cache', 'log', 'logs'
                ],
                maxFileSize: 50 * 1024 * 1024 // 50MB
            };

            const finalOptions = {...defaultOptions, ...options };

            console.log(`Starting indexing: ${rootDir}`);
            await this._indexDirectoryRecursive(rootDir, 0, finalOptions);

            await this.saveIndex();

            const endTime = Date.now();
            console.log(`Indexing completed in ${(endTime - startTime) / 1000}s. ${this.index.size} files indexed.`);
        } catch (error) {
            console.error('Indexing failed:', error);
        } finally {
            this.isIndexing = false;
        }
    }

    async _indexDirectoryRecurisve(currentDir, depth, options) {
        if (depth > options.maxDepth) return;

        try {
            const items = await fs.readdir(currentDir, { withFileTypes: true});

            for (const item of items) {
                const fullPath = path.join(currentDir, item.name);

                // Skip excluded directories
                if (item.isDirectory()) {
                    if (this._shouldSkipDirectory(item.name, options.excludePatterns)) {
                        continue;
                    }
                    await this._indexDirectoryRecursive(fullPath, depth + 1, options);
                } else if (item.isFile()) {
                    await this._indexFile(fullPath, options);
                }
            }
        } catch (error) {
            // Skip directories we can't access
            if (error.code !== 'EACCES' && error.code !== 'EPERM') {
                console.log(`Skipping directory ${currentDir}: ${error.message}`);
            }
        }
    }
}