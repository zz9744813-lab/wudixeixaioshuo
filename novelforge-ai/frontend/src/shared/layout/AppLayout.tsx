import type { ReactNode } from "react";
import { Outlet } from "react-router-dom";

export function AppLayout({ children }: { children?: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      {children ?? <Outlet />}
    </div>
  );
}
