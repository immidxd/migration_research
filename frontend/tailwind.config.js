/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx,js,jsx,html}"],
  theme: {
    extend: {
      colors: {
        // Subtle academic palette — easy on the eyes for long sessions.
        sidebar: "#1f2430",
        panel: "#252b3a",
        accent: "#c9a96e",
      },
    },
  },
  plugins: [],
};
