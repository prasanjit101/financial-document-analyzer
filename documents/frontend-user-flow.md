### Frontend user flow outline

#### Overview
- **Goal**: Plain, unstyled React UI using only existing UI components. No custom CSS or Tailwind classes beyond what the provided UI components require.
- **Key components** (from `src/components/ui`): `card`, `button`, `input`, `progress`, `scroll-area`, `separator`, `dialog` (optional), `sonner` (optional toast), `form` helpers if needed.

### High-level flow
1. **App boot** → Check authentication state.
2. **Unauthenticated** → Show the authentication form.
3. **Authenticated** → Show Home page:
   - Top: Upload File card to create a new analysis.
   - Bottom: List of previously uploaded/analyzed files with a View button to open the analysis results.
4. **On upload** → open the analysis page for the new analysis. Display processing progress using `progress` component.
5. **On completion** → Display Dashboard/Analysis Results for the uploaded file.

#### Guidelines
- Keep the components modular
- If needed use zustand for state management

#### Uploading state (during processing)
- Replace Upload button area with a `progress` component showing current progress.
- Disable inputs during processing.
- No extra styles; only the default `progress` component.

#### Analysis Results (post-processing)
- Show result in a simple `card`.
- Provide a basic Back or Close action to return to Home.
- Update the Previous Files list to include the new result.

### UI constraints
- Use shadcn ui components for the UI.
- Do not add custom styles, CSS, or Tailwind classes beyond what components already include.
- Keep layout simple.

# Features
- Show toast notifications for errors and successes using shadcn ui `sonner` component.
- Export functionality for reports
- Handle edge cases:
  - File upload failures with proper error recovery
  - Large file uploads exceeding browser memory limits
  - Simultaneous document processing and UI responsiveness
  - Cross-origin resource sharing (CORS) issues

# Tech stack
- React vite
- Shadcn ui
- Tailwind css
