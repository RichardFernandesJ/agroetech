import { env } from "@/config/env";

import { ApiClient } from "./api-client";

export interface HealthResponse {
  status: string;
}

// O health check fica na raiz da API, fora de /api/v1.
const healthClient = new ApiClient("");

export const systemService = {
  health: (): Promise<HealthResponse> => healthClient.get<HealthResponse>(env.healthUrl),
};
