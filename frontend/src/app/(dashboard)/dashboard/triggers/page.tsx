import { AgentTriggersPanel } from "@/components/agent-triggers-panel";

export default function TriggersPage() {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Triggers</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Schedule recurring tasks and fan them out to one or more agents.
        </p>
      </div>
      <AgentTriggersPanel />
    </div>
  );
}
