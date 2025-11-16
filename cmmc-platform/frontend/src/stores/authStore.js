import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      accessToken: localStorage.getItem('access_token'),
      refreshToken: localStorage.getItem('refresh_token'),

      setTokens: (accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        if (refreshToken) {
          localStorage.setItem('refresh_token', refreshToken);
        }
        set({ accessToken, refreshToken });
      },

      setUser: (user) => set({ user }),

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, accessToken: null, refreshToken: null });
      },

      isAuthenticated: () => {
        const token = get().accessToken;
        if (!token) return false;

        try {
          // Decode JWT to check expiration
          const payload = JSON.parse(atob(token.split('.')[1]));
          return payload.exp * 1000 > Date.now();
        } catch {
          return false;
        }
      },

      getUserFromToken: () => {
        const token = get().accessToken;
        if (!token) return null;

        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          return {
            id: payload.sub,
            email: payload.email,
            role: payload.role,
            organizationId: payload.org_id,
          };
        } catch {
          return null;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
);

export default useAuthStore;
