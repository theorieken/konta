'use client';

import AddIcon from '@mui/icons-material/Add';
import Autocomplete from '@mui/material/Autocomplete';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import { useRef, useState } from 'react';

import { errorMessage } from '@base/api/client';
import { useCreateTagMutation, useDeleteTagMutation, useTagNamesQuery } from '@base/store/api';
import { useAppDispatch } from '@base/store/hooks';
import { pushToast } from '@base/store/uiSlice';
import type { Tag } from '@base/types';

interface TagEditorProps {
  reference: string;
  tags: Tag[];
  readOnly?: boolean;
}

/**
 * Tags work on every object – the backend addresses the target by
 * `{db_table}` + `{uuid}`, which is exactly the object reference.
 */
export function TagEditor({ reference, tags, readOnly = false }: TagEditorProps) {
  const dispatch = useAppDispatch();
  const [adding, setAdding] = useState(false);
  const [value, setValue] = useState('');
  const submitting = useRef(false);
  const { data: known } = useTagNamesQuery(undefined, { skip: !adding });
  const [createTag, { isLoading }] = useCreateTagMutation();
  const [deleteTag] = useDeleteTagMutation();

  const submit = async () => {
    if (submitting.current) return;
    const name = value.trim();
    if (!name) {
      setAdding(false);
      return;
    }
    submitting.current = true;
    try {
      await createTag({ name, target_reference: reference }).unwrap();
      setValue('');
      setAdding(false);
    } catch (caught) {
      dispatch(pushToast(errorMessage(caught), 'error'));
    } finally {
      submitting.current = false;
    }
  };

  return (
    <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
      {tags.map((tag) => (
        <Chip
          key={tag.id}
          size="small"
          label={tag.name}
          onDelete={readOnly ? undefined : () => deleteTag(tag.id)}
          sx={{
            bgcolor: tag.color || 'action.hover',
            color: tag.color ? '#fff' : 'text.secondary',
          }}
        />
      ))}

      {readOnly ? null : adding ? (
        <Autocomplete
          freeSolo
          size="small"
          openOnFocus
          options={known?.results ?? []}
          inputValue={value}
          onInputChange={(_event, next) => setValue(next)}
          onChange={(_event, next) => setValue(next ?? '')}
          sx={{ minWidth: 180 }}
          renderInput={(params) => (
            <TextField
              {...params}
              autoFocus
              placeholder="Tag"
              disabled={isLoading}
              onBlur={submit}
              onKeyDown={(event) => {
                if (event.key === 'Enter') { event.preventDefault(); void submit(); }
                if (event.key === 'Escape') { setValue(''); setAdding(false); }
              }}
            />
          )}
        />
      ) : (
        <Tooltip title="Tag hinzufügen">
          <IconButton size="small" onClick={() => setAdding(true)}>
            <AddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </Stack>
  );
}
