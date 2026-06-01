import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./shared/layout/AppLayout";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, lazy: () => import("../features/setup/SetupPage").then(m => ({ Component: m.SetupPage })) },
      { path: "setup", lazy: () => import("../features/setup/SetupPage").then(m => ({ Component: m.SetupPage })) },
      { path: "cockpit", lazy: () => import("../features/cockpit/CockpitPage").then(m => ({ Component: m.CockpitPage })) },
      { path: "diagnostics", lazy: () => import("../features/diagnostics/DiagnosticsPage").then(m => ({ Component: m.DiagnosticsPage })) },
      { path: "*", lazy: () => import("../features/setup/SetupPage").then(m => ({ Component: m.SetupPage })) },
    ],
  },
]);
