'use client';

import { useEffect, useState } from 'react';

type Theme = 'dark' | 'light';

const STORAGE_KEY = 'xclaw_theme';

function setTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12.79A9 9 0 1 1 11.21 3c-.02.25-.03.51-.03.77A7 7 0 0 0 18.23 10.8c.26 0 .52-.01.77-.03z" />
    </svg>
  );
}

type ThemeToggleProps = {
  className?: string;
};

export function ThemeToggle({ className }: ThemeToggleProps) {
  const [theme, setThemeState] = useState<Theme>('dark');

  useEffect(() => {
    const persisted = window.localStorage.getItem(STORAGE_KEY);
    if (persisted === 'light' || persisted === 'dark') {
      setThemeState(persisted);
      setTheme(persisted);
      return;
    }

    setTheme('dark');
  }, []);

  const nextTheme = theme === 'dark' ? 'light' : 'dark';

  return (
    <button
      type="button"
      className={className ?? 'theme-toggle'}
      onClick={() => {
        setThemeState(nextTheme);
        setTheme(nextTheme);
        window.localStorage.setItem(STORAGE_KEY, nextTheme);
      }}
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
    >
      <span aria-hidden="true">{theme === 'dark' ? <SunIcon /> : <MoonIcon />}</span>
      <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
    </button>
  );
}
