'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';

import { objectPath } from '@base/lib/reference';
import { useAppDispatch, useAppSelector } from '@base/store/hooks';
import { closeObject, drawerBack, openObject } from '@base/store/uiSlice';

/**
 * The drawer is the app's default way of looking at an object: it opens over
 * the current page so the user never loses their place. "Maximise" navigates
 * to /objects/{reference}, which renders the very same ObjectDisplay.
 */
export function useObjectDrawer() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const reference = useAppSelector((state) => state.ui.drawerReference);
  const canGoBack = useAppSelector((state) => state.ui.drawerHistory.length > 0);

  const open = useCallback(
    (target: string) => dispatch(openObject(target)),
    [dispatch],
  );

  const close = useCallback(() => dispatch(closeObject()), [dispatch]);
  const back = useCallback(() => dispatch(drawerBack()), [dispatch]);

  const maximize = useCallback(() => {
    if (!reference) return;
    dispatch(closeObject());
    router.push(objectPath(reference));
  }, [dispatch, reference, router]);

  return { reference, isOpen: Boolean(reference), canGoBack, open, close, back, maximize };
}
