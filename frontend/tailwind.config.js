// UI design system (shared/hub_ui_kit): preset + scan its components,
// otherwise their classes are missing from the build. Path like vite.config.js.
const hubUiSrc = process.env.HUB_UI_PATH || require('path').resolve(process.cwd(), '../../../shared/hub_ui_kit/src');

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  presets: [require(`${hubUiSrc}/theme/tailwind-preset.cjs`)],
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  `${hubUiSrc.replace(/\\/g, '/')}/**/*.{vue,js}`,
  ],
  theme: {
    screens: {
      'xs': '320px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
    extend: {
      colors: {
        'app-background': 'var(--app-background)',
        'app-card': 'var(--app-card)',
        'app-text-primary': 'var(--app-text-primary)',
        'app-text-secondary': 'var(--app-text-secondary)',
        'app-border': 'var(--app-border)',
        'app-header-bg': 'var(--app-header-bg)',
        'app-button-primary': 'var(--app-button-primary)',
        'app-button-primary-hover': 'var(--app-button-primary-hover)',
      },
      spacing: {
        'touch': '44px',
        'touch-lg': '56px',
      },
      minHeight: {
        'touch': '44px',
        'touch-lg': '56px',
      },
      padding: {
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
        'safe-left': 'env(safe-area-inset-left)',
        'safe-right': 'env(safe-area-inset-right)',
      },
    },
  },
  plugins: [],
}
