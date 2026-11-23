/**
 * Configuração de ambiente do cliente.
 *
 * Em desenvolvimento, as URLs relativas são encaminhadas pelo proxy do Vite
 * para o FastAPI. Em produção, o nginx faz o mesmo papel. Isso evita CORS e
 * mantém a mesma build para qualquer origem.
 */
const apiUrl = (import.meta.env.VITE_API_URL?.trim() || "/api/v1").replace(/\/$/, "");
const healthUrl = import.meta.env.VITE_HEALTH_URL?.trim() || "/health";

export const env = {
  apiUrl,
  healthUrl,
  gameTitle: import.meta.env.VITE_GAME_TITLE?.trim() || "Agro & Tech",
  isDevelopment: import.meta.env.DEV,
} as const;
