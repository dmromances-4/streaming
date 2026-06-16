/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        stream: {
          bg: "#0b0b0f",
          surface: "#141414",
          elevated: "#1f1f1f",
          border: "#2a2a2a",
          muted: "#a3a3a3",
          accent: "#e50914",
          "accent-hover": "#f40612",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
