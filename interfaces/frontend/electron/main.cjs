const path = require("node:path");
const { app, BrowserWindow, shell } = require("electron");

const DEV_URL =
  process.env.VITE_DEV_SERVER_URL ??
  process.env.ELECTRON_START_URL ??
  "http://127.0.0.1:5173/";
const ICON_PATH = path.join(__dirname, "..", "assets", "Charles_logo.png");
const RETRY_MS = 1000;

let mainWindow = null;
let retryTimer = null;

function clearRetry() {
  if (retryTimer !== null) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }
}

function isLocalUrl(url) {
  return (
    url.startsWith("http://127.0.0.1:") || url.startsWith("http://localhost:")
  );
}

function load() {
  if (!mainWindow) return;
  mainWindow.loadURL(DEV_URL).catch(() => scheduleLoad());
}

function scheduleLoad() {
  if (!mainWindow || retryTimer !== null) return;
  retryTimer = setTimeout(() => {
    retryTimer = null;
    load();
  }, RETRY_MS);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: "Charles",
    icon: ICON_PATH,
    backgroundColor: "#0b0b0f",
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow?.show());
  mainWindow.on("closed", () => {
    clearRetry();
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isLocalUrl(url)) return { action: "allow" };
    void shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.webContents.on(
    "did-fail-load",
    (_event, errorCode, _description, validatedUrl, isMainFrame) => {
      if (!isMainFrame || errorCode === -3) return;
      if (validatedUrl.startsWith(DEV_URL)) scheduleLoad();
    },
  );

  load();
}

app.setName("Charles");

app.whenReady().then(() => {
  if (process.platform === "darwin") app.dock.setIcon(ICON_PATH);
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  app.quit();
});
