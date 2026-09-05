'use client';

import Stack from '@mui/material/Stack';
import { useMemo } from 'react';

import { Loading } from '@base/components/loading';
import { PageHeader } from '@base/components/page-header';
import { useSettingDefinitionsQuery } from '@base/store/api';
import type { SettingDefinition } from '@base/types';

import { MasterDataPanel } from './master-data-panel';
import { ProfilePanel } from './profile-panel';
import { SettingsGroup } from './settings-group';
import { UsersPanel } from './users-panel';

/** Groups in the order they should appear. Unknown groups are appended. */
const GROUP_ORDER = ['KI-Import', 'Planung', 'Haushalt', 'E-Mail'];

export default function SettingsPage() {
  const { data, isLoading } = useSettingDefinitionsQuery();

  const groups = useMemo(() => {
    const definitions = data?.results ?? [];
    const map = new Map<string, SettingDefinition[]>();
    definitions.forEach((definition) => {
      const list = map.get(definition.group) ?? [];
      list.push(definition);
      map.set(definition.group, list);
    });
    const known = GROUP_ORDER.filter((group) => map.has(group));
    const rest = Array.from(map.keys()).filter((group) => !GROUP_ORDER.includes(group));
    return [...known, ...rest].map((group) => ({ group, definitions: map.get(group)! }));
  }, [data]);

  if (isLoading) return <Loading height={320} />;

  return (
    <Stack spacing={2.5}>
      <PageHeader
        title="Einstellungen"
        subtitle="Planung, Stammdaten und Profil."
      />

      {groups.map(({ group, definitions }) => (
        <SettingsGroup key={group} title={group} definitions={definitions} />
      ))}

      <MasterDataPanel />

      <UsersPanel />

      <ProfilePanel />
    </Stack>
  );
}
