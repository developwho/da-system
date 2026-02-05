

# DA System - Frontend Implementation Plan

## Overview
A modern, ChatGPT-style data analysis SaaS with 4 core pages (Chat, Data, Models, Reports), real-time progress tracking, and a polished dark theme. Built with mock data initially, but architected for seamless backend integration.

---

## Design System

### Visual Style
- **Theme**: Dark mode inspired by ChatGPT/Claude
- **Colors**: Near-black background (#0D0D0D), subtle grays for cards, bright accent for actions
- **Typography**: Clean sans-serif, generous spacing
- **Components**: Minimal, rounded corners, subtle hover effects
- **Icons**: Lucide icons (already installed)

---

## Core Pages & Features

### 1. Chat Interface (`/`)
The heart of the application - a conversational AI interface for data analysis.

**Features:**
- Welcome screen with quick action cards (Upload, Sample Analysis, Docs)
- Message display with user/AI message styling
- File upload via drag-drop or attachment button
- Sticky input bar at bottom
- Live progress tracker showing 5-step analysis (Data Profiling → Problem Detection → Research → Training → Report)
- Interactive result cards (Data Profile, Model Results, Report Summary)
- Inline charts for feature importance and confusion matrices

### 2. Data Management (`/data`)
File library for uploaded datasets.

**Features:**
- Card/table view of all uploaded files
- File details: name, size, rows, columns, problem type, status
- Actions per file: Preview (modal with first 100 rows), Profile (stats modal), Use in Chat, Delete
- Upload button with drag-drop zone
- Search and filter by file type/status

### 3. Models Tracking (`/models`)
Monitor trained ML models and compare performance.

**Features:**
- Model cards with status badges (Training, Complete, Failed)
- Active training cards with live progress bar and metrics
- Completed model cards showing ROC-AUC, Accuracy, F1, etc.
- Model detail modal with tabs (Overview, Features, Training, Export)
- Model comparison mode (select 2-4 models for side-by-side)
- Download model files (pickle/ONNX)

### 4. Reports Library (`/reports`)
Access and share generated analysis reports.

**Features:**
- Report cards with title, problem type, timestamp, key insights preview
- HTML report viewer (full-screen with table of contents navigation)
- Markdown viewer with syntax highlighting
- Download ZIP (report + charts + model)
- Delete with confirmation

---

## Global Layout

### Navigation Structure
- **Top Bar**: DA System logo, user avatar, settings icon
- **Left Sidebar**: Collapsible navigation (Chat, Data, Models, Reports icons)
- **Main Content**: Fluid width, centered content
- **Mobile**: Hamburger menu, bottom sticky input for chat

### Cross-Page Flows
- Upload file anywhere → Automatically attached in Chat
- Complete analysis → "View Report" button navigates to Reports
- Click model in Reports → Opens Models detail modal
- "Use in Chat" from Data/Models → Pre-loads context in Chat

---

## Real-Time Features

### WebSocket Architecture
- Connection management with auto-reconnect
- Event handlers for:
  - `message.received` - Streaming AI responses
  - `status.update` - Progress tracking updates
  - `message.complete` - Finalization
- Mock WebSocket service for development (simulates realistic delays and events)

### Progress Tracking
- 5-step pipeline visualization
- Animated progress bars per step
- Time elapsed and estimated remaining
- Expandable details for research sources (HuggingFace, Kaggle, DeepResearch)

---

## Mock Data System
Since backend isn't ready yet, we'll build with realistic mock data:

**Sample Datasets:**
- Porto Seguro Insurance Claims (595K rows, binary classification)
- Titanic Survival (891 rows, binary classification)
- Customer Churn (7K rows, classification)

**Mock Responses:**
- Simulated WebSocket events with realistic timing
- Pre-built data profiles with statistics
- Sample model metrics (ROC-AUC 0.85-0.98 range)
- Generated report content with insights

---

## State Management

### Approach
- React Context for global state (session, WebSocket status, notifications)
- React Query for API data caching (files, models, reports lists)
- Component state for page-specific UI (filters, modals, selections)

### Key State
- Active chat session and messages
- WebSocket connection status
- Current analysis progress
- Toast notification queue

---

## UX Polish

### Loading States
- Skeleton screens for initial page loads
- Upload progress bar with percentage
- Typing indicator (animated dots) when AI is thinking
- Spinner overlays for async actions

### Empty States
- Illustrated empty states for each page
- Clear call-to-action buttons (Upload first file, Train first model)

### Error Handling
- Toast notifications for API errors
- Inline error messages for form validation
- "Connection lost" banner with auto-reconnect
- Retry buttons for failed operations

### Success Feedback
- Toast confirmations for uploads, completions, deletions
- Action buttons in toasts ("View Report", "View Model")

---

## Responsive Design

### Breakpoints
- **Desktop (>1280px)**: Full sidebar + content layout
- **Tablet (768-1280px)**: Collapsible sidebar
- **Mobile (<768px)**: Hidden sidebar with hamburger, sticky bottom input

### Touch Optimizations
- 44px minimum touch targets
- Swipe to open/close sidebar
- Pull to refresh on list pages

---

## Technical Stack
Using already-installed packages:
- **Routing**: React Router DOM
- **Styling**: Tailwind CSS with custom dark theme
- **Components**: Shadcn UI components (already available)
- **Charts**: Recharts (already installed)
- **Forms**: React Hook Form + Zod validation
- **API/State**: React Query
- **Notifications**: Sonner toasts (already configured)

---

## Implementation Order

**Phase 1 - Foundation (First)**
1. Dark theme design system and global layout
2. Sidebar navigation with routing
3. Chat page structure with message display
4. Mock WebSocket service

**Phase 2 - Chat Core**
1. File upload with drag-drop
2. Progress tracking visualization
3. Interactive result cards
4. Inline charts

**Phase 3 - Supporting Pages**
1. Data management page
2. Models tracking page
3. Reports page with viewer

**Phase 4 - Integration & Polish**
1. Cross-page navigation flows
2. Loading, empty, and error states
3. Mobile responsive refinement
4. WebSocket reconnection logic

---

## Success Criteria
✅ Smooth demo experience - every flow works end-to-end
✅ Real-time progress feels magical and engaging
✅ Clean ChatGPT-style dark aesthetic
✅ Mobile-friendly responsive design
✅ Ready to swap mocks for real API with minimal changes

