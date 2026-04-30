export interface UserRead {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  created_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserRead;
}
