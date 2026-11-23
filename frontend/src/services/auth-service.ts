import { apiClient } from "./api";

export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
}

export const authService = {
  register: (payload: RegisterPayload): Promise<User> =>
    apiClient.post<User>("/auth/register", payload),

  login: (login: string, password: string): Promise<TokenResponse> =>
    apiClient.post<TokenResponse>("/auth/login", { login, password }),

  me: (token: string): Promise<User> => apiClient.get<User>("/auth/me", { token }),
};
