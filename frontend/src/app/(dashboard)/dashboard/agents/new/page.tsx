"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Provider {
  id: number;
  name: string;
  type: string;
  status: string;
}

export default function NewAgentPage() {
  const router = useRouter();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsHint, setModelsHint] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    name: "",
    role: "",
    model: "",
    system_prompt: "",
    llm_provider_id: "",
    port: "",
  });

  useEffect(() => {
    api.get<Provider[]>("/providers").then(setProviders);
  }, []);

  // Подгружаем модели когда выбирается провайдер
  const handleProviderChange = async (providerId: string) => {
    setForm((prev) => ({ ...prev, llm_provider_id: providerId, model: "" }));
    setModels([]);
    setModelsHint("");

    if (!providerId) return;

    setModelsLoading(true);
    try {
      const res = await api.get<{ models: string[]; hint?: string }>(`/providers/${providerId}/models`);
      setModels(res.models);
      if (res.hint) setModelsHint(res.hint);
    } catch {
      setModelsHint("Failed to load models. Try connecting the provider first.");
    } finally {
      setModelsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api.post("/agents", {
        ...form,
        llm_provider_id: form.llm_provider_id ? parseInt(form.llm_provider_id) : null,
        port: form.port ? parseInt(form.port) : null,
      });
      router.push("/dashboard/agents");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agent");
      setSubmitting(false);
    }
  };

  const selectedProvider = providers.find((p) => String(p.id) === form.llm_provider_id);

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-6">Create Agent</h2>

      {error && (
        <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium mb-1">Agent Name</label>
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            required
            placeholder="e.g. Code Assistant"
          />
        </div>

        {/* Role */}
        <div>
          <label className="block text-sm font-medium mb-1">Role</label>
          <input
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            required
            placeholder="e.g. code, security, analyst, support"
          />
        </div>

        {/* LLM Provider */}
        <div>
          <label className="block text-sm font-medium mb-1">LLM Provider</label>
          <select
            value={form.llm_provider_id}
            onChange={(e) => handleProviderChange(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">Select provider...</option>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.type}){p.status !== "connected" ? " — ⚠ not connected" : " — ✓ connected"}
              </option>
            ))}
          </select>
          {selectedProvider && selectedProvider.status !== "connected" && (
            <p className="mt-1 text-xs text-amber-500">
              This provider is not connected. Go to{" "}
              <a href="/dashboard/providers" className="underline">Providers</a> and click Connect first.
            </p>
          )}
        </div>

        {/* Model */}
        <div>
          <label className="block text-sm font-medium mb-1">Model</label>
          {modelsLoading ? (
            <div className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-muted-foreground animate-pulse">
              Loading models...
            </div>
          ) : models.length > 0 ? (
            <select
              value={form.model}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            >
              <option value="">Select model...</option>
              {models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          ) : (
            <>
              <input
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                required
                placeholder={
                  form.llm_provider_id
                    ? "Type model name manually..."
                    : "Select a provider first to load models"
                }
              />
              {modelsHint && (
                <p className="mt-1 text-xs text-muted-foreground">{modelsHint}</p>
              )}
            </>
          )}
        </div>

        {/* System Prompt */}
        <div>
          <label className="block text-sm font-medium mb-1">System Prompt</label>
          <textarea
            value={form.system_prompt}
            onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm h-36"
            required
            placeholder="You are a helpful AI assistant specialized in..."
          />
        </div>

        {/* Port (optional) */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Port <span className="text-muted-foreground font-normal">(optional)</span>
          </label>
          <input
            value={form.port}
            onChange={(e) => setForm({ ...form, port: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            placeholder="e.g. 3005"
            type="number"
          />
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Agent"}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
