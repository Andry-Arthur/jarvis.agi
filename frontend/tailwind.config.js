/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        jarvis: {
          50:  "#eef9ff",
          100: "#d9f1ff",
          200: "#bce8ff",
          300: "#8edaff",
          400: "#59c3ff",
          500: "#33a9ff",
          600: "#1a8cf5",
          700: "#1373e1",
          800: "#175cb6",
          900: "#194f8f",
          950: "#143059",
        },
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "wave": "wave 1.5s ease-in-out infinite",
      },
      keyframes: {
        wave: {
          "0%, 100%": { transform: "scaleY(0.3)" },
          "50%":       { transform: "scaleY(1)" },
        },
      },
    },
  },
  plugins: [],
};
