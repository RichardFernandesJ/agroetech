import type { TalentState } from "@/services/talent-service";

import { escapeHtml } from "./talent-sidebar";

export interface PresetBarHandlers {
  onActivate: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string) => void;
  onDelete: (id: string) => void;
  onReset: () => void;
}

/** Faixa inferior: presets (builds salvas) e redefinição. Tudo por clique. */
export class TalentPresetsBar {
  constructor(
    private readonly root: HTMLElement,
    private readonly handlers: PresetBarHandlers,
  ) {
    this.root.addEventListener("click", this.handleClick);
  }

  render(state: TalentState, busy: boolean): void {
    const cooldown = this.cooldownText(state);
    const chips = state.presets
      .map((preset) => {
        const actions = `
          <button type="button" class="preset-icon" data-action="rename" data-id="${preset.id}" title="Renomear" aria-label="Renomear ${escapeHtml(preset.name)}">✎</button>
          ${
            preset.is_active
              ? ""
              : `<button type="button" class="preset-icon" data-action="delete" data-id="${preset.id}" title="Excluir" aria-label="Excluir ${escapeHtml(preset.name)}">✕</button>`
          }`;
        const blocked = busy || state.build_locked || (!preset.is_active && cooldown !== "");
        return `
          <div class="preset-chip ${preset.is_active ? "active" : ""}">
            <button type="button" class="preset-main" data-action="activate" data-id="${preset.id}"
              ${blocked ? "disabled" : ""} title="${preset.is_active ? "Build ativa" : cooldown || "Ativar esta build"}">
              <span class="preset-slot">${preset.slot}</span>
              <span class="preset-name">${escapeHtml(preset.name)}</span>
              <span class="preset-points">${preset.points_spent} pt</span>
            </button>
            ${actions}
          </div>`;
      })
      .join("");

    const canCreate = state.presets.length < state.preset_slots;
    const nextUnlock = (Math.floor(state.level / 10) + 1) * 10;
    const slot = canCreate
      ? `<button type="button" class="preset-add" data-action="create" ${busy ? "disabled" : ""}>＋ Nova build</button>`
      : state.preset_slots < 5
        ? `<span class="preset-locked" title="Mais espaços de build em níveis múltiplos de 10">🔒 Nível ${nextUnlock}</span>`
        : "";

    const resetLabel = state.reset_is_free ? "Redefinir (grátis)" : `Redefinir (${state.reset_cost} AGC)`;
    this.root.innerHTML = `
      <div class="preset-list">${chips}${slot}</div>
      <div class="preset-tools">
        ${cooldown ? `<span class="preset-cooldown">${escapeHtml(cooldown)}</span>` : ""}
        <button type="button" class="btn-reset-talents" data-action="reset" ${busy || state.build_locked ? "disabled" : ""}>${resetLabel}</button>
      </div>`;
  }

  private cooldownText(state: TalentState): string {
    if (!state.switch_available_at) {
      return "";
    }
    const remainingMs = new Date(state.switch_available_at).getTime() - Date.now();
    if (remainingMs <= 0) {
      return "";
    }
    const minutes = Math.ceil(remainingMs / 60_000);
    return `Troca de build disponível em ${minutes} min`;
  }

  private readonly handleClick = (event: Event): void => {
    const target = (event.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!target || (target as HTMLButtonElement).disabled) {
      return;
    }
    const id = target.dataset.id ?? "";
    switch (target.dataset.action) {
      case "activate":
        this.handlers.onActivate(id);
        break;
      case "create":
        this.handlers.onCreate();
        break;
      case "rename":
        this.handlers.onRename(id);
        break;
      case "delete":
        this.handlers.onDelete(id);
        break;
      case "reset":
        this.handlers.onReset();
        break;
    }
  };
}
