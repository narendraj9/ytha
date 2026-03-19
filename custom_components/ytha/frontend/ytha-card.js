class YthaCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = {};
    this._url = "";
    this._status = "idle";
    this._progress = 0;
    this._filename = "";
    this._error = "";
    this._unsub = null;
    this._rendered = false;
  }

  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._renderShell();
  }

  connectedCallback() {
    if (!this._rendered) this._renderShell();
  }

  disconnectedCallback() {
    if (this._unsub) {
      this._unsub();
      this._unsub = null;
    }
  }

  async _startDownload() {
    if (!this._url.trim()) return;

    this._status = "downloading";
    this._progress = 0;
    this._error = "";
    this._filename = "";
    this._updateUI();

    try {
      this._unsub = await this._hass.connection.subscribeEvents(
        (event) => this._handleProgress(event.data),
        "ytha_download_progress"
      );
      await this._hass.callService("ytha", "download_audio", {
        url: this._url.trim(),
      });
    } catch (err) {
      this._status = "error";
      this._error = err.message || "Failed to start download";
      this._unsub = null;
      this._updateUI();
    }
  }

  _handleProgress(data) {
    this._status = data.status === "starting" ? "downloading" : data.status;
    if (data.status === "downloading") {
      this._progress = data.progress || 0;
      this._filename = data.filename || "";
    } else if (data.status === "processing") {
      this._filename = data.filename || "";
    } else if (data.status === "complete") {
      this._progress = 100;
      this._filename = data.filename || "";
      this._cleanup();
    } else if (data.status === "error") {
      this._error = data.error || "Download failed";
      this._cleanup();
    }
    this._updateUI();
  }

  _cleanup() {
    if (this._unsub) {
      this._unsub();
      this._unsub = null;
    }
  }

  _renderShell() {
    this._rendered = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 16px; }
        .header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
        .header ha-icon { color: var(--primary-color); --mdc-icon-size: 24px; }
        .header .title { font-size: 1.1em; font-weight: 500; }
        .input-row { display: flex; gap: 8px; margin-bottom: 12px; }
        .input-row input {
          flex: 1; padding: 8px 12px;
          border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px;
          font-size: 14px; background: var(--card-background-color);
          color: var(--primary-text-color); outline: none;
        }
        .input-row input:focus { border-color: var(--primary-color); }
        .input-row input::placeholder { color: var(--secondary-text-color); }
        .btn {
          padding: 8px 20px; border: none; border-radius: 8px;
          font-size: 14px; font-weight: 500; cursor: pointer;
          background: var(--primary-color); color: var(--text-primary-color, #fff);
          transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.85; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .progress-section { display: none; }
        .progress-section.visible { display: block; }
        .progress-bar {
          height: 6px; background: var(--divider-color, #e0e0e0);
          border-radius: 3px; overflow: hidden; margin-bottom: 8px;
        }
        .progress-fill {
          height: 100%; border-radius: 3px; transition: width 0.3s ease;
          width: 0%;
        }
        .status { display: flex; align-items: center; gap: 6px; font-size: 13px; }
        .status ha-icon { --mdc-icon-size: 18px; }
        .filename {
          margin-top: 4px; font-size: 12px;
          color: var(--secondary-text-color); word-break: break-all;
          display: none;
        }
        .filename.visible { display: block; }
      </style>
      <ha-card>
        <div class="header">
          <ha-icon icon="mdi:music-box-multiple"></ha-icon>
          <span class="title">YTHA Audio Downloader</span>
        </div>
        <div class="input-row">
          <input type="text" placeholder="Paste video URL here..." />
          <button class="btn">Download</button>
        </div>
        <div class="progress-section">
          <div class="progress-bar"><div class="progress-fill"></div></div>
          <div class="status">
            <ha-icon icon="mdi:music-box-outline"></ha-icon>
            <span class="status-text">Ready</span>
          </div>
          <div class="filename"></div>
        </div>
      </ha-card>
    `;

    const input = this.shadowRoot.querySelector("input");
    const btn = this.shadowRoot.querySelector(".btn");

    input.addEventListener("input", (e) => { this._url = e.target.value; });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && this._url.trim() && !this._isActive()) {
        this._startDownload();
      }
    });
    btn.addEventListener("click", () => this._startDownload());
  }

  _isActive() {
    return this._status === "downloading" || this._status === "processing";
  }

  _updateUI() {
    const root = this.shadowRoot;
    if (!root) return;

    const isActive = this._isActive();
    const input = root.querySelector("input");
    const btn = root.querySelector(".btn");
    const section = root.querySelector(".progress-section");
    const fill = root.querySelector(".progress-fill");
    const icon = root.querySelector(".status ha-icon");
    const text = root.querySelector(".status-text");
    const filename = root.querySelector(".filename");

    input.disabled = isActive;
    btn.disabled = isActive || !this._url.trim();
    btn.textContent = isActive ? "Downloading..." : "Download";

    const colors = {
      idle: "var(--secondary-text-color)",
      downloading: "var(--info-color, #2196f3)",
      processing: "var(--warning-color, #ff9800)",
      complete: "var(--success-color, #4caf50)",
      error: "var(--error-color, #f44336)",
    };
    const icons = {
      idle: "mdi:music-box-outline",
      downloading: "mdi:download",
      processing: "mdi:cog",
      complete: "mdi:check-circle",
      error: "mdi:alert-circle",
    };
    const texts = {
      idle: "Ready",
      downloading: `Downloading... ${this._progress}%`,
      processing: "Processing audio...",
      complete: "Download complete",
      error: this._error || "Error",
    };

    const color = colors[this._status] || colors.idle;
    section.classList.toggle("visible", this._status !== "idle");
    fill.style.width = `${this._progress}%`;
    fill.style.background = color;
    icon.setAttribute("icon", icons[this._status] || icons.idle);
    text.textContent = texts[this._status] || texts.idle;
    text.style.color = color;

    const showFilename = this._filename && this._status === "complete";
    filename.classList.toggle("visible", showFilename);
    if (showFilename) filename.textContent = this._filename;
  }

  getCardSize() {
    return 2;
  }

  static getStubConfig() {
    return {};
  }
}

customElements.define("ytha-card", YthaCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "ytha-card",
  name: "YTHA Audio Downloader",
  description: "Download audio from video URLs to your media library.",
});
