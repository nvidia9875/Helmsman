import { create } from 'zustand';

interface IdentityState {
  userId: string;
  displayName: string;
  setName: (name: string) => void;
}

function generateUserId(): string {
  return 'u-' + crypto.randomUUID().slice(0, 12);
}

function loadInitial(): { userId: string; displayName: string } {
  if (typeof window === 'undefined') {
    return { userId: 'u-anonymous', displayName: 'Anonymous' };
  }
  const cached = window.localStorage.getItem('helmsman.identity');
  if (cached) {
    try {
      return JSON.parse(cached);
    } catch {
      /* fallthrough */
    }
  }
  const fresh = { userId: generateUserId(), displayName: 'Anonymous' };
  window.localStorage.setItem('helmsman.identity', JSON.stringify(fresh));
  return fresh;
}

export const useIdentity = create<IdentityState>((set) => ({
  ...loadInitial(),
  setName: (displayName: string) =>
    set((s) => {
      const next = { ...s, displayName };
      window.localStorage.setItem(
        'helmsman.identity',
        JSON.stringify({ userId: next.userId, displayName: next.displayName }),
      );
      return next;
    }),
}));
