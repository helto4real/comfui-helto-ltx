import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_NAME = "LTX23MultiImageLatentGuide";
const GUIDE_ROW_HEIGHT = 34;

function injectStyles() {
  if (document.getElementById("ltx23-guide-styles")) return;
  const style = document.createElement("style");
  style.id = "ltx23-guide-styles";
  style.textContent = `
    .ltx23-guide-root { box-sizing: border-box; font: 12px Arial, sans-serif; color: #ddd; width: 100%; max-width: 100%; overflow: hidden; background: #333; }
    .ltx23-guide-root * { box-sizing: border-box; }
    .ltx23-guide-toolbar { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 2px; }
    .ltx23-guide-toolbar button, .ltx23-guide-row button { background: #333; color: #ddd; border: 1px solid #555; border-radius: 4px; padding: 3px 6px; cursor: pointer; }
    .ltx23-guide-toolbar button { width: 28px; height: 28px; padding: 2px; font-size: 16px; line-height: 1; display: inline-flex; align-items: center; justify-content: center; }
    .ltx23-guide-toolbar svg { width: 17px; height: 17px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    .ltx23-guide-toolbar button:hover, .ltx23-guide-row button:hover { background: #444; }
    .ltx23-guide-list { width: 100%; min-width: 0; margin-top: 6px; max-height: 172px; overflow: hidden; border: 1px solid #333; border-radius: 4px; }
    .ltx23-guide-row { display: grid; grid-template-columns: 18px minmax(0, 1fr) 54px 48px 26px 26px 28px; gap: 4px; align-items: center; padding: 4px; border-bottom: 1px solid #2d2d2d; }
    .ltx23-guide-row:last-child { border-bottom: 0; }
    .ltx23-guide-row input, .ltx23-guide-row select { min-width: 0; background: #181818; color: #ddd; border: 1px solid #444; border-radius: 3px; padding: 2px 3px; }
    .ltx23-guide-row button { min-width: 0; height: 24px; padding: 1px 4px; }
    .ltx23-guide-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: zoom-in; }
    .ltx23-guide-preview { position: fixed; z-index: 10000; pointer-events: none; display: none; max-width: 520px; max-height: 380px; overflow: auto; background: #191919; border: 1px solid #555; border-radius: 6px; box-shadow: 0 8px 30px rgba(0,0,0,.45); padding: 8px; }
    .ltx23-guide-preview.visible { display: block; }
    .ltx23-guide-preview-item { display: grid; grid-template-columns: 74px 1fr; gap: 8px; padding: 5px; border-bottom: 1px solid #303030; }
    .ltx23-guide-preview-item:last-child { border-bottom: 0; }
    .ltx23-guide-preview-item img { max-width: 74px; max-height: 74px; object-fit: contain; background: #111; border: 1px solid #333; }
    .ltx23-guide-muted { color: #888; }
    .ltx23-guide-warning { color: #e6b85c; }
    .ltx23-guide-dialog { position: fixed; z-index: 10001; inset: 0; background: rgba(0,0,0,.55); display: flex; align-items: center; justify-content: center; }
    .ltx23-guide-dialog-panel { width: 620px; max-width: 92vw; max-height: 84vh; overflow: auto; background: #222; border: 1px solid #555; border-radius: 6px; padding: 14px; color: #ddd; }
    .ltx23-guide-dialog-panel h3 { margin: 0 0 10px; font-size: 15px; }
    .ltx23-guide-dialog-row { display: grid; grid-template-columns: 110px 1fr; gap: 8px; margin-bottom: 8px; align-items: center; }
    .ltx23-guide-dialog-row input, .ltx23-guide-dialog-row select { background: #151515; color: #ddd; border: 1px solid #555; border-radius: 4px; padding: 6px; }
    .ltx23-guide-dialog-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
    .ltx23-guide-dialog-actions button { background: #333; color: #ddd; border: 1px solid #555; border-radius: 4px; padding: 6px 10px; cursor: pointer; }
    .ltx23-guide-browser-controls { display: grid; grid-template-columns: 1fr auto minmax(130px, 180px); gap: 8px; align-items: center; margin-bottom: 8px; }
    .ltx23-guide-browser-controls select, .ltx23-guide-browser-controls input { background: #151515; color: #ddd; border: 1px solid #555; border-radius: 4px; padding: 6px; }
    .ltx23-guide-browser-controls button { background: #333; color: #ddd; border: 1px solid #555; border-radius: 4px; padding: 6px 10px; cursor: pointer; }
    .ltx23-guide-browser-icon-button { width: 32px; height: 32px; padding: 4px !important; display: inline-flex; align-items: center; justify-content: center; }
    .ltx23-guide-browser-icon-button svg, .ltx23-guide-columns-control svg { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    .ltx23-guide-columns-control { display: grid; grid-template-columns: 22px 1fr 18px; gap: 6px; align-items: center; color: #ddd; }
    .ltx23-guide-columns-control input { width: 100%; min-width: 0; }
    .ltx23-guide-browser-options { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin: 8px 0; color: #ccc; }
    .ltx23-guide-browser-options button { background: #333; color: #ddd; border: 1px solid #555; border-radius: 4px; padding: 6px 10px; cursor: pointer; }
    .ltx23-guide-browser-grid { --ltx23-guide-columns: 4; display: grid; grid-template-columns: repeat(var(--ltx23-guide-columns), minmax(0, 1fr)); gap: 8px; max-height: 52vh; overflow: auto; padding: 2px; }
    .ltx23-guide-browser-grid.hide-images .ltx23-guide-tile img { opacity: 0; }
    .ltx23-guide-dialog-panel:hover .ltx23-guide-browser-grid.hide-images .ltx23-guide-tile img { opacity: 1; }
    .ltx23-guide-browser-grid.show-images .ltx23-guide-tile img { opacity: 1; }
    .ltx23-guide-tile { min-width: 0; background: #181818; border: 1px solid #444; border-radius: 5px; padding: 5px; color: #ddd; cursor: pointer; text-align: left; }
    .ltx23-guide-tile.selected { border-color: #8ab4f8; background: #202a36; }
    .ltx23-guide-tile img { display: block; width: 100%; aspect-ratio: 1 / 1; object-fit: contain; background: #101010; border: 1px solid #2d2d2d; border-radius: 3px; transition: opacity .12s ease; }
    .ltx23-guide-browser-meta { margin-top: 8px; color: #aaa; font-size: 11px; min-height: 14px; }
    .ltx23-guide-large-preview { position: fixed; z-index: 10003; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,.72); padding: 24px; }
    .ltx23-guide-large-preview-panel { position: relative; max-width: 92vw; max-height: 92vh; background: #151515; border: 1px solid #555; border-radius: 6px; padding: 10px; box-shadow: 0 12px 44px rgba(0,0,0,.55); }
    .ltx23-guide-large-preview-panel img { display: block; max-width: calc(92vw - 20px); max-height: calc(92vh - 52px); object-fit: contain; background: #0b0b0b; }
    .ltx23-guide-large-preview-close { position: absolute; top: 8px; right: 8px; width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; background: rgba(20,20,20,.88); color: #ddd; border: 1px solid #666; border-radius: 4px; cursor: pointer; }
    .ltx23-guide-large-preview-close svg { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    .ltx23-guide-large-preview-caption { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: calc(92vw - 20px); margin-top: 7px; color: #aaa; font-size: 12px; }
  `;
  document.head.appendChild(style);
}

function getWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

function getWidgetValue(node, name, fallback) {
  const widget = getWidget(node, name);
  return widget ? widget.value : fallback;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  })[char]);
}

function hideWidget(widget) {
  if (!widget) return;
  widget.type = "hidden";
  widget.label = "";
  widget.hidden = true;
  widget.options = { ...(widget.options || {}), hidden: true };
  widget.draw = () => {};
  widget.computeSize = () => [0, -4];
  for (const element of [widget.element, widget.inputEl]) {
    if (!element?.style) continue;
    element.style.display = "none";
    element.style.width = "0px";
    element.style.height = "0px";
    element.style.opacity = "0";
    element.style.pointerEvents = "none";
  }
}

function hideGuidesWidget(node) {
  const widget = getWidget(node, "guides_json");
  if (!widget) return null;
  hideWidget(widget);
  widget.serializeValue = () => widget.value || "{\"version\":1,\"guides\":[]}";
  return widget;
}

function nodeInnerWidth(node) {
  return Math.max((node.size?.[0] || 390) - 28, 320);
}

function guideWidgetHeight(node) {
  const rowCount = readGuides(node).length;
  const visibleRows = Math.min(rowCount, 5);
  const listHeight = visibleRows > 0 ? visibleRows * GUIDE_ROW_HEIGHT + 2 : 0;
  return 76 + listHeight;
}

