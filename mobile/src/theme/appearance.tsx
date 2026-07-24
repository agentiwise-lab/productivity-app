/**
 * Dark, light, or whatever the phone is doing.
 *
 * Dark is the default rather than the system's choice, because the product is a
 * near-black canvas with one luminous category hue per row and that is what it
 * was designed as. A user who prefers light says so once, in You, and it is
 * remembered.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useColorScheme } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Mode } from './primitives';

export type Appearance = 'dark' | 'light' | 'system';

const KEY = 'appearance.v1';

interface Value {
  /** What the user chose. */
  appearance: Appearance;
  /** What that resolves to right now. */
  mode: Mode;
  setAppearance: (next: Appearance) => void;
}

const Context = createContext<Value>({
  appearance: 'dark',
  mode: 'dark',
  setAppearance: () => {},
});

export function AppearanceProvider({ children }: { children: React.ReactNode }) {
  const system = useColorScheme();
  const [appearance, setStored] = useState<Appearance>('dark');

  useEffect(() => {
    void AsyncStorage.getItem(KEY).then((saved) => {
      if (saved === 'dark' || saved === 'light' || saved === 'system') {
        setStored(saved);
      }
    });
  }, []);

  const setAppearance = useCallback((next: Appearance) => {
    setStored(next);
    void AsyncStorage.setItem(KEY, next);
  }, []);

  const value = useMemo<Value>(() => {
    const mode: Mode =
      appearance === 'system' ? (system === 'light' ? 'light' : 'dark') : appearance;
    return { appearance, mode, setAppearance };
  }, [appearance, system, setAppearance]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAppearance(): Value {
  return useContext(Context);
}
