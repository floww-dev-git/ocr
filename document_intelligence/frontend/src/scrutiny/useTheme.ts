import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "di.theme";
const THEME_ATTRIBUTE = "data-theme";

function readInitialTheme(): Theme {
  const stored = safeReadStored();
  if (stored !== null) {
    return stored;
  }
  // Light by default, as the prototype does (`localStorage.getItem('di-theme') ||
  // 'light'`) — it does not follow the OS. Matching that is part of reflecting the
  // prototype's theme exactly; the toggle still lets an officer pick dark.
  return "light";
}

function safeReadStored(): Theme | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : null;
  } catch {
    // Private browsing can refuse storage; the preference is not worth failing over.
    return null;
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute(THEME_ATTRIBUTE, theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // See safeReadStored.
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  }, []);

  return { theme, toggleTheme };
}
