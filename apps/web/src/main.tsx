import { FluentProvider } from '@fluentui/react-components';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import { App } from './App';
import { CreateMeeting } from './pages/CreateMeeting';
import { GroupDetail } from './pages/GroupDetail';
import { Groups } from './pages/Groups';
import { JoinMeeting } from './pages/JoinMeeting';
import { Landing } from './pages/Landing';
import { MeetingRoom } from './pages/MeetingRoom';
import './styles/global.css';
import { helmsmanDarkTheme } from './styles/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000,
      refetchOnWindowFocus: false,
    },
  },
});

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Landing /> },
      { path: 'new', element: <CreateMeeting /> },
      { path: 'm/:meetingId', element: <MeetingRoom /> },
      { path: 'm/:meetingId/join', element: <JoinMeeting /> },
      { path: 'groups', element: <Groups /> },
      { path: 'groups/:groupId', element: <GroupDetail /> },
    ],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <FluentProvider theme={helmsmanDarkTheme}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </FluentProvider>
  </StrictMode>,
);
