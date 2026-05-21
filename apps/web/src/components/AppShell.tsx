import { Tooltip, makeStyles, mergeClasses } from '@fluentui/react-components';
import {
  ArrowExit24Regular,
  ChartMultiple24Regular,
  Folder24Regular,
  Home24Regular,
  Rocket24Regular,
  Settings24Regular,
} from '@fluentui/react-icons';
import { useEffect, useState, type ReactNode } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';

import { getTeamsContext, looksLikeTeamsHost } from '@/lib/teams';

const NAV_WIDTH = '64px';
const TOPBAR_HEIGHT = '52px';

const useStyles = makeStyles({
  root: {
    display: 'grid',
    gridTemplateColumns: `${NAV_WIDTH} 1fr`,
    minHeight: '100vh',
    backgroundColor: 'var(--bg-0)',
    '@media (max-width: 720px)': {
      gridTemplateColumns: '1fr',
    },
  },
  nav: {
    borderRight: `1px solid var(--border-hairline)`,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '16px 0 12px',
    gap: '4px',
    backgroundColor: 'var(--bg-0)',
    position: 'sticky',
    top: 0,
    height: '100vh',
    '@media (max-width: 720px)': {
      display: 'none',
    },
  },
  brand: {
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    background: 'linear-gradient(135deg, #5b8def 0%, #3661cf 100%)',
    color: '#fff',
    fontSize: '18px',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '12px',
    letterSpacing: '-0.02em',
  },
  brandMark: {
    fontSize: '14px',
    fontWeight: 800,
    letterSpacing: '-0.04em',
  },
  navSection: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '2px',
    paddingTop: '8px',
    paddingBottom: '8px',
  },
  navDivider: {
    width: '24px',
    height: '1px',
    backgroundColor: 'var(--border-hairline)',
    margin: '4px 0',
  },
  navItem: {
    position: 'relative',
    width: '40px',
    height: '40px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-3)',
    cursor: 'pointer',
    transitionProperty: 'background-color, color, transform',
    transitionDuration: '120ms',
    ':hover': {
      backgroundColor: 'var(--bg-2)',
      color: 'var(--text-1)',
    },
  },
  navItemActive: {
    backgroundColor: 'var(--bg-2)',
    color: 'var(--accent)',
    '::before': {
      content: '""',
      position: 'absolute',
      left: '-12px',
      top: '8px',
      bottom: '8px',
      width: '2px',
      borderRadius: '2px',
      backgroundColor: 'var(--accent)',
    },
  },
  spacer: {
    flex: 1,
  },
  workspace: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100vh',
    minWidth: 0,
  },
  topbar: {
    height: TOPBAR_HEIGHT,
    borderBottom: `1px solid var(--border-hairline)`,
    backgroundColor: 'rgba(8, 8, 10, 0.75)',
    backdropFilter: 'saturate(140%) blur(12px)',
    WebkitBackdropFilter: 'saturate(140%) blur(12px)',
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    alignItems: 'center',
    gap: '20px',
    padding: '0 24px',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  crumbs: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '12px',
    color: 'var(--text-2)',
    minWidth: 0,
  },
  crumbBrand: {
    fontSize: '12px',
    fontWeight: 700,
    color: 'var(--text-1)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    textDecoration: 'none',
    transitionProperty: 'color',
    transitionDuration: '120ms',
    ':hover': { color: 'var(--accent)' },
  },
  crumbSep: {
    color: 'var(--text-4)',
  },
  crumbLink: {
    color: 'var(--text-2)',
    textDecoration: 'none',
    transitionProperty: 'color',
    transitionDuration: '120ms',
    ':hover': { color: 'var(--accent)' },
  },
  crumbCurrent: {
    color: 'var(--text-1)',
    fontWeight: 500,
  },
  user: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '12px',
    color: 'var(--text-2)',
  },
  envPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '3px 8px',
    borderRadius: '999px',
    border: '1px solid var(--border-default)',
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    color: 'var(--text-2)',
    fontFamily: 'var(--font-mono)',
  },
  envDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: 'var(--success)',
    boxShadow: '0 0 8px rgba(43, 196, 138, 0.5)',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    minWidth: 0,
  },
  mobileBar: {
    display: 'none',
    '@media (max-width: 720px)': {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-around',
      position: 'sticky',
      bottom: 0,
      borderTop: '1px solid var(--border-hairline)',
      backgroundColor: 'var(--bg-0)',
      padding: '8px',
      zIndex: 10,
    },
  },
  mobileItem: {
    width: '44px',
    height: '44px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-3)',
  },
  mobileItemActive: {
    color: 'var(--accent)',
    backgroundColor: 'var(--bg-2)',
  },
  // Teams Tab iframe 内で動いてる時の最小限 chrome (host 側に既に nav/header があるので
  // 自前の sidebar + topbar は省く)
  teamsRoot: {
    minHeight: '100vh',
    backgroundColor: 'var(--bg-0)',
    color: 'var(--text-1)',
  },
  teamsContent: {
    minHeight: '100vh',
    overflowY: 'auto',
    minWidth: 0,
  },
});

interface NavEntry {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
  external?: boolean;
}

