// NOTICE: This file is protected under RCF-PL
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

// [RCF:PROTECTED]
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
