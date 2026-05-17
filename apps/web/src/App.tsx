import { makeStyles, tokens } from '@fluentui/react-components';
import { Outlet } from 'react-router-dom';

const useStyles = makeStyles({
  root: {
    minHeight: '100vh',
    backgroundColor: tokens.colorNeutralBackground1,
    color: tokens.colorNeutralForeground1,
    fontFamily: tokens.fontFamilyBase,
  },
});

export function App() {
  const styles = useStyles();
  return (
    <div className={styles.root}>
      <Outlet />
    </div>
  );
}
