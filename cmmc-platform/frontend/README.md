# CMMC Compliance Platform - Frontend

Modern React application for CMMC Level 2 compliance assessments.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **TanStack Query** - Server state management
- **Zustand** - Client state management
- **Axios** - HTTP client
- **Recharts** - Data visualization
- **Lucide React** - Icon library

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── layout/         # Layout components (Header, Sidebar, etc.)
│   │   ├── common/         # Common components (Button, Card, etc.)
│   │   ├── dashboard/      # Dashboard-specific components
│   │   ├── assessment/     # Assessment-related components
│   │   └── controls/       # Control findings components
│   ├── pages/              # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Assessments.tsx
│   │   ├── AssessmentDetail.tsx
│   │   ├── Controls.tsx
│   │   ├── Evidence.tsx
│   │   ├── Reports.tsx
│   │   ├── BulkOperations.tsx
│   │   ├── Settings.tsx
│   │   └── Login.tsx
│   ├── services/           # API services
│   │   ├── api.ts         # Axios instance and interceptors
│   │   ├── auth.ts        # Authentication service
│   │   ├── assessments.ts # Assessment API calls
│   │   ├── controls.ts    # Control findings API calls
│   │   ├── evidence.ts    # Evidence API calls
│   │   ├── bulk.ts        # Bulk operations API calls
│   │   └── dashboard.ts   # Dashboard analytics API calls
│   ├── hooks/              # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useAssessments.ts
│   │   ├── useControls.ts
│   │   └── useDashboard.ts
│   ├── stores/             # Zustand stores
│   │   └── authStore.ts
│   ├── types/              # TypeScript types
│   │   ├── assessment.ts
│   │   ├── control.ts
│   │   ├── evidence.ts
│   │   └── user.ts
│   ├── utils/              # Utility functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── index.html             # HTML template
├── package.json           # Dependencies
├── vite.config.ts         # Vite configuration
├── tsconfig.json          # TypeScript configuration
├── tailwind.config.js     # Tailwind configuration
└── README.md             # This file
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
# Start dev server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Format code
npm run format
```

## Key Features

### 1. Dashboard
- Real-time compliance metrics
- Assessment progress tracking
- Domain-level heatmap
- Recent activity feed
- Time & cost savings calculator

### 2. Assessment Management
- Create and manage assessments
- 6-status workflow (Draft → Completed)
- Scope configuration
- Team assignments
- Progress tracking

### 3. Control Findings
- 110 CMMC Level 2 controls
- Status tracking (Met, Not Met, Partially Met, N/A)
- Implementation narratives
- Evidence linking
- AI confidence scores
- Risk level assessment

### 4. Evidence Management
- File upload and organization
- Evidence types and tagging
- Control linkage
- Document preview
- Search and filter

### 5. Bulk Operations
- Bulk control updates (50-100 at once)
- ZIP file evidence upload
- Excel import/export
- Mass assignments
- Domain operations

### 6. Reports
- SSP generation (100-400 pages)
- POA&M generation (Excel)
- Executive summary PDFs
- Export to Word/Excel

### 7. User Management
- Authentication (JWT)
- Role-based access control (Admin, Assessor, Auditor, Viewer)
- User profile management
- Organization settings

## Component Library

### Layout Components

**Header**
```tsx
<Header />
```
- Logo and branding
- Navigation menu
- User profile dropdown
- Notifications

**Sidebar**
```tsx
<Sidebar />
```
- Main navigation
- Assessment selector
- Quick actions
- Collapsible for mobile

**MainLayout**
```tsx
<MainLayout>
  <YourPageContent />
</MainLayout>
```
- Combines Header + Sidebar
- Responsive layout
- Breadcrumbs

### Common Components

**Button**
```tsx
<Button variant="primary" size="md" onClick={handleClick}>
  Click Me
</Button>
```
Variants: `primary | secondary | danger | ghost`
Sizes: `sm | md | lg`

**Card**
```tsx
<Card title="Card Title" subtitle="Subtitle">
  <CardContent />
