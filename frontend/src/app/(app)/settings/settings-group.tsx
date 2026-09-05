'use client';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControlLabel from '@mui/material/FormControlLabel';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import TextField from '@mui/material/TextField';
import { useEffect, useState } from 'react';

import { Section } from '@base/components/section';
import { useSaveSettingsMutation } from '@base/store/api';
import { useAppDispatch } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';
import type { SettingDefinition } from '@base/types';

interface SettingsGroupProps {
  title: string;
  definitions: SettingDefinition[];
}

/**
 * Renders one settings group straight from the backend's definition list –
 * adding a setting on the server makes it appear here without frontend work.
 */
export function SettingsGroup({ title, definitions }: SettingsGroupProps) {
  const dispatch = useAppDispatch();
  const [saveSettings, { isLoading }] = useSaveSettingsMutation();
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    const next: Record<string, unknown> = {};
    definitions.forEach((definition) => {
      next[definition.key] = definition.is_secret ? '' : (definition.value ?? '');
    });
    setDraft(next);
    setDirty(false);
  }, [definitions]);

  const change = (key: string, value: unknown) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setDirty(true);
  };

  const save = async () => {
    // Never send an untouched secret – that would wipe a stored key.
    const payload = Object.fromEntries(
      Object.entries(draft).filter(([key, value]) => {
        const definition = definitions.find((entry) => entry.key === key);
        if (definition?.is_secret) return value !== '';
        return true;
      }),
    );
    try {
      await saveSettings(payload).unwrap();
      dispatch(pushToast('Einstellungen gespeichert.', 'success'));
      setDirty(false);
    } catch {
      dispatch(pushToast('Speichern fehlgeschlagen.', 'error'));
    }
  };

  return (
    <Section
      title={title}
      action={
        <Button size="small" variant="contained" disabled={!dirty || isLoading} onClick={save}>
          Speichern
        </Button>
      }
    >
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
        }}
      >
        {definitions.map((definition) => {
          const value = draft[definition.key];

          if (definition.value_type === 'boolean') {
            return (
              <Box key={definition.key} sx={{ alignSelf: 'center' }}>
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={Boolean(value)}
                      onChange={(event) => change(definition.key, event.target.checked)}
                    />
                  }
                  label={definition.label}
                />
              </Box>
            );
          }

          if (definition.choices?.length) {
            return (
              <TextField
                key={definition.key}
                select
                label={definition.label}
                value={(value as string) ?? ''}
                helperText={definition.description}
                onChange={(event) => change(definition.key, event.target.value)}
              >
                {definition.choices.map((choice) => (
                  <MenuItem key={choice} value={choice}>{choice}</MenuItem>
                ))}
              </TextField>
            );
          }

          return (
            <TextField
              key={definition.key}
              label={definition.label}
              autoComplete={
                definition.is_secret
                  ? 'new-password'
                  : definition.key === 'email_host_user'
                    ? 'off'
                    : undefined
              }
              type={
                definition.is_secret
                  ? 'password'
                  : definition.value_type === 'number'
                    ? 'number'
                    : definition.value_type === 'date'
                      ? 'date'
                      : 'text'
              }
              value={(value as string) ?? ''}
              placeholder={definition.is_secret && definition.is_set ? '•••••••• gespeichert' : ''}
              helperText={definition.description}
              slotProps={{
                inputLabel: definition.value_type === 'date' ? { shrink: true } : undefined,
              }}
              onChange={(event) => change(definition.key, event.target.value)}
            />
          );
        })}
      </Box>
    </Section>
  );
}
