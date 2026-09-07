"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check, Search, X } from "lucide-react";

export interface ModelOption {
  id: string;
  is_supported: boolean;
  type?: string;
}

interface CustomModelSelectProps {
  value: string;
  onChange: (value: string) => void;
  models: ModelOption[];
  disabled?: boolean;
  isVisionModel?: (model: string) => boolean;
  placeholder?: string;
  noneLabel?: string;
}

export function CustomModelSelect({
  value,
  onChange,
  models,
  disabled = false,
  isVisionModel,
  placeholder = "Select model...",
  noneLabel,
}: CustomModelSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-focus search input when opened
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  const filteredModels = models.filter((m) =>
    m.id.toLowerCase().includes(search.toLowerCase())
  );

  const selectedModel = models.find((m) => m.id === value);

  return (
    <div className="relative w-full" ref={containerRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between gap-2 px-3 py-1.5 text-xs font-mono rounded-md border border-input bg-background hover:bg-surface-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-left"
      >
        <span className="truncate">
          {selectedModel ? (
            <>
              {selectedModel.id}
              {isVisionModel && isVisionModel(selectedModel.id) ? " — vision" : ""}
            </>
          ) : !value && noneLabel ? (
            <span className="text-muted-foreground">{noneLabel}</span>
          ) : value ? (
            `${value} (current)`
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </span>
        <ChevronDown size={14} className={`text-muted-foreground transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-background border border-border rounded-lg shadow-xl overflow-hidden animate-in fade-in-50 zoom-in-95 duration-150">
          <div className="p-2 border-b border-border flex items-center gap-2 bg-surface-1">
            <Search size={14} className="text-muted-foreground flex-shrink-0" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search models..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs font-mono bg-transparent focus:outline-none placeholder:text-muted-foreground"
            />
            {search && (
              <button type="button" onClick={() => setSearch("")} className="text-muted-foreground hover:text-foreground">
                <X size={12} />
              </button>
            )}
          </div>

          <div className="max-h-64 overflow-y-auto p-1 space-y-0.5 scrollbar-thin">
            {noneLabel && !search && (
              <button
                type="button"
                onClick={() => {
                  onChange("");
                  setIsOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-1.5 text-xs font-mono rounded text-left transition-colors ${
                  !value ? "bg-primary/10 text-primary font-semibold" : "hover:bg-surface-1 text-muted-foreground"
                }`}
              >
                <span className="truncate">{noneLabel}</span>
                {!value && <Check size={14} className="text-primary flex-shrink-0 ml-1" />}
              </button>
            )}

            {!models.some((m) => m.id === value) && value && !search && (
              <button
                type="button"
                onClick={() => {
                  onChange(value);
                  setIsOpen(false);
                }}
                className="w-full flex items-center justify-between px-3 py-1.5 text-xs font-mono rounded bg-accent/20 text-accent-foreground text-left"
              >
                <span className="truncate">{value} (current)</span>
                <Check size={12} />
              </button>
            )}

            {filteredModels.length === 0 ? (
              <div className="p-3 text-center text-xs text-muted-foreground">
                No models found
              </div>
            ) : (
              filteredModels.map((m) => {
                const isSelected = m.id === value;
                const isVision = isVisionModel ? isVisionModel(m.id) : false;

                return (
                  <button
                    key={m.id}
                    type="button"
                    disabled={!m.is_supported}
                    onClick={() => {
                      if (m.is_supported) {
                        onChange(m.id);
                        setIsOpen(false);
                      }
                    }}
                    className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-xs font-mono rounded transition-colors text-left ${
                      isSelected
                        ? "bg-primary/10 text-primary font-semibold"
                        : m.is_supported
                        ? "hover:bg-surface-1 text-foreground"
                        : "opacity-40 cursor-not-allowed bg-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate min-w-0">
                      <span className="truncate">{m.id}</span>
                      {isVision && (
                        <span className="text-[10px] px-1 py-0.2 rounded bg-amber-500/20 text-amber-500 flex-shrink-0">
                          vision
                        </span>
                      )}
                      {!m.is_supported && m.type && (
                        <span className="text-[10px] px-1 py-0.2 rounded bg-muted text-muted-foreground flex-shrink-0">
                          {m.type}
                        </span>
                      )}
                    </div>
                    {isSelected && <Check size={14} className="text-primary flex-shrink-0 ml-1" />}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
