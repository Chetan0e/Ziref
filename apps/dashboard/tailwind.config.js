/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* Semantic tokens — map to CSS variables */
        background:  "var(--background)",
        surface:     "var(--surface)",
        "surface-muted": "var(--surface-muted)",
        "text-primary":   "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        "text-tertiary":  "var(--text-tertiary)",
        border:      "var(--border)",
        "border-strong": "var(--border-strong)",

        /* Ziref brand blue scale */
        ziref: {
          50:  "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
          950: "#172554",
        },

        /* Keep these for backward compat during migration */
        foreground:          "#F4F4F5",
        muted:               "#27272A",
        "muted-foreground":  "#A1A1AA",
        card:                "#111113",
        "card-foreground":   "#F4F4F5",
        primary: {
          DEFAULT:    "#1D4ED8",
          hover:      "#1E40AF",
          foreground: "#FFFFFF",
        },
        success: {
          DEFAULT:    "#059669",
          foreground: "#FFFFFF",
        },
        warning: {
          DEFAULT:    "#D97706",
          foreground: "#000000",
        },
        destructive: {
          DEFAULT:    "#DC2626",
          foreground: "#FFFFFF",
        },
      },

      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["'JetBrains Mono'", "'Fira Code'", "ui-monospace", "SFMono-Regular", "monospace"],
      },

      letterSpacing: {
        tighter: "-0.04em",
        tight:   "-0.025em",
        snug:    "-0.015em",
      },

      lineHeight: {
        "hero": "1.0",
        "heading": "1.15",
        "relaxed": "1.65",
      },

      maxWidth: {
        "layout": "1280px",
        "prose-wide": "640px",
      },

      boxShadow: {
        "xs":   "var(--shadow-xs)",
        "card": "var(--shadow-sm)",
        "panel":"var(--shadow-md)",
        "float":"var(--shadow-lg)",
      },

      borderRadius: {
        "sm": "var(--radius-sm)",
        "md": "var(--radius-md)",
        "lg": "var(--radius-lg)",
      },

      animation: {
        "fade-in-up":     "fadeInUp 0.4s ease-out forwards",
        "cursor-blink":   "blink 1s step-end infinite",
      },
    },
  },
  plugins: [],
};
