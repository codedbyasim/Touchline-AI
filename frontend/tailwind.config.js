/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Oswald", "Arial Narrow", "sans-serif"],
        sans: ["Figtree", "Segoe UI", "sans-serif"],
      },
      colors: {
        nlr: "#ff3355",
        mcb: "#3d8bfd",
        ink: "#070b14",
        verified: "#3ddc84",
      },
    },
  },
  plugins: [],
};
