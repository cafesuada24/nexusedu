1. Architecture & Folder Structure
 * Strengths: Follows the standard Next.js App Router structure (app/, components/, hooks/, lib/). Clear separation between UI components and logic hooks.
 * Weaknesses:
     * Fat Components: Files like alert-center.tsx (34KB) and csv-uploader.tsx (26KB) are far too large. They contain business logic, complex UI, hardcoded sample data, and state management
       all in one.
     * Logic Leaks: Business logic (like CSV merging and normalization) is living inside UI components instead of pure utility functions or dedicated services.
 * Suggestion: Decompose large components into smaller, focused sub-components. Move heavy logic (e.g., mergeCsv in csv-uploader.tsx) to lib/csv.ts.

2. Backend Communication
 * Critical Issue: The project uses manual fetch wrappers in lib/api.ts.
 * Problems:
     * No Caching/Deduplication: Multiple components requesting the same data will trigger multiple network calls.
     * No Auto-Revalidation: Data doesn't automatically refresh on window focus or network reconnect.
     * Manual Loading States: Every component has to manually track isLoading, isError.
 * Suggestion: Implement TanStack Query (React Query) or SWR. This will eliminate ~40% of your boilerplate in hooks and provide a professional-grade cache layer.

3. State Management
 * Current State: Uses a mix of React Context (useAuth) and localStorage with custom event listeners (useDataset).
 * Risks:
     * useDataset is "pseudo-global." Using window.dispatchEvent and storage events is a clever hack but fragile. It lacks the debugging tools (DevTools) and selector optimizations of a real
       state manager.
     * Scalability: As the dataset grows, localStorage will hit its 5MB limit quickly, and JSON.parse on every change will block the main thread.
 * Suggestion: For client-side state, consider Zustand. It’s lightweight and handles the "event-based" updates much more cleanly than manual event listeners.

4. Code Quality & Modularity
 * Hardcoded Data: csv-uploader.tsx contains a massive hardcoded SAMPLE_CSV string. This should be moved to a .constant.ts file or an asset.
 * Type Safety: Good use of TypeScript and Zod for schema validation.
 * Surgical Changes: The project uses v0.app or similar AI-generation tools (noted in metadata). This often leads to "everything-in-one-file" syndrome.
 * Suggestion: Audit large components and enforce a maximum line count (e.g., 200-300 lines). Anything larger usually indicates a missing abstraction.

5. Optimization & Performance
 * Re-renders: Because large state objects are passed down via Context or custom hooks without fine-grained selectors, small changes (like an input typing) might re-render the entire
   AlertCenter.
 * CSV Processing: Large CSVs are processed on the main thread.
 * Suggestion: Use Web Workers for CSV parsing/merging to keep the UI responsive. Implement useMemo and React.memo for expensive UI branches in AlertCenter.

6. Error Handling & Observability
 * UI Feedback: Good usage of sonner for toasts.
 * Observability: Virtually non-existent. There are no structured logs or error boundaries.
 * Suggestion:
     * Implement Sentry or a similar error-tracking tool.
     * Add a global Error Boundary to catch component-level crashes and provide a "Reset App" button.
     * Replace console.error with a centralized logger utility that can be toggled per environment.

7. Scalability & Production Readiness
 * Current Grade: MVP-Ready, not Enterprise-Ready.
 * Missing Features:
     * Unit/Integration Tests: I see a tests/ folder in the root, but very few frontend-specific tests (mostly API/Agents).
     * CI/CD: No GitHub Actions or similar workflows visible for automated linting/testing.
     * Environment Parity: The API base URL defaults to /api/v1, which might break in different deployment environments (Staging vs. Prod).

Summary of Recommendations:
 1. Introduce TanStack Query: Immediately migrate lib/api.ts calls to useQuery and useMutation.
 2. Refactor AlertCenter and CsvUploader: Break them into at least 4-5 sub-components each.
 3. Move Logic to lib/: Centralize all CSV manipulation and data transformation logic.
 4. Add Error Boundaries: Ensure the entire dashboard doesn't go white if one chart fails.
 5. Environment Config: Ensure NEXT_PUBLIC_API_BASE_URL is rigorously used and documented in .env.example.

Is there a specific module (like the AlertCenter) you'd like me to help refactor or optimize first?
