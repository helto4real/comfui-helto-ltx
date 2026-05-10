import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_NAME = "LTX23MultiImageLatentGuide";

function injectStyles() {
  if (document.getElementById("ltx23-guide-styles")) return;
  const style = document.createElement("style");
  style.id = "ltx23-guide-styles";
  style.textContent = `
    .ltx23-guide-root { font: 12px Arial, sans-serif; color: #ddd; width: 100%; }
    .ltx23-guide-summary { padding: 6px 8px; border: 1px solid #444; background: #202020; border-radius: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ltx23-guide-toolbar { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px; }
    .ltx23-guide-toolbar button, .ltx23-guide-row button { background: #333; color: #ddd; border: 1px solid #555; border-radius: 4px; padding: 3px 6px; cursor: pointer; }
    .ltx23-guide-toolbar button:hover, .ltx23-guide-row button:hover { background: #444; }
    .ltx23-guide-list { margin-top: 6px; max-height: 130px; overflow: auto; border: 1px solid #333; border-radius: 4px; }
    .ltx23-guide-row { display: grid; grid-template-columns: 18px 1fr 54px 48px 32px 42px 46px; gap: 4px; align-items: center; padding: 4px; border-bottom: 1px solid #2d2d2d; }
    .ltx23-guide-row:last-child { border-bottom: 0; }
    .ltx23-guide-row input, .ltx23-guide-row select { min-width: 0; background: #181818; color: #ddd; border: 1px solid #444; border-radius: 3px; padding: 2px 3px; }
    .ltx23-guide-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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

function hideWidget(widget) {
  if (!widget) return;
  widget.type = "hidden";
  widget.draw = () => {};
  widget.computeSize = () => [0, -4];
}

function guideWidgetHeight(node) {
  const rowCount = readGuides(node).length;
  const rowHeight = 30;
  const visibleRows = Math.min(rowCount, 5);
  const listHeight = visibleRows > 0 ? visibleRows * rowHeight + 2 : 0;
  return 112 + listHeight;
}

function updateNodeHeight(node) {
  if (!node?._ltx23) return;
  const guides = readGuides(node);
  const rowCount = guides.length;
  const list = node._ltx23.list;
  if (list) {
    if (rowCount === 0) {
      list.style.display = "none";
      list.style.height = "0px";
    } else {
      const height = Math.min(rowCount, 5) * 30 + 2;
      list.style.display = "";
      list.style.height = `${height}px`;
      list.style.maxHeight = `${height}px`;
    }
  }
  if (node._ltx23.container) {
    node._ltx23.container.style.height = `${guideWidgetHeight(node)}px`;
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
  if (node._ltx23?.summary) node._ltx23.summary.textContent = timelineText(node);
  node.title = "LTX 2.3 Multi Image Latent Guide";
}

async function fetchJson(url, options) {
  const response = await api.fetchApi(url, options);
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || response.statusText);
  return data;
}

function closeDialog() {
  document.querySelector(".ltx23-guide-dialog")?.remove();
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
    <div class="ltx23-guide-dialog-row"><label>Folder</label><select class="folder"></select></div>
    <div class="ltx23-guide-dialog-row"><label>Image</label><select class="image"></select></div>
    <div class="ltx23-guide-dialog-row"><label>Position</label><input class="position" type="number" step="0.01" value="0"></div>
    <div class="ltx23-guide-dialog-row"><label>Strength</label><input class="strength" type="number" min="0" max="1" step="0.01" value="1"></div>
    <div class="ltx23-guide-dialog-row"><label>Label</label><input class="label" type="text"></div>`;
  const folderSelect = body.querySelector(".folder");
  const imageSelect = body.querySelector(".image");
  let availableImages = [];
  const folders = (await fetchJson("/ltx23_guides/folders")).folders;
  folderSelect.innerHTML = folders.map((folder) => `<option value="${folder.alias}">${folder.alias}${folder.exists ? "" : " (missing)"}</option>`).join("");
  async function loadImages() {
    const data = await fetchJson(`/ltx23_guides/images?alias=${encodeURIComponent(folderSelect.value)}`);
    availableImages = data.images;
    imageSelect.innerHTML = availableImages.map((image) => `<option value="${image.filename}">${image.filename}</option>`).join("");
  }
  folderSelect.addEventListener("change", loadImages);
  await loadImages();
  showDialog("Add Guide Image", body, async () => {
    const guide = {
      folder_alias: folderSelect.value,
      filename: imageSelect.value,
      position: Number(body.querySelector(".position").value || 0),
      calculated_frame: 0,
      strength: Number(body.querySelector(".strength").value || 1),
      label: body.querySelector(".label").value || "",
      enabled: true,
    };
    const selected = availableImages.find((image) => image.filename === guide.filename);
    if (selected) {
      guide.width = selected.width || 0;
      guide.height = selected.height || 0;
    }
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
      <button class="up" title="Move up">Up</button>
      <button class="down" title="Move down">Down</button>
      <button class="remove" title="Remove">X</button>`;
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

  container.addEventListener("mouseenter", async () => {
    const guides = readGuides(node).filter((guide) => guide.enabled !== false);
    panel.innerHTML = "";
    for (const guide of guides) {
      const targetRatio = Number(getWidgetValue(node, "width", 768)) / Number(getWidgetValue(node, "height", 512));
      const guideRatio = guide.width && guide.height ? guide.width / guide.height : targetRatio;
      const ratioWarning = Math.abs(targetRatio - guideRatio) > 0.02;
      const item = document.createElement("div");
      item.className = "ltx23-guide-preview-item";
      const thumbUrl = `/ltx23_guides/thumb?alias=${encodeURIComponent(guide.folder_alias)}&filename=${encodeURIComponent(guide.filename)}`;
      item.innerHTML = `
        <img src="${thumbUrl}" alt="">
        <div>
          <div>${guide.filename}</div>
          <div class="ltx23-guide-muted">${guide.folder_alias}</div>
          <div>${guide.position}${getWidgetValue(node, "timing_mode", "frame") === "seconds" ? "s" : "f"} -> ${calcFrame(node, guide)}f</div>
          <div>strength ${guide.strength ?? 1}</div>
          <div>${guide.enabled === false ? "disabled" : "enabled"}</div>
          ${ratioWarning ? `<div class="ltx23-guide-warning">aspect ratio differs</div>` : ""}
        </div>`;
      panel.appendChild(item);
    }
    if (!guides.length) panel.innerHTML = `<div class="ltx23-guide-muted">No enabled guides</div>`;
    panel.classList.add("visible");
  });
  container.addEventListener("mousemove", (event) => {
    panel.style.left = `${Math.min(window.innerWidth - 540, event.clientX + 14)}px`;
    panel.style.top = `${Math.min(window.innerHeight - 400, event.clientY + 14)}px`;
  });
  container.addEventListener("mouseleave", () => panel.classList.remove("visible"));

  const onRemoved = node.onRemoved;
  node.onRemoved = function () {
    panel.remove();
    onRemoved?.apply(this, arguments);
  };
}

function setupNode(node) {
  injectStyles();
  node.properties = node.properties || {};
  readGuides(node);

  const guidesWidget = getWidget(node, "guides_json");
  if (guidesWidget) {
    hideWidget(guidesWidget);
    guidesWidget.serializeValue = () => guidesWidget.value || "{\"version\":1,\"guides\":[]}";
  }

  const container = document.createElement("div");
  container.className = "ltx23-guide-root";
  container.innerHTML = `
    <div class="ltx23-guide-summary"></div>
    <div class="ltx23-guide-toolbar">
      <button data-action="add">Add</button>
      <button data-action="folder-add">Add Folder</button>
      <button data-action="folder-remove">Remove Folder</button>
      <button data-action="refresh">Refresh</button>
      <button data-action="save">Save Set</button>
      <button data-action="load">Load Set</button>
    </div>
    <div class="ltx23-guide-list"></div>`;
  const guideWidget = node.addDOMWidget("guide_manager", "div", container, { serialize: false });
  guideWidget.computeSize = () => [Math.max((node.size?.[0] || 390) - 20, 360), guideWidgetHeight(node)];
  guideWidget.serialize = false;
  node._ltx23 = {
    container,
    widget: guideWidget,
    summary: container.querySelector(".ltx23-guide-summary"),
    list: container.querySelector(".ltx23-guide-list"),
  };
  setupPreview(node, container);

  container.addEventListener("click", async (event) => {
    const action = event.target?.dataset?.action;
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
    if (info?.properties?.ltx23_guides) this.properties.ltx23_guides = info.properties.ltx23_guides;
    renderRows(this);
    setGuidesJson(this);
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
