import type { TalentCatalog, TalentNode } from "@/services/talent-service";

import type { NodeStatus } from "./talent-rules";

const SVG_NS = "http://www.w3.org/2000/svg";

const BRANCH_ICONS: Record<string, string> = {
  agricultura: "🌾",
  comercio: "🪙",
  pecuaria: "🐄",
  industria: "⚙️",
  exploracao: "🧭",
  estrategia: "🛡️",
  hibrido: "⚖️",
};

const SECTOR_RADIUS = 900;
const MIN_VIEW_WIDTH = 260;
const MAX_VIEW_WIDTH = 2600;
const FIT_SIZE = 1700;
const DRAG_THRESHOLD = 5;

type Attrs = Record<string, string | number>;

function svg<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs: Attrs = {},
  className?: string,
): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    element.setAttribute(key, String(value));
  }
  if (className) {
    element.setAttribute("class", className);
  }
  return element;
}

export interface TalentMapOptions {
  catalog: TalentCatalog;
  onSelect: (nodeId: string | null) => void;
  onHover: (nodeId: string | null, anchor: DOMRect | null) => void;
}

interface Edge {
  from: string; // id do nó ou "root"
  to: string;
  element: SVGLineElement;
}

/**
 * Mapa interativo de talentos em SVG: pan por arrasto, zoom por roda/pinça e
 * botões. Só desenha e reporta cliques; quem decide os estados é o chamador.
 */
export class TalentMap {
  private readonly canvas: SVGSVGElement;
  private readonly nodeElements = new Map<string, SVGGElement>();
  private readonly edges: Edge[] = [];
  private readonly pointers = new Map<number, { x: number; y: number }>();
  private readonly resizeObserver: ResizeObserver;
  private view = { x: 0, y: 0, w: FIT_SIZE, h: FIT_SIZE };
  private dragMoved = false;
  private dragTravel = 0;
  private lastPinchDistance = 0;
  private selectedId: string | null = null;
  // Enquanto o jogador não mexe na câmera, redimensionar reenquadra o mapa.
  private interacted = false;

  constructor(
    private readonly container: HTMLElement,
    private readonly options: TalentMapOptions,
  ) {
    this.canvas = svg("svg", { role: "group", "aria-label": "Mapa de talentos" }, "talent-canvas");
    this.container.append(this.canvas);

    this.drawSectors();
    this.drawEdges();
    this.drawRoot();
    this.drawNodes();

    this.canvas.addEventListener("wheel", this.handleWheel, { passive: false });
    this.canvas.addEventListener("pointerdown", this.handlePointerDown);
    this.canvas.addEventListener("click", this.handleBackgroundClick);

    this.fit();
    this.resizeObserver = new ResizeObserver(() => {
      if (this.interacted) {
        this.applyView();
      } else {
        this.fit();
      }
    });
    this.resizeObserver.observe(this.container);
  }

  destroy(): void {
    this.resizeObserver.disconnect();
    window.removeEventListener("pointermove", this.handlePointerMove);
    window.removeEventListener("pointerup", this.handlePointerUp);
    window.removeEventListener("pointercancel", this.handlePointerUp);
    this.canvas.remove();
  }

  // ------------------------------------------------------------- desenho
  private get center(): { x: number; y: number } {
    return { x: this.options.catalog.center_x, y: this.options.catalog.center_y };
  }

  private drawSectors(): void {
    const { x: cx, y: cy } = this.center;
    const layer = svg("g", {}, "talent-sectors");
    for (const branch of this.options.catalog.branches) {
      const toRad = (deg: number) => (deg * Math.PI) / 180;
      const start = toRad(branch.angle - 30);
      const end = toRad(branch.angle + 30);
      const path = svg("path", {
        d: `M ${cx} ${cy} L ${cx + SECTOR_RADIUS * Math.cos(start)} ${cy + SECTOR_RADIUS * Math.sin(start)} A ${SECTOR_RADIUS} ${SECTOR_RADIUS} 0 0 1 ${cx + SECTOR_RADIUS * Math.cos(end)} ${cy + SECTOR_RADIUS * Math.sin(end)} Z`,
      }, `talent-sector branch-${branch.id}${branch.available ? "" : " soon"}`);
      layer.append(path);

      const mid = toRad(branch.angle);
      const label = svg("text", {
        x: cx + (SECTOR_RADIUS + 10) * Math.cos(mid),
        y: cy + (SECTOR_RADIUS + 10) * Math.sin(mid),
        "text-anchor": "middle",
      }, `talent-sector-label branch-${branch.id}`);
      label.textContent = branch.available ? branch.name : `${branch.name} · em breve`;
      layer.append(label);
    }
    this.canvas.append(layer);
  }

