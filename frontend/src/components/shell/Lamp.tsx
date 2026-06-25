// NOTICE: This file is protected under RCF-PL
import Image from "next/image";


interface LampProps {
  /** Pixel size of the lamp glyph itself. Default 34px (mockup). */
  size?: number;
  /** Optional ARIA label override. */
  label?: string;
}

/**
 * AladdinAI lamp logo.
 *
 * - Adaptive drop-shadow per theme (CSS in globals.css via [data-theme])
 * - Golden glow halo (::after) on mystic dark themes
 * - Warm medallion backdrop (::before) on light themes so the dark PNG
 *   doesn't get lost on near-white surfaces
 */

export function Lamp({ size = 34, label = "AladdinAI" }: LampProps) {
  return (
    <span
      className="lamp"
      role="img"
      aria-label={label}
      style={{ width: size, height: size }}
    >
      <Image
        src="/logo.png"
        alt=""
        width={size * 2}
        height={size * 2}
        priority
        sizes={`${size}px`}
        style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
      />
    </span>
  );
}