</Card>
```

**Badge**
```tsx
<Badge variant="success">Met</Badge>
```
Variants: `success | warning | danger | gray | blue`

**Input**
```tsx
<Input
  label="Email"
  type="email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
  error={errors.email}
/>
```

**Select**
```tsx
<Select
  label="Status"
  value={status}
  onChange={setStatus}
  options={[
    { value: 'met', label: 'Met' },
    { value: 'not_met', label: 'Not Met' }
  ]}
/>
```

**Modal**
```tsx
<Modal isOpen={isOpen} onClose={handleClose} title="Modal Title">
  <ModalContent />
</Modal>
```

**Table**
```tsx
<Table
  columns={columns}
  data={data}
  onRowClick={handleRowClick}
  loading={isLoading}
/>
```

**ProgressBar**
```tsx
<ProgressBar value={75} max={100} variant="success" />
```

### Dashboard Components

**StatsCard**
```tsx
<StatsCard
  title="Compliance Rate"
  value="85%"
  trend="+5%"
  icon={<CheckCircle />}
  variant="success"
/>
```

**ComplianceHeatmap**
```tsx
<ComplianceHeatmap data={heatmapData} />
```
- Shows compliance % by domain
- Color-coded (green > amber > red)
- Interactive tooltips

**ProgressChart**
```tsx
<ProgressChart
  data={progressData}
  xKey="date"
  yKey="compliance"
/>
```

### Assessment Components

**AssessmentCard**
```tsx
<AssessmentCard
  assessment={assessment}
  onClick={() => navigate(`/assessments/${assessment.id}`)}
/>
```

**AssessmentStatus**
```tsx
<AssessmentStatus status="In Progress" />
```
- Color-coded by status
- Status badge with icon

**AssessmentTimeline**
```tsx
<AssessmentTimeline events={timelineEvents} />
```

### Control Components

**ControlCard**
```tsx
<ControlCard
  control={control}
  finding={finding}
  onStatusChange={handleStatusChange}
/>
```

**ControlStatusSelector**
```tsx
<ControlStatusSelector
  value={status}
  onChange={setStatus}
/>
```
Options: Met, Not Met, Partially Met, Not Applicable

**ControlNarrative**
```tsx
<ControlNarrative
  value={narrative}
  onChange={setNarrative}
  aiGenerated={aiNarrative}
  onAcceptAI={handleAcceptAI}
/>
```

**ProviderInheritanceBadge**
```tsx
<ProviderInheritanceBadge provider="Microsoft365" type="Inherited" />
```

## API Integration

### Authentication

```tsx
import { useAuth } from '@/hooks/useAuth'

function Component() {
  const { user, login, logout, isAuthenticated } = useAuth()

  const handleLogin = async (email, password) => {
    await login({ email, password })
  }

  return (
    <div>
      {isAuthenticated ? (
        <p>Welcome, {user.fullName}</p>
      ) : (
        <LoginForm onSubmit={handleLogin} />
      )}
    </div>
  )
}
```

### Data Fetching with TanStack Query

```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/services/assessments'

function Assessments() {
  const queryClient = useQueryClient()

  // Fetch assessments
  const { data: assessments, isLoading } = useQuery({
    queryKey: ['assessments'],
    queryFn: api.getAssessments
  })

  // Create assessment
  const createMutation = useMutation({
    mutationFn: api.createAssessment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] })
    }
  })

  return (
    <div>
      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <AssessmentList assessments={assessments} />
      )}
    </div>
  )
}
```

### API Service Example

```tsx
// services/assessments.ts
import { api } from './api'

export const getAssessments = async () => {
  const { data } = await api.get('/api/v1/assessments')
  return data
}

export const getAssessment = async (id: string) => {
  const { data } = await api.get(`/api/v1/assessments/${id}`)
  return data
}