const NAV_PRIMARY: NavEntry[] = [
  { to: '/', label: 'Home', icon: <Home24Regular />, end: true },
  { to: '/new', label: 'Dispatch Bot', icon: <Rocket24Regular /> },
  { to: '/groups', label: 'Groups', icon: <Folder24Regular /> },
  { to: '/insights', label: 'Insights', icon: <ChartMultiple24Regular /> },
];

const NAV_FOOTER: NavEntry[] = [
  {
    to: 'https://learn.microsoft.com/azure/communication-services/',
    label: 'Settings',
    icon: <Settings24Regular />,
    external: true,
  },
];

interface Crumb {
  label: string;
  to?: string;
  current: boolean;
}

function deriveCrumbs(pathname: string): Crumb[] {
  if (pathname === '/') return [{ label: 'Home', current: true }];
  if (pathname === '/insights') return [{ label: 'Insights', current: true }];
  if (pathname === '/new') return [{ label: 'Dispatch', current: true }];
  if (pathname === '/groups') return [{ label: 'Groups', current: true }];
  if (pathname.startsWith('/groups/')) {
    return [
      { label: 'Groups', to: '/groups', current: false },
      { label: 'Detail', current: true },
    ];
  }
  if (pathname.startsWith('/m/')) {
    if (pathname.endsWith('/join')) return [{ label: 'Join meeting', current: true }];
    return [
      { label: 'Sessions', to: '/', current: false },
      { label: 'Mission Control', current: true },
    ];
  }
  return [{ label: 'Helmsman', current: true }];
}

function NavItem({ entry, styles }: { entry: NavEntry; styles: ReturnType<typeof useStyles> }) {
  if (entry.external) {
    return (
      <Tooltip content={entry.label} relationship="label" positioning="after">
        <a
          href={entry.to}
          target="_blank"
          rel="noreferrer"
          className={styles.navItem}
          aria-label={entry.label}
        >
          {entry.icon}
        </a>
      </Tooltip>
    );
  }
  return (
    <Tooltip content={entry.label} relationship="label" positioning="after">
      <NavLink
        to={entry.to}
        end={entry.end}
        className={({ isActive }) =>
          mergeClasses(styles.navItem, isActive && styles.navItemActive)
        }
        aria-label={entry.label}
      >
        {entry.icon}
      </NavLink>
    </Tooltip>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const styles = useStyles();
  const location = useLocation();
  const navigate = useNavigate();
  const crumbs = deriveCrumbs(location.pathname);

  // Teams Tab 内検出 — UA / iframe 早期判定 + SDK の context で確定。
  // 早期判定の段階で hide することで CLS なし。SDK context 取得後に確定値で上書き。
  const [inTeamsTab, setInTeamsTab] = useState<boolean>(() => looksLikeTeamsHost());
  useEffect(() => {
    let cancelled = false;
    getTeamsContext().then((ctx) => {
      if (!cancelled) setInTeamsTab(ctx !== null);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (inTeamsTab) {
    // Teams ホスト側に既に sidebar + topbar が居るので chrome を全部省く。
    // content だけ最大化して埋め込み体験を整える。
    return (
      <div className={styles.teamsRoot}>
        <main className={styles.teamsContent}>{children}</main>
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <nav className={styles.nav} aria-label="primary">
        <div className={styles.brand} aria-label="Helmsman">
          <span className={styles.brandMark}>H</span>
        </div>

        <div className={styles.navSection}>
          {NAV_PRIMARY.map((entry) => (
            <NavItem key={entry.label} entry={entry} styles={styles} />
          ))}
        </div>

        <div className={styles.spacer} />

        <div className={styles.navSection}>
          {NAV_FOOTER.map((entry) => (
            <NavItem key={entry.label} entry={entry} styles={styles} />
          ))}
          <Tooltip content="Sign out" relationship="label" positioning="after">
            <a href="#" className={styles.navItem} aria-label="Sign out">
              <ArrowExit24Regular />
            </a>
          </Tooltip>
        </div>
      </nav>

      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <div className={styles.crumbs}>
            <Link to="/" className={styles.crumbBrand} aria-label="Overview に戻る">
              HELMSMAN
            </Link>
            <span className={styles.crumbSep}>/</span>
            {crumbs.map((c, i) => (
              <span key={`${c.label}-${i}`} style={{ display: 'inline-flex', gap: '8px' }}>
                {c.current ? (
                  <span className={styles.crumbCurrent}>{c.label}</span>
                ) : c.to ? (
                  <Link to={c.to} className={styles.crumbLink}>
                    {c.label}
                  </Link>
                ) : (
                  <span>{c.label}</span>
                )}
                {i < crumbs.length - 1 && <span className={styles.crumbSep}>/</span>}
              </span>
            ))}
          </div>

          <div className={styles.user}>
            <span className={styles.envPill}>
              <span className={styles.envDot} />
              PROD · westus2
            </span>
          </div>
        </header>

        <main className={styles.content}>{children}</main>

        {/* Mobile bottom nav */}
        <div className={styles.mobileBar}>
          {NAV_PRIMARY.map((entry) => (
            <a
              key={entry.label}
              className={mergeClasses(
                styles.mobileItem,
                location.pathname === entry.to && styles.mobileItemActive,
              )}
              onClick={() => navigate(entry.to)}
              aria-label={entry.label}
            >
              {entry.icon}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