  private drawEdges(): void {
    const layer = svg("g", {}, "talent-edges");
    const { x: cx, y: cy } = this.center;
    const byId = new Map(this.options.catalog.nodes.map((node) => [node.id, node]));

    for (const node of this.options.catalog.nodes) {
      const parents = [...node.requires, ...node.requires_any];
      const sources = parents.length > 0 ? parents : ["root"];
      for (const parentId of sources) {
        const parent = byId.get(parentId);
        const element = svg("line", {
          x1: parent ? parent.x : cx,
          y1: parent ? parent.y : cy,
          x2: node.x,
          y2: node.y,
        }, `talent-edge${node.requires_any.includes(parentId) ? " alt" : ""}`);
        layer.append(element);
        this.edges.push({ from: parentId, to: node.id, element });
      }
    }
    this.canvas.append(layer);
  }

  private drawRoot(): void {
    const { x, y } = this.center;
    const group = svg("g", {}, "talent-root");
    group.append(svg("circle", { cx: x, cy: y, r: 38 }, "talent-root-ring"));
    const icon = svg("text", { x, y: y + 11, "text-anchor": "middle" }, "talent-root-icon");
    icon.textContent = "🏡";
    group.append(icon);
    this.canvas.append(group);
  }

  private drawNodes(): void {
    const layer = svg("g", {}, "talent-nodes");
    for (const node of this.options.catalog.nodes) {
      layer.append(this.createNode(node));
    }
    this.canvas.append(layer);
  }

