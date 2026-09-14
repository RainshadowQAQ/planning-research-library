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
    });
  }
  async open(url, version, position = {}) {
    const token = ++this.token;
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
      if (token === this.token)
        this.onError("PDF 未能顯示，可使用「開啟原件」。");
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
    this.pendingDocument = null;
    ++this.token;
    this.ready = false;
    this.viewer.setDocument(null);
    this.link.setDocument(null);
    if (this.task) await this.task.destroy();
    this.task = null;
  }
}
