/**
 * SwarmShield design tokens — an oscilloscope / SOC-console palette.
 * Deliberately not the templated cream+terracotta or flat near-black+acid-green
 * defaults: deep graphite-blue base, amber for "in progress", cyan for "clear",
 * red reserved solely for confirmed violations so it stays meaningful.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0A0E13",
        panel: "#10161D",
        "panel-raised": "#161D26",
        grid: "#1E2731",
        "text-primary": "#E4EAEF",
        "text-muted": "#6B7A8A",
        amber: {
          DEFAULT: "#E8A33D",
          dim: "#3A2E1A",
        },
        cyan: {
          DEFAULT: "#3DDBD9",
          dim: "#123333",
        },
        critical: {
          DEFAULT: "#FF5C5C",
          dim: "#3A1414",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
        body: ["'Inter'", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(232,163,61,0.25), 0 0 20px rgba(232,163,61,0.15)",
        "glow-critical": "0 0 0 1px rgba(255,92,92,0.35), 0 0 24px rgba(255,92,92,0.25)",
        "glow-cyan": "0 0 0 1px rgba(61,219,217,0.25), 0 0 20px rgba(61,219,217,0.12)",
      },
      keyframes: {
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.35 },
        },
      },
      animation: {
        scanline: "scanline 1.6s linear infinite",
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