  private createNode(node: TalentNode): SVGGElement {
    const radius = 22 + node.tier * 4;
    const group = svg("g", {
      transform: `translate(${node.x} ${node.y})`,
      tabindex: 0,
      role: "button",
      "aria-label": `${node.name} (${node.tier_name}, custo ${node.cost})`,
      "data-id": node.id,
    }, `talent-node branch-${node.branch} tier-${node.tier} status-locked`);

    group.append(svg("circle", { r: radius + 5 }, "talent-node-halo"));
    group.append(svg("circle", { r: radius }, "talent-node-body"));
    const icon = svg("text", { y: 8, "text-anchor": "middle" }, "talent-node-icon");
    icon.textContent = BRANCH_ICONS[node.branch] ?? "✦";
    group.append(icon);

    const badge = svg("g", { transform: `translate(${radius * 0.78} ${radius * 0.78})` }, "talent-node-cost");
    badge.append(svg("circle", { r: 11 }));
    const costText = svg("text", { y: 4.5, "text-anchor": "middle" });
    costText.textContent = String(node.cost);
    badge.append(costText);
    group.append(badge);

    group.addEventListener("click", (event) => {
      event.stopPropagation();
      if (!this.dragMoved) {
        this.options.onSelect(node.id);
      }
    });
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        this.options.onSelect(node.id);
      }
    });
    group.addEventListener("pointerenter", () =>
      this.options.onHover(node.id, group.getBoundingClientRect()),
    );
    group.addEventListener("pointerleave", () => this.options.onHover(null, null));

    this.nodeElements.set(node.id, group);
    return group;
  }

  // -------------------------------------------------------------- estado
  setStatuses(statuses: ReadonlyMap<string, NodeStatus>): void {
    for (const [id, element] of this.nodeElements) {
      const status = statuses.get(id) ?? "locked";
      element.setAttribute(
        "class",
        element.getAttribute("class")!.replace(/status-\w+/, `status-${status}`),
      );
    }
    for (const edge of this.edges) {
      const fromOwned = edge.from === "root" || statuses.get(edge.from) === "owned";
      const toStatus = statuses.get(edge.to);
      const state =
        fromOwned && toStatus === "owned"
          ? "lit"
          : fromOwned && toStatus === "available"
            ? "open"
            : "dim";
      edge.element.setAttribute(
        "class",
        edge.element.getAttribute("class")!.replace(/ ?(lit|open|dim)/g, "") + ` ${state}`,
      );
    }
  }

  select(nodeId: string | null): void {
    if (this.selectedId) {
      this.nodeElements.get(this.selectedId)?.classList.remove("selected");
    }
    this.selectedId = nodeId;
    if (nodeId) {
      this.nodeElements.get(nodeId)?.classList.add("selected");
    }
  }

  /** Animação curta ao adquirir um talento. */
  flash(nodeId: string): void {
    const element = this.nodeElements.get(nodeId);
    if (!element) {
      return;
    }
    element.classList.add("just-acquired");
    window.setTimeout(() => element.classList.remove("just-acquired"), 1100);
  }

  // ------------------------------------------------------------- câmera
  zoomBy(factor: number): void {
    const rect = this.canvas.getBoundingClientRect();
    this.zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, factor);
  }

  /** Enquadra a região com talentos disponíveis (ignora os setores "em breve"). */
  fit(): void {
    this.interacted = false;
    const open = new Set(
      this.options.catalog.branches.filter((branch) => branch.available).map((b) => b.id),
    );
    const nodes = this.options.catalog.nodes.filter(
      (node) => open.has(node.branch) || node.branch === "hibrido",
    );
    const points = [this.center, ...nodes.map((node) => ({ x: node.x, y: node.y }))];
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    this.fitBounds(Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys), 110);
  }

  /** Enquadra o mapa inteiro, com todos os setores. */
  fitAll(): void {
    this.interacted = true;
    const c = this.center;
    this.fitBounds(c.x - FIT_SIZE / 2, c.y - FIT_SIZE / 2, c.x + FIT_SIZE / 2, c.y + FIT_SIZE / 2, 0);
  }

  private fitBounds(minX: number, minY: number, maxX: number, maxY: number, pad: number): void {
    const rect = this.canvas.getBoundingClientRect();
    const aspect = rect.width > 0 && rect.height > 0 ? rect.width / rect.height : 1;
    const needW = maxX - minX + pad * 2;
    const needH = maxY - minY + pad * 2;
    const w = needW / needH > aspect ? needW : needH * aspect;
    const h = w / aspect;
    this.view = { x: (minX + maxX) / 2 - w / 2, y: (minY + maxY) / 2 - h / 2, w, h };
    this.applyView();
  }

  private applyView(): void {
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      this.view.h = (this.view.w * rect.height) / rect.width;
    }
    const margin = 400;
    this.view.x = Math.min(
      Math.max(this.view.x, this.center.x - SECTOR_RADIUS - margin - this.view.w / 2),
      this.center.x + SECTOR_RADIUS + margin - this.view.w / 2,
    );
    this.view.y = Math.min(
      Math.max(this.view.y, this.center.y - SECTOR_RADIUS - margin - this.view.h / 2),
      this.center.y + SECTOR_RADIUS + margin - this.view.h / 2,
    );
    this.canvas.setAttribute(
      "viewBox",
      `${this.view.x.toFixed(1)} ${this.view.y.toFixed(1)} ${this.view.w.toFixed(1)} ${this.view.h.toFixed(1)}`,
    );
  }

  private zoomAt(clientX: number, clientY: number, factor: number): void {
    this.interacted = true;
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width === 0) {
      return;
    }
    const fx = (clientX - rect.left) / rect.width;
    const fy = (clientY - rect.top) / rect.height;
    const anchorX = this.view.x + fx * this.view.w;
    const anchorY = this.view.y + fy * this.view.h;

    const nextW = Math.min(MAX_VIEW_WIDTH, Math.max(MIN_VIEW_WIDTH, this.view.w * factor));
    const nextH = (nextW * rect.height) / rect.width;
    this.view = { x: anchorX - fx * nextW, y: anchorY - fy * nextH, w: nextW, h: nextH };
    this.applyView();
  }

  private panByPixels(dx: number, dy: number): void {
    this.interacted = true;
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width === 0) {
      return;
    }
    this.view.x -= (dx / rect.width) * this.view.w;
    this.view.y -= (dy / rect.height) * this.view.h;
    this.applyView();
  }

  // ------------------------------------------------------------ entradas
  private readonly handleWheel = (event: WheelEvent): void => {
    event.preventDefault();
    this.zoomAt(event.clientX, event.clientY, event.deltaY < 0 ? 0.88 : 1.14);
  };

  private readonly handlePointerDown = (event: PointerEvent): void => {
    this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (this.pointers.size === 1) {
      this.dragMoved = false;
      this.dragTravel = 0;
    }
    this.lastPinchDistance = this.pinchDistance();
    window.addEventListener("pointermove", this.handlePointerMove);
    window.addEventListener("pointerup", this.handlePointerUp);
    window.addEventListener("pointercancel", this.handlePointerUp);
  };

  private readonly handlePointerMove = (event: PointerEvent): void => {
    const previous = this.pointers.get(event.pointerId);
    if (!previous) {
      return;
    }
    const dx = event.clientX - previous.x;
    const dy = event.clientY - previous.y;
    this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

    if (this.pointers.size >= 2) {
      const distance = this.pinchDistance();
      if (this.lastPinchDistance > 0 && distance > 0) {
        const mid = this.pinchCenter();
        this.zoomAt(mid.x, mid.y, this.lastPinchDistance / distance);
      }
      this.lastPinchDistance = distance;
      this.dragMoved = true;
      return;
    }

    this.dragTravel += Math.abs(dx) + Math.abs(dy);
    if (this.dragTravel > DRAG_THRESHOLD) {
      this.dragMoved = true;
      this.options.onHover(null, null);
      this.panByPixels(dx, dy);
    }
  };

  private readonly handlePointerUp = (event: PointerEvent): void => {
    this.pointers.delete(event.pointerId);
    this.lastPinchDistance = this.pinchDistance();
    if (this.pointers.size === 0) {
      window.removeEventListener("pointermove", this.handlePointerMove);
      window.removeEventListener("pointerup", this.handlePointerUp);
      window.removeEventListener("pointercancel", this.handlePointerUp);
      // Mantém dragMoved até o `click` seguinte ser descartado.
      window.setTimeout(() => {
        this.dragMoved = false;
      }, 0);
    }
  };

  private readonly handleBackgroundClick = (): void => {
    if (!this.dragMoved) {
      this.options.onSelect(null);
    }
  };

  private pinchDistance(): number {
    const [a, b] = [...this.pointers.values()];
    return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0;
  }

  private pinchCenter(): { x: number; y: number } {
    const [a, b] = [...this.pointers.values()];
    return a && b ? { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 } : { x: 0, y: 0 };
  }
}
