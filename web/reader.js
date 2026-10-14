import * as pdfjs from "/vendor/pdfjs/build/pdf.mjs";
globalThis.pdfjsLib = pdfjs;
const { PDFViewer, EventBus, PDFLinkService } =
  await import("/vendor/pdfjs/web/pdf_viewer.mjs");
pdfjs.GlobalWorkerOptions.workerSrc = "/vendor/pdfjs/build/pdf.worker.mjs";

export class Reader {
  constructor(container, onPosition, onReady, onError) {
    this.container = container;
    this.onPosition = onPosition;
    this.onReady = onReady;
    this.onError = onError;
    this.token = 0;
    this.ready = false;
    this.restoring = false;
    this.events = new EventBus();
    this.link = new PDFLinkService({ eventBus: this.events });
    this.viewer = new PDFViewer({
      container,
      viewer: container.querySelector(".pdfViewer"),
      eventBus: this.events,
      linkService: this.link,
      textLayerMode: 1,
      annotationMode: 0,
      annotationEditorMode: -1,
      enableScripting: false,
    });
    this.link.setViewer(this.viewer);
    this.events.on("updateviewarea", () => {
      if (this.ready && !this.restoring) this.onPosition(this.position());
    });
    this.events.on("pagesinit", () => {
      this.ready = true;
      this.restore(this.saved || {});
      this.onReady(this.doc.numPages);
      this.readyWaiters.splice(0).forEach((done) => done(this.version));
    });
    this.readyWaiters = [];
    this.evidence = null;
    // Zoom and rotation re-render the text layer; redraw from fresh geometry.
    this.events.on("textlayerrendered", ({ pageNumber }) => {
      if (this.evidence?.page === pageNumber) this.drawEvidence();
    });
  }
  whenReady(version, timeout = 15000) {
    if (this.ready && this.version === version) return Promise.resolve(true);
    return new Promise((resolve) => {
      const timer = setTimeout(() => resolve(false), timeout);
      this.readyWaiters.push((v) => {
        clearTimeout(timer);
        resolve(v === version);
      });
    });
  }
  textLayerFor(n, timeout = 8000) {
    const view = this.viewer.getPageView(n - 1);
    const done = () =>
      view?.textLayer?.div?.isConnected &&
      view.renderingState === 3 &&
      view.textLayer.div.childNodes.length;
    if (done()) return Promise.resolve(view.textLayer.div);
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        this.events.off("textlayerrendered", listener);
        resolve(done() ? view.textLayer.div : null);
      }, timeout);
      const listener = ({ pageNumber }) => {
        if (pageNumber !== n) return;
        clearTimeout(timer);
        this.events.off("textlayerrendered", listener);
        resolve(view.textLayer?.div || null);
      };
      this.events.on("textlayerrendered", listener);
    });
  }
  clearEvidence() {
    this.evidence = null;
    this.container
      .querySelectorAll(".evidence-highlight")
      .forEach((n) => n.remove());
  }
  // Text-layer geometry, never model or stored coordinates; null unless unique.
  locate(layer, excerpt) {
    const norm = (t) =>
      t
        .replace(/[‘’]/g, "'")
        .replace(/[“”]/g, '"')
        .toLowerCase();
    const map = [];
    let text = "";
    const walker = document.createTreeWalker(layer, NodeFilter.SHOW_TEXT);
    for (let node; (node = walker.nextNode()); )
      for (let i = 0; i < node.data.length; i++) {
        const ch = norm(node.data[i]);
        if (/\s/.test(ch)) continue;
        text += ch;
        map.push([node, i]);
      }
    if (!text) return { reason: "此頁沒有可讀文字層（可能是掃描頁），未繪製標示" };
    const needle = norm(excerpt).replace(/\s+/g, "");
    const at = text.indexOf(needle);
    if (at < 0) return { reason: "此頁未找到所引原文，未繪製標示" };
    if (text.indexOf(needle, at + 1) >= 0)
      return { reason: "所引原文在此頁出現多次，未繪製標示" };
    const range = document.createRange();
    const [startNode, startOffset] = map[at];
    const [endNode, endOffset] = map[at + needle.length - 1];
    range.setStart(startNode, startOffset);
    range.setEnd(endNode, endOffset + 1);
    return { range };
  }
  drawEvidence() {
    const e = this.evidence;
    this.container
      .querySelectorAll(".evidence-highlight")
      .forEach((n) => n.remove());
    const view = this.viewer.getPageView(e.page - 1);
    const layer = view?.textLayer?.div;
    if (!layer) return { ok: false, reason: "原文頁面未能顯示" };
    const found = this.locate(layer, e.excerpt);
    if (!found.range) return { ok: false, reason: found.reason };
    const div = view.div;
    const outer = div.getBoundingClientRect();
    const box = {
      left: outer.left + div.clientLeft,
      top: outer.top + div.clientTop,
      width: div.clientWidth,
      height: div.clientHeight,
    };
    const rects = [...found.range.getClientRects()].filter(
      (r) => r.width > 0 && r.height > 0,
    );
    for (const r of rects) {
      const mark = document.createElement("div");
      mark.className = "evidence-highlight";
      mark.style.left = ((r.left - box.left) / box.width) * 100 + "%";
      mark.style.top = ((r.top - box.top) / box.height) * 100 + "%";
      mark.style.width = (r.width / box.width) * 100 + "%";
      mark.style.height = (r.height / box.height) * 100 + "%";
      view.div.append(mark);
    }
    return { ok: true, rects: rects.length, top: rects[0] };
  }
  async jumpToEvidence(citation) {
    this.clearEvidence();
    if (!this.ready || this.version !== citation.source_sha256)
      return { ok: false, reason: "閱讀器未開啟所引文件版本" };
    const page = Number(citation.page);
    if (!Number.isInteger(page) || page < 1 || page > this.doc.numPages)
      return { ok: false, reason: "所引頁碼不在此文件內" };
    this.page(page);
    if (!citation.excerpt)
      return { ok: false, reason: `已跳到第 ${page} 頁；此來源只記錄頁碼，未繪製標示` };
    const token = this.token;
    const layer = await this.textLayerFor(page);
    if (token !== this.token) return { ok: false, reason: "已切換文件" };
    if (!layer) return { ok: false, reason: `已跳到第 ${page} 頁；文字層未能載入，未繪製標示` };
    this.evidence = { page, excerpt: citation.excerpt };
    const result = this.drawEvidence();
    if (!result.ok) {
      this.evidence = null;
      return { ok: false, reason: `已跳到第 ${page} 頁；${result.reason}` };
    }
    const mark = this.container.querySelector(".evidence-highlight");
    if (mark)
      this.container.scrollTop = Math.max(
        0,
        mark.getBoundingClientRect().top -
          this.container.getBoundingClientRect().top +
          this.container.scrollTop -
          this.container.clientHeight / 3,
      );
    return { ok: true };
  }
  async open(url, version, position = {}) {
    const token = ++this.token;
    this.clearEvidence();
    this.ready = false;
    this.pendingDocument = null;
    this.saved = position;
    this.version = version;
    this.viewer.setDocument(null);
    this.link.setDocument(null);
    if (this.task) await this.task.destroy();
    if (token !== this.token) return;
    this.task = pdfjs.getDocument({
      url,
      cMapUrl: "/vendor/pdfjs/cmaps/",
      cMapPacked: true,
      standardFontDataUrl: "/vendor/pdfjs/standard_fonts/",
      wasmUrl: "/vendor/pdfjs/wasm/",
      iccUrl: "/vendor/pdfjs/iccs/",
      isEvalSupported: false,
      enableXfa: false,
    });
    try {
      const doc = await this.task.promise;
      if (token !== this.token) return;
      this.doc = doc;
      this.pendingDocument = doc;
      this.attach();
    } catch (e) {
      if (token === this.token) {
        this.onError("PDF 未能顯示，可使用「開啟原件」。");
        this.readyWaiters.splice(0).forEach((done) => done(null));
      }
    }
  }
  attach() {
    if (!this.pendingDocument || !this.container.offsetParent) return;
    const doc = this.pendingDocument;
    this.pendingDocument = null;
    this.link.setDocument(doc);
    this.viewer.setDocument(doc);
  }
  position() {
    if (!this.ready || !this.container.offsetParent) return this.saved || {};
    const page = this.viewer.currentPageNumber;
    const div = this.viewer.getPageView(page - 1)?.div;
    const offset = div
      ? Math.max(
          0,
          Math.min(
            0.99,
            (this.container.scrollTop - div.offsetTop) / div.offsetHeight,
          ),
        )
      : 0;
    this.saved = {
      page,
      offset,
      zoom:
        this.viewer.currentScaleValue === "page-width"
          ? "page-width"
          : this.viewer.currentScale,
    };
    return this.saved;
  }
  restore(p) {
    this.saved = p;
    this.attach();
    if (!this.ready || !this.container.offsetParent) return;
    this.restoring = true;
    this.viewer.currentScaleValue =
      p.zoom === "page-width" || !p.zoom
        ? "page-width"
        : String(Math.max(0.25, Math.min(4, Number(p.zoom) || 1)));
    this.viewer.currentPageNumber = Math.max(
      1,
      Math.min(this.doc.numPages, Number(p.page) || 1),
    );
    this.viewer.scrollPageIntoView({
      pageNumber: this.viewer.currentPageNumber,
    });
    const div = this.viewer.getPageView(this.viewer.currentPageNumber - 1)?.div;
    if (div)
      this.container.scrollTop =
        div.offsetTop +
        Math.max(0, Math.min(0.99, Number(p.offset) || 0)) * div.offsetHeight;
    this.restoring = false;
    this.onPosition(this.position());
  }
  resize() {
    this.attach();
    if (this.ready && this.container.offsetParent)
      this.restore(this.position());
  }
  page(n) {
    if (this.ready) {
      this.viewer.currentPageNumber = Math.max(
        1,
        Math.min(this.doc.numPages, n),
      );
      this.viewer.scrollPageIntoView({
        pageNumber: this.viewer.currentPageNumber,
      });
    }
  }
  zoom(value) {
    if (this.ready) this.restore({ ...this.position(), zoom: value });
  }
  async clear() {
    this.clearEvidence();
    this.pendingDocument = null;
    ++this.token;
    this.ready = false;
    this.viewer.setDocument(null);
    this.link.setDocument(null);
    if (this.task) await this.task.destroy();
    this.task = null;
  }
}
