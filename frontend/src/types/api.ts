export type UserStatus = string;

export interface UserPublic {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_verified: boolean;
  status: UserStatus;
  created_at: string;
}

export type UserMe = UserPublic;

export interface Token {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface TokenWithRefresh extends Token {
  refresh_token: string;
}

export interface Message {
  detail: string;
}

export interface ApiError {
  detail: string;
}

export interface UserRegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string | null;
}

export interface UserLoginRequest {
  email_or_username: string;
  password: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}
