"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Server, Rocket, Loader2, X } from "lucide-react";

interface BentoML {
  id: number;
  name: string;
  endpoint_url: string;
  status: string;
}

interface VM {
  id: number;
  name: string;
  host: string;
  username: string;
}

export default function BentoMLPage() {
  const [conns, setConns] = useState<BentoML[]>([]);
  const [vms, setVms] = useState<VM[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", endpoint_url: "", api_key: "" });

  const [deployingId, setDeployingId] = useState<number | null>(null);
  const [showDeployModal, setShowDeployModal] = useState<number | null>(null);
  const [deployForm, setDeployForm] = useState({ vm_id: "", service_name: "my_service:svc", port: "3000" });

  const load = () => {
    api.get<BentoML[]>("/bentoml").then(setConns);
    api.get<VM[]>("/ssh/vms-list").then(setVms);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/bentoml", form);
    setForm({ name: "", endpoint_url: "", api_key: "" });
    setShowForm(false);
    load();
  };

  const handleTest = async (id: number) => {
    try {
      const res = await api.post<{ status: string; message?: string }>(`/bentoml/${id}/test`);
      const msg = res.message || `Status: ${res.status}`;
      res.status === "ok" || res.status === "success" || res.status === "connected"
        ? toast.success(msg)
        : toast.error(msg);
      load();
    } catch {
      toast.error("Test failed");
    }
  };

  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showDeployModal) return;

    setDeployingId(showDeployModal);
    try {
      const res = await api.post<{ status: string; message?: string; endpoint_url?: string }>(
        `/bentoml/${showDeployModal}/deploy`,
        {
          vm_id: parseInt(deployForm.vm_id),
          service_name: deployForm.service_name,
          port: parseInt(deployForm.port),
        }
      );

      if (res.status === "deployed") {
        toast.success(`Deployed to ${res.endpoint_url}`);
        setShowDeployModal(null);
      } else {
        toast.error(`Deploy failed: ${res.message}`);
      }
      load();
    } catch {
      toast.error("Deploy request failed");
    } finally {
      setDeployingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this connection?")) return;
    await api.delete(`/bentoml/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">BentoML Orchestration</h2>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "Add Connection"}
        </Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <input
            placeholder="Name (e.g. Production Model)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            required
          />
          <input
            placeholder="Endpoint URL (http://...)"
            value={form.endpoint_url}
            onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            required
          />
          <input
            placeholder="API Key (optional)"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            type="password"
          />
          <Button type="submit">Save Connection</Button>
        </form>
      )}

      <div className="space-y-3">
        {conns.map((c) => (
          <div key={c.id} className="rounded-lg border border-border p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 min-w-0">
                <div className="w-9 h-9 rounded-md flex items-center justify-center bg-muted text-muted-foreground shrink-0">
                  <Server size={18} />
                </div>
                <div className="min-w-0">
                  <p className="font-medium truncate">{c.name}</p>
                  <p className="text-sm text-muted-foreground truncate">{c.endpoint_url}</p>
                </div>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded shrink-0 ${
                  c.status === "connected" || c.status === "deployed"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-zinc-500/20 text-zinc-400"
                }`}
              >
                {c.status}
              </span>
            </div>

            <div className="mt-4 flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => handleTest(c.id)}>
                Test
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowDeployModal(c.id);
                  if (vms.length > 0 && !deployForm.vm_id)
                    setDeployForm({ ...deployForm, vm_id: vms[0].id.toString() });
                }}
              >
                <Rocket size={14} className="mr-1" />
                Deploy to VM
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleDelete(c.id)} className="ml-auto">
                Delete
              </Button>
            </div>
          </div>
        ))}
        {conns.length === 0 && (
          <p className="text-muted-foreground text-sm py-8 text-center border border-dashed rounded-lg">
            No BentoML instances found. Create or deploy one.
          </p>
        )}
      </div>

      {showDeployModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="w-full max-w-md rounded-lg border border-border bg-background p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Rocket size={18} />
                Remote Deployment
              </h3>
              <button
                onClick={() => setShowDeployModal(null)}
                className="p-1 rounded-md hover:bg-muted transition-colors"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleDeploy} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Target Machine (VM)</label>
                <select
                  value={deployForm.vm_id}
                  onChange={(e) => setDeployForm({ ...deployForm, vm_id: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  required
                >
                  <option value="" disabled>Select a VM…</option>
                  {vms.map((vm) => (
                    <option key={vm.id} value={vm.id}>
                      {vm.name} ({vm.username}@{vm.host})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Service Identifier</label>
                <input
                  placeholder="e.g. summarize_service:svc"
                  value={deployForm.service_name}
                  onChange={(e) => setDeployForm({ ...deployForm, service_name: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Port</label>
                <input
                  type="number"
                  value={deployForm.port}
                  onChange={(e) => setDeployForm({ ...deployForm, port: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  required
                />
              </div>

              <div className="pt-2 flex gap-2 justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowDeployModal(null)}
                  disabled={!!deployingId}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={!!deployingId || !deployForm.vm_id}>
                  {deployingId ? (
                    <>
                      <Loader2 className="animate-spin mr-2" size={16} />
                      Deploying…
                    </>
                  ) : (
                    "Start Deployment"
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
