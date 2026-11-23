import { env } from "@/config/env";

import { ApiClient } from "./api-client";

/** Ponto único para os endpoints versionados em /api/v1. */
export const apiClient = new ApiClient(env.apiUrl);
