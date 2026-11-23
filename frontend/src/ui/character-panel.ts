import { ApiError } from "@/services/api-client";
import {
  characterService,
  type Character,
  type HairStyle,
  type SkinTone,
} from "@/services/character-service";
import { session } from "@/state/session";

interface CharacterPanelOptions {
  onCreated: (character: Character) => void;
}

const SKIN_TONES: Array<{ value: SkinTone; label: string }> = [
  { value: "light", label: "Clara" },
  { value: "medium", label: "Média" },
  { value: "dark", label: "Morena" },
  { value: "deep", label: "Negra" },
];

const HAIR_STYLES: Array<{ value: HairStyle; label: string }> = [
  { value: "short", label: "Curto" },
  { value: "long", label: "Longo" },
  { value: "bun", label: "Coque" },
  { value: "cap", label: "Chapéu" },
];

export class CharacterPanel {
  private readonly root: HTMLDivElement;
  private busy = false;

  constructor(private readonly options: CharacterPanelOptions) {
    this.root = document.createElement("div");
    this.root.className = "overlay";
    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);
    this.render();
  }

  destroy(): void {
    this.root.remove();
  }

  private render(): void {
    this.root.innerHTML = `
      <section class="panel" role="dialog" aria-modal="true" aria-labelledby="character-title">
        <p class="eyebrow">Primeiro acesso</p>
        <h2 id="character-title">Crie seu personagem</h2>
        <p class="panel-subtitle">
          Escolha um nome e a aparência. Sua primeira fazenda e o kit inicial de sementes
          serão criados automaticamente.
        </p>

        <form novalidate>
          <label class="field">
            <span>Nome do personagem</span>
            <input name="name" type="text" required minlength="3" maxlength="20" autocomplete="nickname" placeholder="Ana" />
          </label>

          <div class="field-row">
            <label class="field">
              <span>Tom de pele</span>
              <select name="skin_tone">
                ${SKIN_TONES.map((tone) => `<option value="${tone.value}">${tone.label}</option>`).join("")}
              </select>
            </label>

            <label class="field">
              <span>Cabelo</span>
              <select name="hair_style">
                ${HAIR_STYLES.map((style) => `<option value="${style.value}">${style.label}</option>`).join("")}
              </select>
            </label>
          </div>

          <label class="field field-color">
            <span>Cor da roupa</span>
            <input name="outfit_color" type="color" value="#3f7d4e" />
          </label>

          <p class="form-error" role="alert" hidden></p>
          <button class="primary-button" type="submit">Começar a cultivar</button>
        </form>

        <p class="panel-hint">Você poderá ajustar a aparência em uma etapa futura.</p>
      </section>
    `;

    this.root.querySelector("form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.submit();
    });
  }

  private async submit(): Promise<void> {
    if (this.busy) {
      return;
    }

    const token = session.accessToken;
    if (!token) {
      this.showError("Sua sessão expirou. Entre novamente.");
      return;
    }

    const form = this.root.querySelector("form");
    if (!form) {
      return;
    }

    const name = form.querySelector<HTMLInputElement>('input[name="name"]')?.value.trim() ?? "";
    const skinTone =
      form.querySelector<HTMLSelectElement>('select[name="skin_tone"]')?.value ?? "medium";
    const hairStyle =
      form.querySelector<HTMLSelectElement>('select[name="hair_style"]')?.value ?? "short";
    const outfitColor =
      form.querySelector<HTMLInputElement>('input[name="outfit_color"]')?.value ?? "#3f7d4e";

    if (name.length < 3) {
      this.showError("O nome precisa ter ao menos 3 caracteres.");
      return;
    }

    this.busy = true;
    this.setBusy(true);
    this.showError("");

    try {
      const character = await characterService.create(
        {
          name,
          appearance: {
            skin_tone: skinTone as SkinTone,
            hair_style: hairStyle as HairStyle,
            outfit_color: outfitColor,
          },
        },
        token,
      );
      this.options.onCreated(character);
    } catch (error) {
      this.showError(
        error instanceof ApiError
          ? error.message
          : "Não foi possível criar o personagem. Tente novamente.",
      );
    } finally {
      this.busy = false;
      this.setBusy(false);
    }
  }

  private showError(message: string): void {
    const element = this.root.querySelector<HTMLParagraphElement>(".form-error");
    if (!element) {
      return;
    }
    element.textContent = message;
    element.hidden = message.length === 0;
  }

  private setBusy(busy: boolean): void {
    const button = this.root.querySelector<HTMLButtonElement>(".primary-button");
    if (!button) {
      return;
    }
    button.disabled = busy;
    button.textContent = busy ? "Preparando a fazenda..." : "Começar a cultivar";
  }
}
