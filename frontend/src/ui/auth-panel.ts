import { ApiError } from "@/services/api-client";
import type { User } from "@/services/auth-service";
import { session } from "@/state/session";

type AuthMode = "login" | "register";

interface AuthPanelOptions {
  onAuthenticated: (user: User) => void;
}

/**
 * Painel DOM de entrada. Formulários HTML são mais acessíveis e confortáveis
 * que inputs desenhados no canvas; o Phaser continua responsável pelo mundo.
 */
export class AuthPanel {
  private readonly root: HTMLDivElement;
  private mode: AuthMode = "login";
  private busy = false;

  constructor(private readonly options: AuthPanelOptions) {
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
    const isLogin = this.mode === "login";
    this.root.innerHTML = `
      <section class="panel" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <p class="eyebrow">Agro &amp; Tech</p>
        <h2 id="auth-title">${isLogin ? "Entrar na fazenda" : "Criar sua conta"}</h2>
        <p class="panel-subtitle">
          ${isLogin ? "Continue de onde parou e cuide da sua produção." : "Comece com uma fazenda e um kit de sementes."}
        </p>

        <div class="tabs" role="tablist" aria-label="Entrar ou criar conta">
          <button type="button" class="tab ${isLogin ? "active" : ""}" data-mode="login" role="tab" aria-selected="${isLogin}">Entrar</button>
          <button type="button" class="tab ${isLogin ? "" : "active"}" data-mode="register" role="tab" aria-selected="${!isLogin}">Criar conta</button>
        </div>

        <form novalidate>
          ${
            isLogin
              ? `
                <label class="field">
                  <span>E-mail ou usuário</span>
                  <input name="login" type="text" autocomplete="username" required minlength="1" maxlength="255" placeholder="ana@agro.com.br" />
                </label>
              `
              : `
                <label class="field">
                  <span>E-mail</span>
                  <input name="email" type="email" autocomplete="email" required maxlength="255" placeholder="ana@agro.com.br" />
                </label>
                <label class="field">
                  <span>Nome de usuário</span>
                  <input name="username" type="text" autocomplete="username" required minlength="3" maxlength="30" placeholder="ana_fazendeira" />
                </label>
              `
          }
          <label class="field">
            <span>Senha</span>
            <input name="password" type="password" autocomplete="${isLogin ? "current-password" : "new-password"}" required minlength="${isLogin ? 1 : 8}" maxlength="128" placeholder="Mínimo de 8 caracteres" />
          </label>

          <p class="form-error" role="alert" hidden></p>
          <button class="primary-button" type="submit">${isLogin ? "Entrar" : "Criar conta e entrar"}</button>
        </form>

        <p class="panel-hint">${isLogin ? "Ainda não tem conta? Use a aba Criar conta." : "Sua primeira fazenda é criada automaticamente."}</p>
      </section>
    `;

    this.root.querySelectorAll<HTMLButtonElement>(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        const next = tab.dataset.mode;
        if (next === "login" || next === "register") {
          this.mode = next;
          this.render();
        }
      });
    });

    this.root.querySelector("form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.submit();
    });
  }

  private async submit(): Promise<void> {
    if (this.busy) {
      return;
    }

    const form = this.root.querySelector("form");
    if (!form) {
      return;
    }

    const password = this.inputValue(form, "password");
    const login = this.inputValue(form, "login");
    const email = this.inputValue(form, "email");
    const username = this.inputValue(form, "username");

    if (!password) {
      this.showError("Informe a senha.");
      return;
    }
    if (this.mode === "login" && !login) {
      this.showError("Informe o e-mail ou usuário.");
      return;
    }
    if (this.mode === "register" && (!email || !username)) {
      this.showError("Informe e-mail e nome de usuário.");
      return;
    }

    this.busy = true;
    this.setBusy(true);
    this.showError("");

    try {
      const user =
        this.mode === "login"
          ? await session.signIn(login, password)
          : await session.signUp({ email, username, password });
      this.options.onAuthenticated(user);
    } catch (error) {
      this.showError(
        error instanceof ApiError ? error.message : "Não foi possível entrar. Tente novamente.",
      );
    } finally {
      this.busy = false;
      this.setBusy(false);
    }
  }

  private inputValue(form: HTMLFormElement, name: string): string {
    const input = form.querySelector<HTMLInputElement>(`input[name="${name}"]`);
    return input?.value.trim() ?? "";
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
    button.textContent = busy
      ? "Aguarde..."
      : this.mode === "login"
        ? "Entrar"
        : "Criar conta e entrar";
  }
}
