# 🛸 Orion Frontend

> React 19 + Vite 8 SPA powering Orion's four role-based dashboards with real-time Socket.IO integration.

## Overview

The Orion frontend is a single-page application that provides four distinct portals based on user role:

| Portal | Route | Role | Description |
|--------|-------|------|-------------|
| **Customer Chat** | `/chat` | `customer` | Support ticket creation, AI-powered real-time chat, order linking |
| **Agent Dashboard** | `/agent` | `agent` | Escalated ticket handling, AI briefing docs, manual messaging |
| **Manager Portal** | `/manager` | `manager` | Approval queue, KPI dashboard, action review |
| **Admin Panel** | `/admin` | `admin` | User management, system stats, full audit trail |

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| **React 19** | UI framework with modern features |
| **Vite 8** | Dev server with HMR, fast builds |
| **Zustand 5** | Lightweight state management |
| **React Router 7** | Client-side routing with role-based guards |
| **Axios** | HTTP client with JWT interceptor |
| **Socket.IO Client 4** | Real-time ticket updates and AI thinking indicators |
| **React Hot Toast** | Notification system |
| **Lucide React** | Icon library |
| **Recharts 3** | KPI chart visualization |

## Architecture

```
src/
├── api/
│   └── client.js          # Axios instance, JWT auth interceptor, 401 redirect
├── store/
│   ├── authStore.js        # Zustand: user, token, login(), logout()
│   └── ticketStore.js      # Zustand: tickets, messages, orders, CRUD actions
├── pages/
│   ├── Login.jsx           # Auth form with demo account quick-select
│   ├── Chat.jsx            # Customer: ticket list + real-time AI chat
│   ├── AgentDashboard.jsx  # Agent: escalated tickets + manual reply + resolve
│   ├── ManagerPortal.jsx   # Manager: approval queue + KPI stats
│   └── AdminPanel.jsx      # Admin: users, stats, audit log
├── App.jsx                 # BrowserRouter, ProtectedRoute, RoleRedirect
├── main.jsx                # React DOM entry point
├── index.css               # Complete design system (670 lines)
└── App.css                 # App-level overrides
```

## Setup

```bash
# Install dependencies
npm install

# Start dev server (default: http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment

The frontend connects to the backend at `http://localhost:8000` (hardcoded in `api/client.js`). To change:

```javascript
// src/api/client.js
const api = axios.create({
  baseURL: 'http://localhost:8000',  // ← Change this
});
```

## Design System

The CSS design system (`index.css`) provides:

- **Dark mode** color palette with semantic tokens
- **Inter + JetBrains Mono** typography
- **Glassmorphism** effects
- **Gradient text** for branding
- **Badge system** for status, priority, and roles
- **Stat cards** with accent-colored top borders
- **Chat UI** with AI/user message bubbles
- **Typing indicators** with animated dots
- **Modal system** with backdrop blur
- **Custom scrollbar** styling
- **Responsive breakpoints** (mobile sidebar collapse)
- **Animation library** (fadeIn, slideRight, scaleIn)

## Real-Time Features

The frontend establishes a Socket.IO connection to `ws://localhost:8000` and listens for:

| Event | Handler |
|-------|---------|
| `agent_thinking` | Shows thinking indicator with step info |
| `ticket_update` | Updates ticket status, adds AI reply to chat, refreshes ticket |

## Authentication Flow

1. User submits credentials → `POST /auth/login`
2. JWT token + user object stored in `localStorage`
3. Axios interceptor attaches `Authorization: Bearer <token>` to all requests
4. On 401 response → token cleared, redirect to `/login`
5. `ProtectedRoute` component checks role permissions on route access
6. `RoleRedirect` routes `/` to the appropriate dashboard based on user role
