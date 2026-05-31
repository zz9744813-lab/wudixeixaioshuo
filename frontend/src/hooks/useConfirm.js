import { useCallback, useState } from 'react';

export function useConfirm(message = '确认执行该操作？', title = '请确认') {
  const [open, setOpen] = useState(false);
  const [resolver, setResolver] = useState(null);
  const [meta, setMeta] = useState({ message, title });

  const confirm = useCallback(
    (opts = {}) => {
      const m = { message: opts.message ?? message, title: opts.title ?? title };
      setMeta(m);
      setOpen(true);
      return new Promise((resolve) => {
        setResolver(() => resolve);
      });
    },
    [message, title],
  );

  const handleOk = useCallback(() => {
    setOpen(false);
    if (resolver) resolver(true);
  }, [resolver]);

  const handleCancel = useCallback(() => {
    setOpen(false);
    if (resolver) resolver(false);
  }, [resolver]);

  return { confirm, state: { open, ...meta }, handleOk, handleCancel };
}
