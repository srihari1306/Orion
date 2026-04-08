import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: JSON.parse(localStorage.getItem('orion_user') || 'null'),
  token: localStorage.getItem('orion_token') || null,

  login: (user, token) => {
    localStorage.setItem('orion_user', JSON.stringify(user));
    localStorage.setItem('orion_token', token);
    set({ user, token });
  },

  logout: () => {
    localStorage.removeItem('orion_user');
    localStorage.removeItem('orion_token');
    set({ user: null, token: null });
  },
}));
