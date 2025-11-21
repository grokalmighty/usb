class CustomCommands {
    consructor() {
        this.commands = [
            {
                name: 'create-note',
                title: 'Create New Note',
                description: 'Create a new markdown note in project folder',
                icon: '📝',
                execute: () => this.createNote()
            },
            {
                name: 'clear-trash',
                title: 'Empty Trash',
                description: 'Permanently delete all items in trash',
                icon: '🗑️',
                execute: () => this.clearTrash()
            },
            {
                name: 'screenshot',
                title: 'Take Screenshot',
                description: 'Capture screen area',
                icon: '📸',
                execute: () => this.takeScreenshot()
            }
        ];
    }

    async search(query) {
        if (!query) return [];

        const lowercaseQuery = query.toLowerCase();
        const results = this.commands
            .filter(cmd =>
                    cmd.title.toLowerCase().includes(lowercaseQuery) ||
                    cmd.description.toLowerCase().includes(lowercaseQuery)
            )
            .map(cmd => ({
                title: cmd.title,
                subtitle: cmd.description,
                type: 'command',
                icon: cmd.icon,
                execute: cmd.execute,
                shortcut: 'Enter to execute'
            }));
        
        return results;
    }
}