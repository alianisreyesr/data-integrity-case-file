import { useEffect, useState } from "react";

type AiStatus = {
  status: "ready" | "model_not_installed" | "service_unavailable";
  configured_model: string;
  service_available: boolean;
  model_available: boolean;
  message: string;
};

const labelByStatus: Record<AiStatus["status"], string> = {
  ready: "AI ready",
  model_not_installed: "AI model not installed",
  service_unavailable: "AI unavailable",
};

export default function AiStatus() {
  const [status, setStatus] = useState<AiStatus | null>(null);

  async function refreshStatus() {
    try {
      const response = await fetch("/api/ai/status");
      if (!response.ok) throw new Error("Unable to load AI status");
      setStatus((await response.json()) as AiStatus);
    } catch {
      setStatus({
        status: "service_unavailable",
        configured_model: "local model",
        service_available: false,
        model_available: false,
        message: "AI status cannot be loaded. The core case workflow remains available.",
      });
    }
  }

  useEffect(() => {
    refreshStatus();
  }, []);

  if (!status) {
    return <span className="muted" role="status">Checking AI status...</span>;
  }

  const badgeClass = status.status === "ready" ? "ok" : status.status === "model_not_installed" ? "open" : "gap";

  return (
    <div role="status" aria-live="polite" aria-label={status.message}>
      <span className={`badge ${badgeClass}`}>{labelByStatus[status.status]}</span>
      <button type="button" className="link" onClick={refreshStatus} style={{ marginLeft: "0.5rem" }}>
        Refresh AI status
      </button>
    </div>
  );
}
