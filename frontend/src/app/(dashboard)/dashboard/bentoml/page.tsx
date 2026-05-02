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
  
  // Deploy State
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
          port: parseInt(deployForm.port)
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
    <div className="relative">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">BentoML Orchestration</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Connection"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3 bg-card shadow-sm">
          <input placeholder="Name (e.g. Production Model)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-1 focus:ring-accent outline-none" required />
          <input placeholder="Endpoint URL (http://...)" value={form.endpoint_url} onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-1 focus:ring-accent outline-none" required />
          <input placeholder="API Key (optional)" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-1 focus:ring-accent outline-none" type="password" />
          <Button type="submit">Save Connection</Button>
        </form>
      )}

      <div className="grid gap-4">
        {conns.map((c) => (
          <div key={c.id} className="group relative rounded-xl border border-border p-5 bg-card hover:border-accent/50 transition-all shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex gap-4">
                <div className="p-3 rounded-lg bg-accent/10 text-accent">
                  <Server size={24} />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">{c.name}</h3>
                  <code className="text-sm text-muted-foreground bg-muted/50 px-2 py-0.5 rounded">{c.endpoint_url}</code>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded-full ${c.status === "connected" || c.status === "deployed" ? "bg-green-500/10 text-green-400" : "bg-zinc-500/10 text-zinc-400"}`}>
                  {c.status}
                </span>
              </div>
            </div>

            <div className="mt-6 flex items-center gap-3">
              <Button variant="secondary" size="sm" onClick={() => handleTest(c.id)} className="flex items-center gap-2">
                Check Health
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  setShowDeployModal(c.id);
                  if (vms.length > 0 && !deployForm.vm_id) setDeployForm({...deployForm, vm_id: vms[0].id.toString()});
                }}
                className="flex items-center gap-2 border-accent/20 text-accent hover:bg-accent/10"
              >
                <Rocket size={14} />
                Deploy to VM
              </Button>
              <Button variant="ghost" size="sm" onClick={() => handleDelete(c.id)} className="ml-auto text-danger hover:bg-danger/10 hover:text-danger">
                Delete
              </Button>
            </div>
          </div>
        ))}
        {conns.length === 0 && (
          <div className="text-center py-12 rounded-xl border border-dashed border-border text-muted-foreground">
            No BentoML instances found. Create or deploy one.
          </div>
        )}
      </div>

      {/* Deploy Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <Rocket className="text-accent" />
                Remote Deployment
              </h3>
              <button onClick={() => setShowDeployModal(null)} className="p-1 rounded-full hover:bg-muted transition-colors">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleDeploy} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-muted-foreground">Target Machine (VM)</label>
                <select 
                  value={deployForm.vm_id} 
                  onChange={(e) => setDeployForm({ ...deployForm, vm_id: e.target.value })}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/20"
                  required
                >
                  <option value="" disabled>Select a VM...</option>
                  {vms.map(vm => (
                    <option key={vm.id} value={vm.id}>{vm.name} ({vm.username}@{vm.host})</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-muted-foreground">Service Identifier</label>
                <input 
                  placeholder="e.g. summarize_service:svc" 
                  value={deployForm.service_name} 
                  onChange={(e) => setDeployForm({ ...deployForm, service_name: e.target.value })}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/20"
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-muted-foreground">Port</label>
                <input 
                  type="number" 
                  value={deployForm.port} 
                  onChange={(e) => setDeployForm({ ...deployForm, port: e.target.value })}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-accent/20"
                  required
                />
              </div>

              <div className="pt-4 flex gap-3">
                <Button 
                  type="button" 
                  variant="ghost" 
                  className="flex-1" 
                  onClick={() => setShowDeployModal(null)}
                  disabled={!!deployingId}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="flex-1 gap-2"
                  disabled={!!deployingId || !deployForm.vm_id}
                >
                  {deployingId ? (
                    <>
                      <Loader2 className="animate-spin" size={16} />
                      Deploying...
                    </>
                  ) : (
                    <>Start Deployment</>
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