function updateNodeHeight(node) {
  if (!node?._ltx23) return;
  const guides = readGuides(node);
  const rowCount = guides.length;
  const innerWidth = nodeInnerWidth(node);
  const list = node._ltx23.list;
  if (list) {
    if (rowCount === 0) {
      list.style.display = "none";
      list.style.height = "0px";
    } else {
      const visibleRows = Math.min(rowCount, 5);
      const height = visibleRows * GUIDE_ROW_HEIGHT + 2;
      list.style.display = "";
      list.style.height = `${height}px`;
      list.style.maxHeight = `${height}px`;
      list.style.overflowY = rowCount > visibleRows ? "auto" : "hidden";
    }
  }
  if (node._ltx23.container) {
    node._ltx23.container.style.height = `${guideWidgetHeight(node)}px`;
    node._ltx23.container.style.width = `${innerWidth}px`;
    node._ltx23.container.style.maxWidth = `${innerWidth}px`;
  }
  if (node._ltx23.widget?.element) {
    node._ltx23.widget.element.style.width = `${innerWidth}px`;
    node._ltx23.widget.element.style.maxWidth = `${innerWidth}px`;
  }
  requestAnimationFrame(() => {
    const width = Math.max(node.size?.[0] || 390, 390);
    if (node.computeSize) {
      const computed = node.computeSize();
      node.setSize([width, computed[1]]);
    }
    node.setDirtyCanvas(true, true);
  });
}

function setGuidesJson(node) {
  const widget = getWidget(node, "guides_json");
  const payload = {
    version: 1,
    timing_mode: getWidgetValue(node, "timing_mode", "frame"),
    fps: Number(getWidgetValue(node, "fps", 24)),
    width: Number(getWidgetValue(node, "width", 768)),
    height: Number(getWidgetValue(node, "height", 512)),
    guides: node.properties.ltx23_guides || [],
  };
  if (widget) widget.value = JSON.stringify(payload);
  node.properties.ltx23_guides_json = widget?.value || JSON.stringify(payload);
  updateSummary(node);
  node.setDirtyCanvas(true, false);
}

function readGuides(node) {
  node.properties = node.properties || {};
  if (Array.isArray(node.properties.ltx23_guides)) return node.properties.ltx23_guides;
  const widget = getWidget(node, "guides_json");
  const raw = node.properties.ltx23_guides_json || widget?.value || "";
  try {
    const parsed = JSON.parse(raw);
    node.properties.ltx23_guides = Array.isArray(parsed.guides) ? parsed.guides : [];
  } catch {
    node.properties.ltx23_guides = [];
  }
  return node.properties.ltx23_guides;
}

function calcFrame(node, guide) {
  const timingMode = getWidgetValue(node, "timing_mode", "frame");
  const fps = Number(getWidgetValue(node, "fps", 24));
  const numFrames = Math.max(1, Number(getWidgetValue(node, "num_frames", 97)));
  const raw = Number(guide.position || 0);
  let frame = timingMode === "seconds" ? Math.round(raw * fps) : Math.round(raw);
  if (frame < 0) frame = numFrames + frame;
  return Math.max(0, Math.min(numFrames - 1, frame));
}

