import apiClient from "./client";
import type {
  LogoutRequest,
  Message,
  RefreshTokenRequest,
  Token,
  TokenWithRefresh,
  UserLoginRequest,
  UserMe,
  UserRegisterRequest,
} from "../types/api";

export const authApi = {
  async register(
    payload: UserRegisterRequest,
  ): Promise<TokenWithRefresh> {
    const { data } = await apiClient.post<TokenWithRefresh>(
      "/auth/register",
      payload,
    );

    return data;
  },

  async login(
    payload: UserLoginRequest,
  ): Promise<TokenWithRefresh> {
    const { data } = await apiClient.post<TokenWithRefresh>(
      "/auth/login",
      payload,
    );

    return data;
  },

  async refresh(
    payload: RefreshTokenRequest,
  ): Promise<Token> {
    const { data } = await apiClient.post<Token>(
      "/auth/refresh",
      payload,
    );

    return data;
  },

  async logout(
    payload: LogoutRequest,
  ): Promise<Message> {
    const { data } = await apiClient.post<Message>(
      "/auth/logout",
      payload,
    );

    return data;
  },

  async me(): Promise<UserMe> {
    const { data } = await apiClient.get<UserMe>("/auth/me");

    return data;
  },
};
