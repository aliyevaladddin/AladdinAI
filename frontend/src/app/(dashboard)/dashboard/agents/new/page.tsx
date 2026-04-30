"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Provider {
  id: number;
  name: string;
  type: string;
}

export default function NewAgentPage() {
  const router = useRouter();
  const [providers, setProviders] = useState<Provider[]>([]);
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/agents", {
      ...form,
      llm_provider_id: form.llm_provider_id ? parseInt(form.llm_provider_id) : null,
      port: form.port ? parseInt(form.port) : null,
    });
    router.push("/dashboard/agents");
  };

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-6">Create Agent</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Agent Name</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required placeholder="e.g. Code Assistant" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Role</label>
          <input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required placeholder="e.g. code, security, analyst" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">LLM Provider</label>
            <select value={form.llm_provider_id} onChange={(e) => setForm({ ...form, llm_provider_id: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="">Select provider...</option>
              {providers.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.type})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Model</label>
            <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required placeholder="e.g. meta/llama-4-maverick" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">System Prompt</label>
          <textarea value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm h-32" required placeholder="You are a helpful AI assistant specialized in..." />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Port (optional)</label>
          <input value={form.port} onChange={(e) => setForm({ ...form, port: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder="e.g. 3005" type="number" />
        </div>
        <div className="flex gap-3">
          <Button type="submit">Create Agent</Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
        </div>
      </form>
    </div>
  );
}