function timelineText(node) {
  const guides = readGuides(node)
    .filter((guide) => guide.enabled !== false)
    .map((guide) => ({ ...guide, calculated_frame: calcFrame(node, guide) }))
    .sort((a, b) => a.calculated_frame - b.calculated_frame);
  if (!guides.length) return "No guides";
  const parts = guides.slice(0, 4).map((guide) => `${guide.calculated_frame}f ${guide.filename}`);
  return `${guides.length} guides: ${parts.join(", ")}${guides.length > 4 ? `, +${guides.length - 4} more` : ""}`;
}

function updateSummary(node) {
  node.title = "LTX 2.3 Multi Image Latent Guide";
}

async function fetchJson(url, options) {
  const response = await api.fetchApi(url, options);
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || response.statusText);
  return data;
}

function closeDialog() {
  closeLargePreview();
  document.querySelector(".ltx23-guide-dialog")?.remove();
}

function closeLargePreview() {
  document.querySelector(".ltx23-guide-large-preview")?.remove();
}

function showLargePreview(alias, image) {
  closeLargePreview();
  const overlay = document.createElement("div");
  overlay.className = "ltx23-guide-large-preview";
  const imageUrl = `/ltx23_guides/image?alias=${encodeURIComponent(alias)}&filename=${encodeURIComponent(image.filename)}&t=${encodeURIComponent(image.mtime || 0)}`;
  overlay.innerHTML = `
    <div class="ltx23-guide-large-preview-panel">
      <button class="ltx23-guide-large-preview-close" type="button" title="Close preview" aria-label="Close preview">
        <svg viewBox="0 0 24 24"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
      </button>
      <img src="${escapeHtml(imageUrl)}" alt="">
      <div class="ltx23-guide-large-preview-caption">${escapeHtml(image.filename)} (${image.width || "?"}x${image.height || "?"})</div>
    </div>`;
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay || event.target.closest(".ltx23-guide-large-preview-close")) closeLargePreview();
  });
  document.body.appendChild(overlay);
}

function showDialog(title, body, onOk) {
  closeDialog();
  const overlay = document.createElement("div");
  overlay.className = "ltx23-guide-dialog";
  overlay.innerHTML = `
    <div class="ltx23-guide-dialog-panel">
      <h3>${title}</h3>
      <div class="ltx23-guide-dialog-body"></div>
      <div class="ltx23-guide-dialog-actions">
        <button data-action="cancel">Cancel</button>
        <button data-action="ok">OK</button>
      </div>
    </div>`;
  overlay.querySelector(".ltx23-guide-dialog-body").appendChild(body);
  overlay.addEventListener("click", async (event) => {
    if (event.target === overlay || event.target.dataset.action === "cancel") closeDialog();
    if (event.target.dataset.action === "ok") {
      try {
        await onOk();
        closeDialog();
      } catch (error) {
        alert(error.message);
      }
    }
  });
  document.body.appendChild(overlay);
}

