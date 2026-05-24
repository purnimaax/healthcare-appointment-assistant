/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Distinctive choices — not Inter, not Roboto
        display: ['"Fraunces"', "ui-serif", "Georgia", "serif"],
        body: ['"Instrument Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        // Calm clinical palette — sage + warm cream, single warm accent
        ink: {
          900: "#1c1f1d", // primary text
          700: "#3d423f",
          500: "#6b716e",
          300: "#a5aaa7",
        },
        paper: {
          50: "#fbf9f4",  // page background — warm off-white
          100: "#f4f1ea", // surface
          200: "#e8e3d6", // muted border
          300: "#d9d2bf",
        },
        sage: {
          50:  "#eef2ed",
          200: "#c8d3c5",
          400: "#7a9079",
          600: "#4d6b4f", // primary accent
          800: "#2d4030",
        },
        clay: {
          400: "#c97a5e", // warm secondary accent (used sparingly)
          600: "#9b5239",
        },
      },
      boxShadow: {
        soft: "0 1px 2px rgba(28,31,29,0.04), 0 4px 12px rgba(28,31,29,0.04)",
        card: "0 1px 0 rgba(28,31,29,0.04), 0 8px 28px rgba(28,31,29,0.06)",
      },
      keyframes: {
        "fade-in":   { "0%": { opacity: "0", transform: "translateY(4px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        "pulse-dot": { "0%,100%": { opacity: "0.4" }, "50%": { opacity: "1" } },
        "stripe":    { "0%": { backgroundPosition: "0 0" }, "100%": { backgroundPosition: "40px 0" } },
      },
      animation: {
        "fade-in":   "fade-in 0.25s ease-out",
        "pulse-dot": "pulse-dot 1.2s ease-in-out infinite",
        "stripe":    "stripe 1.2s linear infinite",
      },
    },
  },
  plugins: [],
};
