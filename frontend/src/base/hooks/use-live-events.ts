'use client';

import { useEffect, useRef } from 'react';

import { websocketUrl } from '@base/api/client';
import { api } from '@base/store/api';
import { useAppDispatch, useAppSelector } from '@base/store/hooks';
import { pushToast, setLiveConnected } from '@base/store/uiSlice';
import type { LiveEvent } from '@base/types';

/** Which cache tags a change on a table has to invalidate. */
const TABLE_TAGS: Record<string, string[]> = {
  finance_account: ['Account', 'Dashboard'],
  finance_category: ['Category', 'Dashboard'],
  finance_transaction: ['Transaction', 'Dashboard', 'Account'],
  finance_contract: ['Contract', 'Transaction', 'Dashboard'],
  finance_loan: ['Loan', 'Transaction', 'Dashboard'],
  finance_job: ['Job', 'Transaction', 'Dashboard'],
  base_file: ['File'],
  base_household: ['Household', 'User'],
  base_setting: ['Setting'],
  base_tag: ['Tag'],
  users_user: ['User'],
};

/**
 * One WebSocket for the whole app.
 *
 * Celery does the heavy lifting in the background (CSV import, AI
 * classification, plan generation), so the UI learns about results through
 * this socket instead of polling. Reconnects with a capped backoff.
 */
export function useLiveEvents(enabled: boolean, householdId?: string): void {
  const dispatch = useAppDispatch();
  const token = useAppSelector((state) => state.auth.token);
  const socketRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const closedByUs = useRef(false);

  useEffect(() => {
    if (!enabled || !token || typeof window === 'undefined') return undefined;

    let reconnectTimer: ReturnType<typeof setTimeout>;
    let pingTimer: ReturnType<typeof setInterval>;
    closedByUs.current = false;

    const connect = () => {
      const url = websocketUrl('/events/');
      if (!url) return;

      let socket: WebSocket;
      try {
        socket = new WebSocket(url);
      } catch {
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        dispatch(setLiveConnected(true));
        pingTimer = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30_000);
      };

      socket.onmessage = (event) => {
        let payload: LiveEvent;
        try {
          payload = JSON.parse(event.data);
        } catch {
          return;
        }
        handleEvent(payload);
      };

      socket.onclose = () => {
        dispatch(setLiveConnected(false));
        clearInterval(pingTimer);
        if (closedByUs.current) return;
        attemptRef.current += 1;
        const delay = Math.min(1000 * 2 ** attemptRef.current, 30_000);
        reconnectTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => socket.close();
    };

    const handleEvent = (event: LiveEvent) => {
      switch (event.type) {
        case 'object.changed': {
          const tags = TABLE_TAGS[event.db_table] || ['Object'];
          dispatch(api.util.invalidateTags([
            ...tags,
            { type: 'Object' as const, id: event.object_reference },
          ] as never));
          break;
        }
        case 'import.finished': {
          dispatch(api.util.invalidateTags(['File', 'Transaction', 'Dashboard'] as never));
          dispatch(pushToast(
            `Import fertig: ${event.imported} Buchungen, ${event.duplicates} Duplikate übersprungen.`,
            'success',
          ));
          break;
        }
        case 'import.progress':
          dispatch(api.util.invalidateTags(['File'] as never));
          break;
        case 'import.analyzed':
          dispatch(api.util.invalidateTags(['File'] as never));
          dispatch(pushToast('Die Importprüfung ist fertig.', 'success'));
          break;
        case 'household.restored':
          dispatch(api.util.invalidateTags([
            'File', 'Transaction', 'Dashboard', 'Account', 'Category',
            'Contract', 'Loan', 'Job', 'Setting', 'Tag', 'Household', 'User',
          ] as never));
          dispatch(pushToast('Der Haushalt wurde vollständig wiederhergestellt.', 'success'));
          break;
        case 'plan.generated':
          if (event.created) {
            dispatch(api.util.invalidateTags(['Transaction', 'Dashboard'] as never));
          }
          break;
        case 'plan.matched':
          if (event.matched) {
            dispatch(api.util.invalidateTags(['Transaction', 'Dashboard'] as never));
          }
          break;
        case 'toast':
          dispatch(pushToast(event.message, event.severity));
          break;
        default:
          break;
      }
    };

    connect();

    return () => {
      closedByUs.current = true;
      clearTimeout(reconnectTimer);
      clearInterval(pingTimer);
      socketRef.current?.close();
      socketRef.current = null;
      dispatch(setLiveConnected(false));
    };
  }, [dispatch, enabled, householdId, token]);
}
