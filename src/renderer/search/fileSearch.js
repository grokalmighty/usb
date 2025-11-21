class FileSearch {
    constructor () {
        this.index = [];
        this.isIndexing = false;
        this.startIndexing();
    }

    async startIndexing() {
        if (this.isIndexing) return;

        this.isIndexing = true;
        try {
            // Index common directories
            const homeDir = await window.electronAPI.getHomeDirectory();
            await this.indexDirectory(homeDir);
        } catch (error) {
            console.error('Indexing failed:', error);
        }
        this.isIndexing = false;
    }

    async indexDirectory(dirPath) {
        try {
            const files = await window.electronAPI.readDirectory(dirPath);

            for (const file of files) {
                const fullPath = `${dirPath}/${file}`;
                const stats = await window.electronAPI.getStats(fullPath);

                if (stats.isDirectory()) {
                    // Skip node_modules and other large directories
                    if (!this.shouldSkipDirectory(file)) {
                        await this.indexDirectory(fullPath);
                    }
                } else {
                    this.index.push({
                        name: file,
                        path: fullPath,
                        type: this.getFileType(file)
                    });
                }
            }
        } catch (error) {
            // Skip directories we can't access
        }
    }

    shouldSkipDirectory(dirName) {
        const SkipDirs = ['node_modules', '.git', '.vscode', 'Library'];
        return SkipDirs.includes(dirName);
    }

    getFileType(fileName) {
        const extension = fileName.split('.').pop().toLowerCase();
        const typeMap = {
            'js': 'JavaScript',
            'html': 'HTML',
            'css': 'CSS',
            'md': 'Markdown',
            'txt': 'Text',
            'pdf': 'PDF',
            'doc': 'Word',
            'docx': 'Word'
        };
        return typeMap[extension] || 'File';
    }

    async search(query) {
        if (!query || this.index.length === 0) return [];

        const lowercaseQuery = query.toLowerCase();
        const results = this.index
            .filter(file =>
                file.name.toLowerCase().includes(lowercaseQuery) ||
                file.path.toLowerCase().includes(lowercaseQuery)
            )
            .slice(0, 20)
            .map(file => ({
                title: file.name,
                subtitle: file.path,
                path: file.path,
                type: 'file',
                icon: this.getFileIcon(file.name),
                shortcut: 'Enter to open'
            }));
        
        return results;
    }
}