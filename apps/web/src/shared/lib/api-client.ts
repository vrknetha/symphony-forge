import { appEnv } from "@/config/env";

interface ApiEnvelope<T> {
  data: T;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${appEnv.apiBaseUrl}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  const json = (await response.json()) as ApiEnvelope<T>;
  return json.data;
}

export const apiClient = {
  get: request,
};
