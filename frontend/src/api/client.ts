import axios, {
  AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";

import { tokenStorage } from "../lib/tokenStorage";
import type { Token } from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let refreshPromise: Promise<string | null> | null = null;

const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = tokenStorage.getRefreshToken();

  if (!refreshToken) {
    return null;
  }

  if (!refreshPromise) {
    refreshPromise = apiClient
      .post<Token>("/auth/refresh", {
        refresh_token: refreshToken,
      })
      .then(({ data }) => {
        tokenStorage.setTokens(data.access_token);
        return data.access_token;
      })
      .catch(() => {
        tokenStorage.clear();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
};

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const accessToken = tokenStorage.getAccessToken();

    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    return config;
  },
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest.url?.includes("/auth/refresh") ||
      originalRequest.headers?.["X-Trazio-Retry"] === "1"
    ) {
      return Promise.reject(error);
    }

    const newAccessToken = await refreshAccessToken();

    if (!newAccessToken) {
      return Promise.reject(error);
    }

    originalRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
    originalRequest.headers["X-Trazio-Retry"] = "1";

    return apiClient(originalRequest);
  },
);

export default apiClient;
