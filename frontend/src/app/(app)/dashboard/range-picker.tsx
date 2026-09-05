'use client';

import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import TuneIcon from '@mui/icons-material/Tune';
import { useState } from 'react';

import { addMonths, endOfMonth, startOfMonth } from '@base/lib/format';
import { setRange } from '@base/store/uiSlice';
import { useAppDispatch, useAppSelector } from '@base/store/hooks';

const PRESETS: { label: string; months: number }[] = [
  { label: '6 Monate', months: 6 },
  { label: '12 Monate', months: 12 },
  { label: '24 Monate', months: 24 },
  { label: '36 Monate', months: 36 },
];

/** From/until for the whole dashboard – kept in Redux so it survives navigation. */
export function RangePicker() {
  const dispatch = useAppDispatch();
  const from = useAppSelector((state) => state.ui.dateFrom);
  const until = useAppSelector((state) => state.ui.dateUntil);
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);
  const [custom, setCustom] = useState(false);

  const currentPreset = PRESETS.find((preset) => {
    const start = startOfMonth();
    return from === start && until === endOfMonth(addMonths(start, preset.months - 1));
  });

  const applyPreset = (months: number) => {
    const start = startOfMonth();
    dispatch(setRange({ from: start, until: endOfMonth(addMonths(start, months - 1)) }));
    setCustom(false);
    setAnchor(null);
  };

  const showCustom = () => {
    setCustom(true);
    setAnchor(null);
  };

  return (
    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
      <Button
        size="small"
        color="inherit"
        startIcon={<TuneIcon />}
        onClick={(event) => setAnchor(event.currentTarget)}
      >
        {custom ? 'Benutzerdefiniert' : currentPreset?.label ?? 'Zeitraum'}
      </Button>
      {custom ? (
        <>
          <TextField
            type="date"
            label="Von"
            value={from}
            sx={{ width: { xs: 145, sm: 152 } }}
            onChange={(event) => dispatch(setRange({ from: event.target.value }))}
          />
          <TextField
            type="date"
            label="Bis"
            value={until}
            sx={{ width: { xs: 145, sm: 152 } }}
            onChange={(event) => dispatch(setRange({ until: event.target.value }))}
          />
        </>
      ) : null}
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {PRESETS.map((preset) => (
          <MenuItem key={preset.months} onClick={() => applyPreset(preset.months)}>
            {preset.label}
          </MenuItem>
        ))}
        <Divider />
        <MenuItem onClick={showCustom}>Benutzerdefiniert</MenuItem>
      </Menu>
    </Stack>
  );
}