export const createAssessment = async (assessment: CreateAssessmentDto) => {
  const { data } = await api.post('/api/v1/assessments', assessment)
  return data
}

export const updateAssessment = async (id: string, updates: Partial<Assessment>) => {
  const { data } = await api.put(`/api/v1/assessments/${id}`, updates)
  return data
}
```

## State Management

### Auth Store (Zustand)

```tsx
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setTokens: (access: string, refresh: string) => void
  setUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setTokens: (access, refresh) => set({
        accessToken: access,
        refreshToken: refresh,
        isAuthenticated: true
      }),
      setUser: (user) => set({ user }),
      logout: () => set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false
      })
    }),
    { name: 'auth-storage' }
  )
)
```

## Routing

```tsx
// App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/assessments" element={<Assessments />} />
          <Route path="/assessments/:id" element={<AssessmentDetail />} />
          <Route path="/controls/:assessmentId" element={<Controls />} />
          <Route path="/evidence/:assessmentId" element={<Evidence />} />
          <Route path="/bulk" element={<BulkOperations />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

## Styling Guidelines

### Tailwind Utility Classes

Use Tailwind's utility-first approach:

```tsx
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm">
  <h2 className="text-xl font-semibold text-gray-900">Title</h2>
  <button className="btn-primary">Action</button>
</div>
```

### Custom Components with @apply

For repeated patterns, use `@apply` in CSS:

```css
.card {
  @apply bg-white rounded-lg shadow-sm border border-gray-200 p-6;
}
```

### Color Palette

- **Primary**: Blue (`primary-500`, `primary-600`, `primary-700`)
- **Success**: Green (`success-500`)
- **Warning**: Yellow (`warning-500`)
- **Danger**: Red (`danger-500`)
- **Gray**: Neutral (`gray-50` to `gray-900`)

## Performance Optimization

### Code Splitting

```tsx
import { lazy, Suspense } from 'react'

const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Assessments = lazy(() => import('@/pages/Assessments'))

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/assessments" element={<Assessments />} />
      </Routes>
    </Suspense>
  )
}
```

### Memoization

```tsx
import { useMemo, useCallback } from 'react'

function Component({ data }) {
  // Memoize expensive calculations
  const processedData = useMemo(() => {
    return data.map(/* expensive operation */)
  }, [data])

  // Memoize callbacks
  const handleClick = useCallback(() => {
    // handle click
  }, [/* dependencies */])

  return <ExpensiveComponent data={processedData} onClick={handleClick} />
}
```

### Virtual Scrolling

For large lists (100+ items), use virtual scrolling:

```tsx
import { useVirtualizer } from '@tanstack/react-virtual'

function LargeList({ items }) {
  const parentRef = useRef()

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
  })

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            {items[virtualRow.index]}
          </div>
        ))}
      </div>
    </div>
  )
}
```

## Testing

### Unit Tests

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '@/components/common/Button'

test('button calls onClick when clicked', () => {
  const handleClick = jest.fn()
  render(<Button onClick={handleClick}>Click me</Button>)

  fireEvent.click(screen.getByText('Click me'))

  expect(handleClick).toHaveBeenCalledTimes(1)
})
```

### Integration Tests

```tsx
import { renderWithProviders } from '@/test-utils'
import { Assessments } from '@/pages/Assessments'

test('displays assessment list', async () => {
  renderWithProviders(<Assessments />)

  expect(await screen.findByText('Q1 2024 Assessment')).toBeInTheDocument()
})
```

## Deployment

### Build for Production

```bash
npm run build
```

Output: `dist/` directory

### Environment Variables

Create `.env` file:

```env
VITE_API_URL=https://api.example.com
VITE_APP_NAME=CMMC Compliance Platform
```

Access in code:

```tsx
const apiUrl = import.meta.env.VITE_API_URL
```

### Deploy to Static Hosting

The built app can be deployed to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- Azure Static Web Apps
- GitHub Pages

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## License

Internal use only - CMMC Compliance Platform
