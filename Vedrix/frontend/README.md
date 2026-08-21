# 🎨 Autergo Frontend

The frontend for Autergo is a modern, high-performance React application built with **React 19**, **Vite**, and **Tailwind CSS v4**. It features a glassy, dark-themed interface designed for a professional interview experience.

## 🚀 Key Features

- **Real-time Interview Room**: WebSocket-powered chat with streaming AI responses.
- **Adaptive UI**: Responsive dashboard for both candidates and HR.
- **Interactive Coding Sandbox**: Integrated **Monaco Editor** for technical tasks.
- **Visual Analytics**: Performance radar charts and skill breakdown via **Recharts**.
- **Smooth Animations**: Motion components powered by **Framer Motion**.

## 🛠️ Tech Stack

- **Framework**: React 19 + TypeScript
- **State Management**: **Zustand** (Global state) + **React Query** (Server state)
- **Styling**: Tailwind CSS v4 + Framer Motion
- **Icons**: Lucide-React
- **Testing**: Vitest + React Testing Library

## 📂 Project Structure

- `src/components/`: Reusable UI primitives (Buttons, Modals, Cards).
- `src/pages/`: Main application views:
  - `LandingPage`: Product overview.
  - `InterviewRoom`: The core AI interview interface.
  - `Dashboard`: Candidate performance tracking.
  - `HRDashboard`: Recruiter view for drive management.
- `src/hooks/`: Custom hooks for Auth, Media (Microphone), and WebSockets.
- `src/store/`: Zustand state definitions.
- `src/services/`: API client and WebSocket handlers.

## 🚦 Getting Started

### Prerequisites
- Node.js 20+
- A running backend instance (see `Autergo/backend/README.md`)

### Installation
```bash
npm install
```

### Development
```bash
npm run dev
```

### Testing
```bash
npm test
```

## 🎨 Design Tokens

- **Primary Color**: Purple (`#7C3AED`)
- **Background**: Slate Dark (`#020617`)
- **Glassmorphism**: 10% opacity white with `backdrop-blur-xl`
