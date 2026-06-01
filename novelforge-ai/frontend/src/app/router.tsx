import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../shared/layout/AppLayout";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, lazy: () => import("../features/setup/SetupPage").then(m => ({ Component: m.SetupPage })) },
      { path: "setup", lazy: () => import("../features/setup/SetupPage").then(m => ({ Component: m.SetupPage })) },
      { path: "cockpit", lazy: () => import("../features/cockpit/CockpitPage").then(m => ({ Component: m.CockpitPage })) },
      { path: "diagnostics", lazy: () => import("../features/diagnostics/DiagnosticsPage").then(m => ({ Component: m.DiagnosticsPage })) },
      { path: "projects", lazy: () => import("../features/projects/ProjectsPage").then(m => ({ Component: m.ProjectsPage })) },
{ path: "projects/:id", lazy: () => import("../features/projects/ProjectDetailPage").then(m => ({ Component: m.ProjectDetailPage })) },
{ path: "*", lazy: () => import("../features/setup/SetupPage").then(m => ({ Component: m.SetupPage })) },
    ],
  },
]);
