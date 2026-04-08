import { create } from 'zustand';
import api from '../api/client';

export const useTicketStore = create((set, get) => ({
  tickets: [],
  activeTicket: null,
  messages: [],
  orders: [],
  loading: false,

  fetchTickets: async () => {
    set({ loading: true });
    try {
      const { data } = await api.get('/tickets/');
      set({ tickets: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchTicket: async (id) => {
    set({ loading: true });
    try {
      const { data } = await api.get(`/tickets/${id}`);
      set({ activeTicket: data.ticket, messages: data.messages, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchOrders: async () => {
    try {
      const { data } = await api.get('/orders/');
      set({ orders: data });
    } catch {
      set({ orders: [] });
    }
  },

  createTicket: async (subject, orderId = null) => {
    const payload = { subject };
    if (orderId) payload.order_id = orderId;
    const { data } = await api.post('/tickets/', payload);
    await get().fetchTickets();
    return data;
  },

  sendMessage: async (ticketId, content) => {
    const { data } = await api.post('/chat/send', { ticket_id: ticketId, content });
    return data;
  },

  addMessage: (msg) => {
    set((state) => ({ messages: [...state.messages, msg] }));
  },

  updateTicketStatus: (ticketId, status, resolutionPath) => {
    set((state) => ({
      tickets: state.tickets.map((t) =>
        t.id === ticketId ? { ...t, status, resolution_type: resolutionPath } : t
      ),
      activeTicket:
        state.activeTicket?.id === ticketId
          ? { ...state.activeTicket, status, resolution_type: resolutionPath }
          : state.activeTicket,
    }));
  },
}));
