'use client';

import { useEffect } from 'react';

import styles from './primary-nav.module.css';

type MobileMoreSheetProps = {
  open: boolean;
  title?: string;
  onClose: () => void;
  children: React.ReactNode;
};

export function MobileMoreSheet({ open, title = 'More', onClose, children }: MobileMoreSheetProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className={styles.sheetBackdrop} role="presentation" onClick={onClose}>
      <section className={styles.sheet} role="dialog" aria-modal="true" aria-label={`${title} navigation`} onClick={(event) => event.stopPropagation()}>
        <div className={styles.sheetTitleRow}>
          <div className={styles.sheetTitle}>{title}</div>
          <button type="button" className={styles.sheetClose} onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
