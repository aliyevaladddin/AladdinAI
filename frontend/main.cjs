const { app, BrowserWindow } = require('electron');
const path = require('path');
const serve = require('electron-serve');

const loadURL = serve({ directory: 'out' });
const isDev = process.env.NODE_ENV === 'development';

function createWindow() {
  const win = new BrowserWindow({
    width: 1300,
    height: 850,
    minWidth: 1000,
    minHeight: 700,
    titleBarStyle: 'hiddenInset', 
    backgroundColor: '#131313', // Соответствует нашему дизайну
    show: false, // Покажем окно, когда оно будет готово
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs'), // Добавим прелоад на будущее
    },
  });

  if (isDev) {
    win.loadURL('http://localhost:3000');
    win.webContents.openDevTools();
  } else {
    loadURL(win);
  }

  win.once('ready-to-show', () => {
    win.show();
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
