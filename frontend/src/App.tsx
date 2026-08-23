import { useState } from "react";
import DataBoundaryBanner from "./components/DataBoundaryBanner";
import Dashboard from "./components/Dashboard";
import CaseList from "./components/CaseList";
import CaseDetail from "./components/CaseDetail";
import NewCaseForm from "./components/NewCaseForm";
import AuditLog from "./components/AuditLog";

type Tab = "dashboard" | "cases" | "new-case" | "audit-log";

const TAB_LABELS: Record<Tab, string> = {
  dashboard: "Dashboard",
  cases: "Cases",
  "new-case": "New case",
  "audit-log": "Audit log",
};

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);

  function goToCases() {
    setSelectedCaseId(null);
    setTab("cases");
  }

  function openCase(id: number) {
    setSelectedCaseId(id);
    setTab("cases");
  }

  function handleTabClick(key: Tab) {
    if (key === "cases") {
      goToCases();
    } else {
      setTab(key);
    }
  }

  return (
    <div className="app">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className="topbar">
        <h1>Data Integrity Case File</h1>
        <nav className="nav" aria-label="Main navigation">
          {(Object.keys(TAB_LABELS) as Tab[]).map((key) => (
            <button
              key={key}
              type="button"
              className={tab === key ? "active" : ""}
              aria-current={tab === key ? "page" : undefined}
              onClick={() => handleTabClick(key)}
            >
              {TAB_LABELS[key]}
            </button>
          ))}
        </nav>
      </header>
      <DataBoundaryBanner />
      <main className="main" id="main-content">
        {tab === "dashboard" && <Dashboard />}
        {tab === "cases" &&
          (selectedCaseId ? (
            <CaseDetail caseId={selectedCaseId} onBack={() => setSelectedCaseId(null)} />
          ) : (
            <CaseList onSelect={openCase} />
          ))}
        {tab === "new-case" && <NewCaseForm onCreated={openCase} />}
        {tab === "audit-log" && <AuditLog />}
      </main>
    </div>
  );
}
