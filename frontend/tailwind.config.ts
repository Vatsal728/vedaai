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
        veda: {
          orange: "#FF6B2C",
          peach: "#FFEDE0",
          bg: "#F6F5F5",
          card: "#FFFFFF",
          muted: "#9CA3AF",
          dark: "#1F1F1F",
          sidebar: "#FFFFFF",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      }
    },
  },
  plugins: [],
};
export default config;
