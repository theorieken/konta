'use client';

import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import LogoutIcon from '@mui/icons-material/Logout';
import AccountBalanceWalletOutlinedIcon from '@mui/icons-material/AccountBalanceWalletOutlined';
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import FileUploadOutlinedIcon from '@mui/icons-material/FileUploadOutlined';
import AddIcon from '@mui/icons-material/Add';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Button from '@mui/material/Button';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

import { useAppDispatch, useAppSelector } from '@base/store/hooks';
import { setThemeMode, toggleSidebar } from '@base/store/uiSlice';
import {
  useActivateHouseholdMutation,
  useCreateHouseholdMutation,
  useHouseholdsQuery,
} from '@base/store/api';

export const SIDEBAR_WIDTH = 220;

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: DashboardOutlinedIcon },
  { href: '/expenses', label: 'Ausgaben', icon: ReceiptLongOutlinedIcon },
  { href: '/income', label: 'Einnahmen', icon: AccountBalanceWalletOutlinedIcon },
  { href: '/import', label: 'Import', icon: FileUploadOutlinedIcon },
  { href: '/settings', label: 'Einstellungen', icon: SettingsOutlinedIcon },
];

interface SidebarProps {
  householdName: string;
  householdId: string | null;
  onLogout: () => void;
}

export function Sidebar({ householdName, householdId, onLogout }: SidebarProps) {
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);
  const themeMode = useAppSelector((state) => state.ui.themeMode);
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const { data: households } = useHouseholdsQuery();
  const [activate] = useActivateHouseholdMutation();
  const [createHousehold] = useCreateHouseholdMutation();

  const isDark = themeMode === 'dark';

  return (
    <Stack sx={{ height: '100%', px: 1.5, py: 2.25 }}>
      <Typography variant="h1" sx={{ px: 1, mb: 1.25, fontSize: 24 }}>
        Finanzen
      </Typography>
      <Stack direction="row" spacing={0.5} alignItems="center" sx={{ px: 0.5, mb: 2.5 }}>
        <TextField
          select
          variant="standard"
          value={householdId ?? ''}
          aria-label="Haushalt wechseln"
          fullWidth
          onChange={(event) => void activate(event.target.value)}
          slotProps={{ input: { disableUnderline: true } }}
          sx={{ '& .MuiSelect-select': { fontSize: 14, fontWeight: 600, py: 0.5, px: 0.5 } }}
        >
          {(households?.results ?? []).map((household) => (
            <MenuItem key={household.id} value={household.id}>{household.name}</MenuItem>
          ))}
          {!householdId ? <MenuItem value="">{householdName}</MenuItem> : null}
        </TextField>
        <Tooltip title="Haushalt hinzufügen">
          <IconButton size="small" onClick={() => setCreateOpen(true)}>
            <AddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Navigation */}
      <List disablePadding sx={{ flexGrow: 1 }}>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <ListItemButton
              key={href}
              component={Link}
              href={href}
              selected={active}
              onClick={() => dispatch(toggleSidebar(false))}
              sx={{
                position: 'relative',
                minHeight: 42,
                px: 1.25,
                borderRadius: 1.5,
                mb: 0.5,
                color: active ? 'text.primary' : 'text.secondary',
                '&.Mui-selected': { bgcolor: 'action.selected' },
                '&.Mui-selected:hover': { bgcolor: 'action.selected' },
                '&.Mui-selected::before': {
                  content: '""',
                  position: 'absolute',
                  left: 0,
                  width: 2,
                  height: 18,
                  borderRadius: 2,
                  bgcolor: 'primary.main',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>
                <Icon sx={{ fontSize: 19 }} />
              </ListItemIcon>
              <ListItemText
                primary={label}
                slotProps={{
                  primary: { fontSize: 14, fontWeight: active ? 600 : 450 },
                }}
              />
            </ListItemButton>
          );
        })}
      </List>

      <Divider sx={{ my: 1.5 }} />

      {/* User */}
      <Stack direction="row" alignItems="center" spacing={1} sx={{ px: 0.5 }}>
        <Avatar
          sx={{
            width: 28, height: 28, fontSize: 12, fontWeight: 600,
            bgcolor: user?.color || 'primary.main',
          }}
        >
          {user?.initials ?? '?'}
        </Avatar>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="body2" noWrap>{user?.display_name ?? '–'}</Typography>
        </Box>
        <Tooltip title={isDark ? 'Helles Design' : 'Dunkles Design'}>
          <IconButton
            size="small"
            onClick={() => dispatch(setThemeMode(isDark ? 'light' : 'dark'))}
          >
            {isDark ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
          </IconButton>
        </Tooltip>
        <Tooltip title="Abmelden">
          <IconButton size="small" onClick={onLogout}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Haushalt hinzufügen</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Name"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button color="inherit" onClick={() => setCreateOpen(false)}>Abbrechen</Button>
          <Button
            variant="contained"
            disabled={!newName.trim()}
            onClick={async () => {
              const created = await createHousehold({ name: newName.trim() }).unwrap();
              await activate(created.id).unwrap();
              setNewName('');
              setCreateOpen(false);
            }}
          >
            Hinzufügen
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
