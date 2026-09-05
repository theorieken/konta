import Box from '@mui/material/Box';
import type { ReactNode } from 'react';

interface AuthPageProps {
  children: ReactNode;
  footer: ReactNode;
  maxWidth?: number;
}

/** Centers the auth card while keeping secondary navigation at the viewport edge. */
export function AuthPage({ children, footer, maxWidth = 400 }: AuthPageProps) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateRows: 'minmax(0, 1fr) auto minmax(0, 1fr)',
        minHeight: '100dvh',
        p: 2,
      }}
    >
      <Box sx={{ gridRow: 2, width: '100%', maxWidth, justifySelf: 'center' }}>
        {children}
      </Box>
      <Box component="footer" sx={{ gridRow: 3, alignSelf: 'end', justifySelf: 'center' }}>
        {footer}
      </Box>
    </Box>
  );
}
