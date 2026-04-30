import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#131313",
        "on-background": "#e2e2e2",
        primary: "#ffffff",
        "on-primary": "#003737",
        "primary-container": "#00fbfb",
        "on-primary-container": "#007070",
        cyan: {
          400: "#00fbfb",
          DEFAULT: "#00fbfb",
          glow: "rgba(0, 255, 255, 0.3)",
        },
        surface: {
          DEFAULT: "#131313",
          container: "#1f1f1f",
          "container-low": "#1b1b1b",
          "container-high": "#2a2a2a",
          "container-highest": "#353535",
          lowest: "#0e0e0e",
          plate: "#0A0A0B",
        }
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        header: ["Space Grotesk", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
        data: ["JetBrains Mono", "monospace"],
      },
      spacing: {
        unit: "4px",
        gutter: "24px",
        "stack-sm": "8px",
        "stack-md": "16px",
        "stack-lg": "32px",
      },
      boxShadow: {
        'cyan-glow': '0 0 15px rgba(0, 255, 255, 0.15)',
        'cyan-pulse': '0 0 10px rgba(0, 255, 255, 0.3)',
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid': '32px 32px',
      }
    },
  },
  plugins: [],
};
export default config;
