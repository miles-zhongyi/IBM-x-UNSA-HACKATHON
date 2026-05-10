import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function PortalLayout({ role }) {
  return (
    <div className="flex min-h-screen bg-[#F7FFFD]">
      <Sidebar role={role} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar role={role} />
        <main data-testid={`${role}-main-content`} className="flex-1 px-6 lg:px-10 py-8 max-w-[1600px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
