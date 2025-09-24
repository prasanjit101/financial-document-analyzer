import { create } from "zustand";
import { apiLogin, apiMe, apiRegister } from "./api";
import { type AuthTokenResponse, type UserMe } from "./types";

type AuthState = {
  token: string | null;
  user: UserMe | null;
  isLoading: boolean;
  error: string | null;
  register: (input: { username: string; password: string; full_name?: string | null }) => Promise<void>;
  login: (input: { username: string; password: string }) => Promise<void>;
  refreshMe: () => Promise<void>;
  logout: () => void;
  hydrate: () => void;
};

const TOKEN_KEY = "auth.token";

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  isLoading: false,
  error: null,

  hydrate: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) set({ token });
  },

  register: async (input) => {
    set({ isLoading: true, error: null });
    try {
      await apiRegister({
        username: input.username,
        password: input.password,
        full_name: input.full_name ?? undefined,
      });
      // After registration, perform login to obtain token
      const tokenRes: AuthTokenResponse = await apiLogin({ username: input.username, password: input.password });
      localStorage.setItem(TOKEN_KEY, tokenRes.access_token);
      set({ token: tokenRes.access_token });
      const me = await apiMe(tokenRes.access_token);
      set({ user: me });
    } catch (e: any) {
      set({ error: e?.message || "Registration failed" });
      throw e;
    } finally {
      set({ isLoading: false });
    }
  },

  login: async (input) => {
    set({ isLoading: true, error: null });
    try {
      const tokenRes = await apiLogin({ username: input.username, password: input.password });
      localStorage.setItem(TOKEN_KEY, tokenRes.access_token);
      set({ token: tokenRes.access_token });
      const me = await apiMe(tokenRes.access_token);
      set({ user: me });
    } catch (e: any) {
      set({ error: e?.message || "Login failed" });
      throw e;
    } finally {
      set({ isLoading: false });
    }
  },

  refreshMe: async () => {
    const token = get().token || localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    set({ isLoading: true });
    try {
      const me = await apiMe(token);
      set({ user: me, token });
    } catch {
      // Token invalid, clear
      localStorage.removeItem(TOKEN_KEY);
      set({ token: null, user: null });
    } finally {
      set({ isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ token: null, user: null });
  },
}));


