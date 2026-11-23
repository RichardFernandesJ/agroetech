import { authService, type RegisterPayload, type User } from "@/services/auth-service";

const TOKEN_KEY = "agroetech.access_token";

/**
 * Sessão do jogador.
 *
 * O token fica em `sessionStorage`: some ao fechar a aba e não é compartilhado
 * entre abas. Para produção, o próximo passo é refresh token em cookie
 * HttpOnly; o cliente nunca deve persistir senha.
 */
class SessionStore {
  private token: string | null = null;
  private user: User | null = null;

  constructor() {
    try {
      this.token = sessionStorage.getItem(TOKEN_KEY);
    } catch {
      this.token = null;
    }
  }

  get accessToken(): string | null {
    return this.token;
  }

  get currentUser(): User | null {
    return this.user;
  }

  async restore(): Promise<boolean> {
    if (!this.token) {
      return false;
    }
    try {
      this.user = await authService.me(this.token);
      return true;
    } catch {
      this.clear();
      return false;
    }
  }

  async signIn(login: string, password: string): Promise<User> {
    const response = await authService.login(login, password);
    this.setToken(response.access_token);
    this.user = await authService.me(response.access_token);
    return this.user;
  }

  async signUp(payload: RegisterPayload): Promise<User> {
    await authService.register(payload);
    return this.signIn(payload.email, payload.password);
  }

  clear(): void {
    this.token = null;
    this.user = null;
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      // sessionStorage pode estar indisponível em modo privado restrito.
    }
  }

  private setToken(token: string): void {
    this.token = token;
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      // Mantém o token apenas em memória se o storage falhar.
    }
  }
}

export const session = new SessionStore();