async function chooseGuide(node) {
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="ltx23-guide-browser-controls">
      <select class="folder" title="Folder"></select>
      <button class="scope ltx23-guide-browser-icon-button" type="button" title="Recursive folder view" aria-label="Recursive folder view"></button>
      <label class="ltx23-guide-columns-control" title="Images per row">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        <input class="columns" type="range" min="2" max="8" step="1" value="4">
        <span class="columns-value">4</span>
      </label>
    </div>
    <div class="ltx23-guide-browser-options">
      <button class="hover-hide ltx23-guide-browser-icon-button" type="button" title="Hide images until hovering over window" aria-label="Hide images until hovering over window"></button>
    </div>
    <div class="ltx23-guide-browser-grid hide-images"></div>
    <div class="ltx23-guide-browser-meta"></div>
    <div class="ltx23-guide-dialog-row"><label>Position</label><input class="position" type="number" step="0.01" value="0"></div>
    <div class="ltx23-guide-dialog-row"><label>Strength</label><input class="strength" type="number" min="0" max="1" step="0.01" value="1"></div>
    <div class="ltx23-guide-dialog-row"><label>Label</label><input class="label" type="text"></div>`;
  const folderSelect = body.querySelector(".folder");
  const scopeButton = body.querySelector(".scope");
  const columnsInput = body.querySelector(".columns");
  const columnsValue = body.querySelector(".columns-value");
  const hoverHideButton = body.querySelector(".hover-hide");
  const grid = body.querySelector(".ltx23-guide-browser-grid");
  const meta = body.querySelector(".ltx23-guide-browser-meta");
  let availableImages = [];
  let selectedImage = null;
  let recursive = true;
  let hideImagesUntilHover = true;
  const folders = (await fetchJson("/ltx23_guides/folders")).folders;
  folderSelect.innerHTML = folders.map((folder) => `<option value="${folder.alias}">${folder.alias}${folder.exists ? "" : " (missing)"}</option>`).join("");
  function syncScopeButton() {
    scopeButton.title = recursive ? "Recursive folder view" : "Folder-only view";
    scopeButton.setAttribute("aria-label", scopeButton.title);
    scopeButton.innerHTML = recursive
      ? `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h6l2 2h9a2 2 0 0 1 2 2v2"/><path d="M6 12v6a2 2 0 0 0 2 2h5"/><path d="M10 15h4l1.5 1.5H21v3.5H10z"/></svg>`
      : `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`;
  }
  function syncGridVisibility() {
    hoverHideButton.title = hideImagesUntilHover ? "Hide images until hovering over window" : "Always show images";
    hoverHideButton.setAttribute("aria-label", hoverHideButton.title);
    hoverHideButton.innerHTML = hideImagesUntilHover
      ? `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="3"/><path d="M3 3l18 18"/></svg>`
      : `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="3"/></svg>`;
    grid.classList.toggle("hide-images", hideImagesUntilHover);
    grid.classList.toggle("show-images", !hideImagesUntilHover);
  }
  function syncColumns() {
    const columns = Number(columnsInput.value || 4);
    grid.style.setProperty("--ltx23-guide-columns", String(columns));
    columnsValue.textContent = String(columns);
  }
  function renderImageGrid() {
    grid.innerHTML = "";
    selectedImage = null;
    for (const image of availableImages) {
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "ltx23-guide-tile";
      tile.title = image.filename;
      tile.innerHTML = `
        <img src="${escapeHtml(image.thumb_url)}" alt="">`;
      tile.addEventListener("click", (event) => {
        if (event.ctrlKey) {
          showLargePreview(folderSelect.value, image);
          return;
        }
        selectedImage = image;
        for (const other of grid.querySelectorAll(".ltx23-guide-tile")) other.classList.remove("selected");
        tile.classList.add("selected");
        meta.textContent = `${image.filename} (${image.width || "?"}x${image.height || "?"})`;
      });
      grid.appendChild(tile);
    }
    meta.textContent = availableImages.length ? `${availableImages.length} images. Select one to add.` : "No images found.";
    syncGridVisibility();
  }
  async function loadImages() {
    const data = await fetchJson(`/ltx23_guides/images?alias=${encodeURIComponent(folderSelect.value)}&recursive=${recursive ? "1" : "0"}`);
    availableImages = data.images;
    renderImageGrid();
  }
  folderSelect.addEventListener("change", loadImages);
  scopeButton.addEventListener("click", async () => {
    recursive = !recursive;
    syncScopeButton();
    await loadImages();
  });
  columnsInput.addEventListener("input", syncColumns);
  hoverHideButton.addEventListener("click", () => {
    hideImagesUntilHover = !hideImagesUntilHover;
    syncGridVisibility();
  });
  syncColumns();
  syncScopeButton();
  await loadImages();
  showDialog("Add Guide Image", body, async () => {
    if (!selectedImage) throw new Error("Select an image first.");
    const guide = {
      folder_alias: folderSelect.value,
      filename: selectedImage.filename,
      position: Number(body.querySelector(".position").value || 0),
      calculated_frame: 0,
      strength: Number(body.querySelector(".strength").value || 1),
      label: body.querySelector(".label").value || "",
      enabled: true,
    };
    guide.width = selectedImage.width || 0;
    guide.height = selectedImage.height || 0;
    guide.calculated_frame = calcFrame(node, guide);
    readGuides(node).push(guide);
    renderRows(node);
    setGuidesJson(node);
  });
}

