import { useState } from "react";
import DataBoundaryBanner from "./components/DataBoundaryBanner";
import Dashboard from "./components/Dashboard";
import CaseList from "./components/CaseList";
import CaseDetail from "./components/CaseDetail";
import NewCaseForm from "./components/NewCaseForm";
import AuditLog from "./components/AuditLog";

type Tab = "dashboard" | "cases" | "new-case" | "audit-log";

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

  return (
    <div className="app">
      <div className="topbar">
        <h1>Data Integrity Case File</h1>
        <nav className="nav">
          <button className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>
            Dashboard
          </button>
          <button className={tab === "cases" ? "active" : ""} onClick={goToCases}>
            Cases
          </button>
          <button className={tab === "new-case" ? "active" : ""} onClick={() => setTab("new-case")}>
            New case
          </button>
          <button className={tab === "audit-log" ? "active" : ""} onClick={() => setTab("audit-log")}>
            Audit log
          </button>
        </nav>
      </div>
      <DataBoundaryBanner />
      <main className="main">
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
