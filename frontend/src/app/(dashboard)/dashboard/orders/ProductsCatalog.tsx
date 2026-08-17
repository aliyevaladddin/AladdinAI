"use client";

import { useMemo, useState, FormEvent } from "react";
import { Package, Plus, Search, Pencil, Trash2, Power, X } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export interface CatalogProduct {
  id: number;
  sku: string;
  name: string;
  description?: string | null;
  price: number;
  currency: string;
  active: boolean;
}

const CURRENCIES = ["USD", "EUR", "AZN", "TRY", "GBP", "RUB"];

interface ProductsCatalogProps {
  products: CatalogProduct[];
  onChanged: () => void;
}

interface FormState {
  sku: string;
  name: string;
  description: string;
  price: string;
  currency: string;
  active: boolean;
}

const EMPTY_FORM: FormState = {
  sku: "",
  name: "",
  description: "",
  price: "",
  currency: "USD",
  active: true,
};

/** Pull the FastAPI `detail` out of the api-client error text, if present. */
function apiErrorMessage(err: unknown, fallback: string): string {
  const raw = err instanceof Error ? err.message : String(err);
  const m = raw.match(/"detail"\s*:\s*"([^"]+)"/);
  return m ? m[1] : fallback;
}

export function ProductsCatalog({ products, onChanged }: ProductsCatalogProps) {
  const [query, setQuery] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) => p.sku.toLowerCase().includes(q) || p.name.toLowerCase().includes(q)
    );
  }, [products, query]);

  const openAdd = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setFormOpen(true);
  };

  const openEdit = (p: CatalogProduct) => {
    setEditingId(p.id);
    setForm({
      sku: p.sku,
      name: p.name,
      description: p.description ?? "",
      price: String(p.price),
      currency: p.currency,
      active: p.active,
    });
    setFormError(null);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingId(null);
    setFormError(null);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.sku.trim() || !form.name.trim()) {
      setFormError("SKU and name are required.");
      return;
    }
    const price = parseFloat(form.price);
    if (isNaN(price) || price < 0) {
      setFormError("Price must be a number greater than or equal to 0.");
      return;
    }
    const payload = {
      sku: form.sku.trim(),
      name: form.name.trim(),
      description: form.description.trim() || null,
      price,
      currency: form.currency,
      active: form.active,
    };
    setSaving(true);
    setFormError(null);
    try {
      if (editingId !== null) {
        await api.put(`/crm/products/${editingId}`, payload);
        toast.success("Product updated");
      } else {
        await api.post("/crm/products", payload);
        toast.success("Product added to the catalog");
      }
      closeForm();
      onChanged();
    } catch (err) {
      setFormError(apiErrorMessage(err, "Failed to save the product."));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (p: CatalogProduct) => {
    try {
      await api.put(`/crm/products/${p.id}`, { active: !p.active });
      onChanged();
    } catch {
      toast.error("Failed to update the product.");
    }
  };

  const handleDelete = async (p: CatalogProduct) => {
    if (!confirm(`Delete "${p.name}"? Orders that include it keep their snapshot of the item.`)) return;
    try {
      await api.delete(`/crm/products/${p.id}`);
      toast.success("Product deleted");
      if (editingId === p.id) closeForm();
      onChanged();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Failed to delete the product."));
    }
  };

  const inputCls =
    "rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20";

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative w-full max-w-xs">
          <Search size={14} className="absolute left-3 top-2.5 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by SKU or name..."
            className={`w-full pl-8 ${inputCls}`}
          />
        </div>
        <Button onClick={formOpen ? closeForm : openAdd} variant={formOpen ? "outline" : "default"}>
          {formOpen ? (
            <>
              <X size={14} /> Close
            </>
          ) : (
            <>
              <Plus size={14} /> Add Product
            </>
          )}
        </Button>
      </div>

      {/* Add / Edit form */}
      {formOpen && (
        <form onSubmit={handleSave} className="rounded-lg border border-border p-4 space-y-3">
          <p className="text-sm font-medium">
            {editingId !== null ? "Edit product" : "New product"}
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <input
              placeholder="SKU *"
              value={form.sku}
              onChange={(e) => setForm({ ...form, sku: e.target.value })}
              className={`${inputCls} font-mono`}
            />
            <input
              placeholder="Name *"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={`${inputCls} md:col-span-2`}
            />
            <select
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              className={inputCls}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3 items-center">
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="Price *"
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              className={inputCls}
            />
            {editingId !== null && (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                />
                Active (available for new orders)
              </label>
            )}
          </div>
          <textarea
            rows={2}
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className={`w-full resize-none ${inputCls}`}
          />
          {formError && <p className="text-xs text-red-500">{formError}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : editingId !== null ? "Save changes" : "Add product"}
            </Button>
            <Button type="button" variant="outline" onClick={closeForm}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {/* Catalog table */}
      {filtered.length > 0 ? (
        <div className="rounded-lg border border-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-medium">SKU</th>
                <th className="px-4 py-2.5 font-medium">Product</th>
                <th className="px-4 py-2.5 font-medium">Price</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((p) => (
                <tr key={p.id} className={p.active ? "" : "opacity-60"}>
                  <td className="px-4 py-3 font-mono text-xs whitespace-nowrap">{p.sku}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium">{p.name}</p>
                    {p.description && (
                      <p className="text-xs text-muted-foreground line-clamp-1">{p.description}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {p.currency} {p.price.toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        p.active
                          ? "bg-green-500/20 text-green-400"
                          : "bg-zinc-500/20 text-zinc-400"
                      }`}
                    >
                      {p.active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => openEdit(p)}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                        title="Edit product"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => toggleActive(p)}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                        title={p.active ? "Deactivate" : "Activate"}
                      >
                        <Power size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(p)}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-muted transition-colors"
                        title="Delete product"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-border p-10 text-center">
          <Package size={28} className="mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm font-medium mb-1">
            {query ? "Nothing matches your search" : "No products in the catalog yet"}
          </p>
          <p className="text-xs text-muted-foreground mb-4 max-w-sm mx-auto">
            {query
              ? "Try a different SKU or name."
              : "Add your first product — it becomes available in the New Order form immediately."}
          </p>
          {!query && (
            <Button size="sm" onClick={openAdd}>
              <Plus size={14} /> Add Product
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