function showFolderDialog(node) {
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="ltx23-guide-dialog-row"><label>Alias</label><input class="alias" type="text"></div>
    <div class="ltx23-guide-dialog-row"><label>Path</label><input class="path" type="text" placeholder="/path/to/images"></div>`;
  showDialog("Add Folder", body, async () => {
    await fetchJson("/ltx23_guides/folders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alias: body.querySelector(".alias").value, path: body.querySelector(".path").value }),
    });
  });
}

async function removeFolderDialog() {
  const body = document.createElement("div");
  body.innerHTML = `<div class="ltx23-guide-dialog-row"><label>Folder</label><select class="folder"></select></div>`;
  const folders = (await fetchJson("/ltx23_guides/folders")).folders.filter((folder) => folder.alias !== "input");
  body.querySelector(".folder").innerHTML = folders.map((folder) => `<option value="${folder.alias}">${folder.alias}</option>`).join("");
  showDialog("Remove Folder", body, async () => {
    const alias = body.querySelector(".folder").value;
    await fetchJson(`/ltx23_guides/folders?alias=${encodeURIComponent(alias)}`, { method: "DELETE" });
  });
}

function renderRows(node) {
  const list = node._ltx23?.list;
  if (!list) return;
  const guides = readGuides(node);
  list.innerHTML = "";
  for (const [index, guide] of guides.entries()) {
    guide.calculated_frame = calcFrame(node, guide);
    const row = document.createElement("div");
    row.className = "ltx23-guide-row";
    row.innerHTML = `
      <input class="enabled" type="checkbox" ${guide.enabled !== false ? "checked" : ""} title="Enabled">
      <div class="ltx23-guide-name" title="${guide.folder_alias}/${guide.filename}">${guide.filename}</div>
      <input class="position" type="number" step="0.01" value="${guide.position ?? 0}" title="Position">
      <input class="strength" type="number" min="0" max="1" step="0.01" value="${guide.strength ?? 1}" title="Strength">
      <button class="up" title="Move up">↑</button>
      <button class="down" title="Move down">↓</button>
      <button class="remove" title="Remove">×</button>`;
    row.querySelector(".enabled").addEventListener("change", (event) => {
      guide.enabled = event.target.checked;
      setGuidesJson(node);
    });
    row.querySelector(".position").addEventListener("change", (event) => {
      guide.position = Number(event.target.value || 0);
      guide.calculated_frame = calcFrame(node, guide);
      setGuidesJson(node);
      renderRows(node);
    });
    row.querySelector(".strength").addEventListener("change", (event) => {
      guide.strength = Number(event.target.value || 1);
      setGuidesJson(node);
    });
    row.querySelector(".remove").addEventListener("click", () => {
      guides.splice(index, 1);
      setGuidesJson(node);
      renderRows(node);
    });
    row.querySelector(".up").addEventListener("click", () => {
      if (index <= 0) return;
      [guides[index - 1], guides[index]] = [guides[index], guides[index - 1]];
      setGuidesJson(node);
      renderRows(node);
    });
    row.querySelector(".down").addEventListener("click", () => {
      if (index >= guides.length - 1) return;
      [guides[index + 1], guides[index]] = [guides[index], guides[index + 1]];
      setGuidesJson(node);
      renderRows(node);
    });
    const name = row.querySelector(".ltx23-guide-name");
    name.addEventListener("mouseenter", (event) => showPreviewForGuide(node, guide, event));
    name.addEventListener("mousemove", (event) => positionPreview(node, event));
    name.addEventListener("mouseleave", () => hidePreview(node));
    list.appendChild(row);
  }
  updateSummary(node);
  updateNodeHeight(node);
}

async function saveGuideSet(node) {
  const name = prompt("Guide set name");
  if (!name) return;
  const payload = JSON.parse(getWidget(node, "guides_json")?.value || "{}");
  await fetchJson(`/ltx23_guides/guide_sets/${encodeURIComponent(name)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function loadGuideSet(node) {
  const sets = (await fetchJson("/ltx23_guides/guide_sets")).guide_sets;
  const body = document.createElement("div");
  body.innerHTML = `<div class="ltx23-guide-dialog-row"><label>Set</label><select class="set"></select></div>`;
  body.querySelector(".set").innerHTML = sets.map((name) => `<option value="${name}">${name}</option>`).join("");
  showDialog("Load Guide Set", body, async () => {
    const name = body.querySelector(".set").value;
    const data = await fetchJson(`/ltx23_guides/guide_sets/${encodeURIComponent(name)}`);
    node.properties.ltx23_guides = Array.isArray(data.guides) ? data.guides : [];
    renderRows(node);
    setGuidesJson(node);
  });
}

function setupPreview(node, container) {
  const panel = document.createElement("div");
  panel.className = "ltx23-guide-preview";
  document.body.appendChild(panel);
  node._ltx23.preview = panel;

  const onRemoved = node.onRemoved;
  node.onRemoved = function () {
    panel.remove();
    onRemoved?.apply(this, arguments);
  };
}

function positionPreview(node, event) {
  const panel = node._ltx23?.preview;
  if (!panel) return;
  panel.style.left = `${Math.min(window.innerWidth - 540, event.clientX + 14)}px`;
  panel.style.top = `${Math.min(window.innerHeight - 400, event.clientY + 14)}px`;
}

function hidePreview(node) {
  node._ltx23?.preview?.classList.remove("visible");
}

function showPreviewForGuide(node, guide, event) {
  const panel = node._ltx23?.preview;
  if (!panel) return;
  const targetRatio = Number(getWidgetValue(node, "width", 768)) / Number(getWidgetValue(node, "height", 512));
  const guideRatio = guide.width && guide.height ? guide.width / guide.height : targetRatio;
  const ratioWarning = Math.abs(targetRatio - guideRatio) > 0.02;
  const thumbUrl = `/ltx23_guides/thumb?alias=${encodeURIComponent(guide.folder_alias)}&filename=${encodeURIComponent(guide.filename)}`;
  panel.innerHTML = `
    <div class="ltx23-guide-preview-item">
      <img src="${thumbUrl}" alt="">
      <div>
        <div>${guide.filename}</div>
        <div class="ltx23-guide-muted">${guide.folder_alias}</div>
        <div>${guide.position}${getWidgetValue(node, "timing_mode", "frame") === "seconds" ? "s" : "f"} -> ${calcFrame(node, guide)}f</div>
        <div>strength ${guide.strength ?? 1}</div>
        <div>${guide.enabled === false ? "disabled" : "enabled"}</div>
        ${ratioWarning ? `<div class="ltx23-guide-warning">aspect ratio differs</div>` : ""}
      </div>
    </div>`;
  positionPreview(node, event);
  panel.classList.add("visible");
}

function setupNode(node) {
  injectStyles();
  node.properties = node.properties || {};
  readGuides(node);

  hideGuidesWidget(node);

  const container = document.createElement("div");
  container.className = "ltx23-guide-root";
  container.innerHTML = `
    <div class="ltx23-guide-toolbar">
      <button data-action="add" title="Add guide image" aria-label="Add guide image">
        <svg viewBox="0 0 24 24"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
      </button>
      <button data-action="folder-add" title="Add folder" aria-label="Add folder">
        <svg viewBox="0 0 24 24"><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 14h6"/><path d="M15 11v6"/></svg>
      </button>
      <button data-action="folder-remove" title="Remove folder" aria-label="Remove folder">
        <svg viewBox="0 0 24 24"><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 14h6"/></svg>
      </button>
      <button data-action="refresh" title="Refresh folders and images" aria-label="Refresh folders and images">
        <svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 0 1-13.7 5.7"/><path d="M4 12A8 8 0 0 1 17.7 6.3"/><path d="M7 18H3v-4"/><path d="M17 6h4v4"/></svg>
      </button>
      <button data-action="save" title="Save guide set" aria-label="Save guide set">
        <svg viewBox="0 0 24 24"><path d="M5 3h12l2 2v16H5z"/><path d="M8 3v6h8V3"/><path d="M8 21v-7h8v7"/></svg>
      </button>
      <button data-action="load" title="Load guide set" aria-label="Load guide set">
        <svg viewBox="0 0 24 24"><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 15h6"/><path d="M15 12l3 3-3 3"/></svg>
      </button>
    </div>
    <div class="ltx23-guide-list"></div>`;
  const guideWidget = node.addDOMWidget("guide_manager", "div", container, { serialize: false });
  guideWidget.computeSize = () => [nodeInnerWidth(node), guideWidgetHeight(node)];
  guideWidget.serialize = false;
  node._ltx23 = {
    container,
    widget: guideWidget,
    list: container.querySelector(".ltx23-guide-list"),
  };
  setupPreview(node, container);

  container.addEventListener("click", async (event) => {
    const action = event.target?.closest?.("button[data-action]")?.dataset?.action;
    if (!action) return;
    try {
      if (action === "add") await chooseGuide(node);
      if (action === "folder-add") showFolderDialog(node);
      if (action === "folder-remove") await removeFolderDialog();
      if (action === "refresh") {
        await fetchJson("/ltx23_guides/refresh", { method: "POST" });
        renderRows(node);
      }
      if (action === "save") await saveGuideSet(node);
      if (action === "load") await loadGuideSet(node);
    } catch (error) {
      alert(error.message);
    }
  });

  for (const name of ["timing_mode", "fps", "num_frames", "width", "height"]) {
    const widget = getWidget(node, name);
    if (!widget) continue;
    const callback = widget.callback;
    widget.callback = function () {
      callback?.apply(this, arguments);
      for (const guide of readGuides(node)) guide.calculated_frame = calcFrame(node, guide);
      renderRows(node);
      setGuidesJson(node);
    };
  }

  const onSerialize = node.onSerialize;
  node.onSerialize = function (info) {
    setGuidesJson(this);
    onSerialize?.apply(this, arguments);
    info.properties = { ...(info.properties || {}), ltx23_guides: readGuides(this), ltx23_guides_json: getWidget(this, "guides_json")?.value };
  };

  const onConfigure = node.onConfigure;
  node.onConfigure = function (info) {
    onConfigure?.apply(this, arguments);
    hideGuidesWidget(this);
    if (info?.properties?.ltx23_guides) this.properties.ltx23_guides = info.properties.ltx23_guides;
    renderRows(this);
    setGuidesJson(this);
  };

  const onResize = node.onResize;
  node.onResize = function () {
    onResize?.apply(this, arguments);
    updateNodeHeight(this);
  };

  const onDrawForeground = node.onDrawForeground;
  node.onDrawForeground = function () {
    onDrawForeground?.apply(this, arguments);
    hideGuidesWidget(this);
    if (this._ltx23) {
      const width = `${nodeInnerWidth(this)}px`;
      if (this._ltx23.container?.style.width !== width) {
        this._ltx23.container.style.width = width;
        this._ltx23.container.style.maxWidth = width;
      }
      if (this._ltx23.widget?.element?.style.width !== width) {
        this._ltx23.widget.element.style.width = width;
        this._ltx23.widget.element.style.maxWidth = width;
      }
    }
  };

  renderRows(node);
  setGuidesJson(node);
}

app.registerExtension({
  name: "helto.ltx23.multi_image_latent_guide",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      setupNode(this);
      return result;
    };
  },
});
