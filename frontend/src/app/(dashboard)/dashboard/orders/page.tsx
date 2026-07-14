// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface OrderItem {
  id: number;
  product_id: number | null;
  product_name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

interface Order {
  id: number;
  contact_id: number;
  deal_id: number | null;
  status: string;
  total: number;
  currency: string;
  assigned_agent_id: number | null;
  source: string | null;
  campaign: string | null;
  notes: string | null;
  created_at: string;
  items: OrderItem[];
}

interface Product {
  id: number;
  sku: string;
  name: string;
  price: number;
  currency: string;
  active: boolean;
}

interface Contact {
  id: number;
  name: string;
}

interface OrderMetrics {
  realized_revenue: number;
  booked_revenue: number;
  order_count: number;
  count_by_status: Record<string, number>;
  revenue_by_status: Record<string, number>;
  pipeline_value: number;
  win_rate: number;
}

const STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"];

// Legal forward moves per the backend ALLOWED_TRANSITIONS graph.
const ALLOWED_NEXT: Record<string, string[]> = {
  pending: ["processing", "cancelled"],
  processing: ["shipped", "cancelled"],
  shipped: ["delivered", "cancelled"],
  delivered: [],
  cancelled: [],
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-blue-500/20 text-blue-400",
  processing: "bg-yellow-500/20 text-yellow-400",
  shipped: "bg-purple-500/20 text-purple-400",
  delivered: "bg-green-500/20 text-green-400",
  cancelled: "bg-red-500/20 text-red-400",
};

interface FormItem {
  product_id: string;
  quantity: string;
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [metrics, setMetrics] = useState<OrderMetrics | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [mineOnly, setMineOnly] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [contactId, setContactId] = useState("");
  const [source, setSource] = useState("");
  const [campaign, setCampaign] = useState("");
  const [items, setItems] = useState<FormItem[]>([{ product_id: "", quantity: "1" }]);

  const load = () => {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status", statusFilter);
    if (mineOnly) params.set("mine", "true");
    const qs = params.toString();
    api.get<Order[]>(`/crm/orders${qs ? `?${qs}` : ""}`).then(setOrders);
    api.get<OrderMetrics>("/crm/orders/metrics").then(setMetrics).catch(() => {});
  };

  useEffect(() => {
    load();
    api.get<Contact[]>("/crm/contacts").then(setContacts);
    api.get<Product[]>("/crm/products").then(setProducts).catch(() => setProducts([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, mineOnly]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      contact_id: parseInt(contactId),
      source: source || null,
      campaign: campaign || null,
      items: items
        .filter((it) => it.product_id)
        .map((it) => ({
          product_id: parseInt(it.product_id),
          quantity: parseInt(it.quantity) || 1,
        })),
    };
    await api.post("/crm/orders", payload);
    setContactId("");
    setSource("");
    setCampaign("");
    setItems([{ product_id: "", quantity: "1" }]);
    setShowForm(false);
    load();
  };

  const handleStatus = async (orderId: number, status: string) => {
    if (!status) return;
    try {
      await api.put(`/crm/orders/${orderId}/status?status=${status}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Could not change status");
    }
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this order?")) return;
    await api.delete(`/crm/orders/${id}`);
    load();
  };

  const contactName = (id: number) => contacts.find((c) => c.id === id)?.name || `#${id}`;

  const addFormItem = () => setItems([...items, { product_id: "", quantity: "1" }]);
  const setFormItem = (idx: number, patch: Partial<FormItem>) =>
    setItems(items.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  const removeFormItem = (idx: number) => setItems(items.filter((_, i) => i !== idx));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Orders</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "New Order"}</Button>
      </div>

      {/* Metrics band */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="p-3 rounded-lg border border-border">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Realized revenue</p>
            <p className="text-xl font-bold">${metrics.realized_revenue.toLocaleString()}</p>
          </div>
          <div className="p-3 rounded-lg border border-border">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Booked revenue</p>
            <p className="text-xl font-bold">${metrics.booked_revenue.toLocaleString()}</p>
          </div>
          <div className="p-3 rounded-lg border border-border">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Open pipeline</p>
            <p className="text-xl font-bold">${metrics.pipeline_value.toLocaleString()}</p>
          </div>
          <div className="p-3 rounded-lg border border-border">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Orders</p>
            <p className="text-xl font-bold">{metrics.order_count}</p>
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <select value={contactId} onChange={(e) => setContactId(e.target.value)} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required>
              <option value="">Select customer...</option>
              {contacts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <div className="grid grid-cols-2 gap-3">
              <input placeholder="Source" value={source} onChange={(e) => setSource(e.target.value)} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
              <input placeholder="Campaign" value={campaign} onChange={(e) => setCampaign(e.target.value)} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">Items</p>
            {items.map((it, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                <select value={it.product_id} onChange={(e) => setFormItem(idx, { product_id: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required>
                  <option value="">Select product...</option>
                  {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.currency} {p.price})</option>)}
                </select>
                <input type="number" min="1" value={it.quantity} onChange={(e) => setFormItem(idx, { quantity: e.target.value })} className="w-20 rounded-md border border-input bg-background px-3 py-2 text-sm" />
                {items.length > 1 && <Button type="button" variant="outline" size="sm" onClick={() => removeFormItem(idx)}>×</Button>}
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={addFormItem}>+ Add item</Button>
          </div>

          <Button type="submit">Create Order</Button>
          {products.length === 0 && (
            <p className="text-xs text-muted-foreground">No products yet — add products to the catalog first.</p>
          )}
        </form>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-md border border-input bg-background px-3 py-2 text-sm">
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} />
          Assigned orders only
        </label>
      </div>

      <div className="space-y-3">
        {orders.map((o) => (
          <div key={o.id} className="rounded-lg border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Order #{o.id} · {contactName(o.contact_id)}</p>
                <p className="text-sm text-muted-foreground">
                  {o.currency} {o.total.toLocaleString()} · {o.items.length} item{o.items.length === 1 ? "" : "s"}
                  {o.source ? ` · ${o.source}` : ""}{o.campaign ? ` / ${o.campaign}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-1 rounded ${STATUS_COLORS[o.status] || "bg-zinc-500/20 text-zinc-400"}`}>
                  {o.status}
                </span>
                {ALLOWED_NEXT[o.status]?.length > 0 && (
                  <select
                    value=""
                    onChange={(e) => handleStatus(o.id, e.target.value)}
                    className="text-xs px-2 py-1 rounded border border-input bg-background"
                  >
                    <option value="">Move to...</option>
                    {ALLOWED_NEXT[o.status].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                )}
                <Button variant="outline" size="sm" onClick={() => handleDelete(o.id)}>Delete</Button>
              </div>
            </div>
            {o.items.length > 0 && (
              <ul className="mt-3 border-t border-border pt-2 text-sm text-muted-foreground space-y-1">
                {o.items.map((it) => (
                  <li key={it.id} className="flex justify-between">
                    <span>{it.product_name} × {it.quantity}</span>
                    <span>{o.currency} {it.line_total.toLocaleString()}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {orders.length === 0 && <p className="text-muted-foreground text-sm">No orders yet.</p>}
      </div>
    </div>
  );
}
