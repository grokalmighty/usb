const { app, BrowserWindow, globalShortcut, ipcMain, dialog } = require('electron');
const path = require('path');
const isDev = proces.argv.includes('--dev');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 600,
        height: 500,
        show: false,
        frame: false,
        alwaysOnTop: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'));

    // Hide window when blurred
    mainWindow.on('blur', () => {
        if (!isDev) mainWindow.hide();
    });
}

function registerGlobalHotKey() {
    const ret = globalShortcut.register('CommandOrControl+Space', () => {
        if (mainWindow) {
            if (mainWindow.isVisible) {
                mainWindow.hide();
            } else {
                mainWindow.show();
                mainWindow.focus();
                mainWindow.webContents.send('focus-search');
            }
        }
    });

    if (!ret) {
        console.log('Global hotkey registration failed');
    }
}

app.whenReady().then(() => {
    createWindow();
    registerGlobalHotKey();

    app.on('acivate', function () {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});