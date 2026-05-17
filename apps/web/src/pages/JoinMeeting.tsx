import { Body1, Button, Field, Input, Title2, makeStyles } from '@fluentui/react-components';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { useIdentity } from '@/lib/store';

const useStyles = makeStyles({
  root: {
    maxWidth: '480px',
    margin: '80px auto',
    padding: '32px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
});

export function JoinMeeting() {
  const styles = useStyles();
  const { meetingId } = useParams<{ meetingId: string }>();
  const navigate = useNavigate();
  const { displayName, setName } = useIdentity();
  const [name, setNameLocal] = useState(displayName === 'Anonymous' ? '' : displayName);

  return (
    <div className={styles.root}>
      <Title2>会議に参加する</Title2>
      <Body1>会議 ID: {meetingId}</Body1>
      <Field label="あなたの表示名" required>
        <Input value={name} onChange={(_, d) => setNameLocal(d.value)} placeholder="例: 田中" />
      </Field>
      <Button
        appearance="primary"
        size="large"
        disabled={!name.trim() || !meetingId}
        onClick={() => {
          setName(name);
          navigate(`/m/${meetingId}`);
        }}
      >
        参加する
      </Button>
    </div>
  );
}
