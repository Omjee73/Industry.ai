import React, { useEffect } from 'react';

interface ToastProps {
  message: string;
  onClose: () => void;
}

/** Small bottom-right notification for uploads, saves and inspections. */
export default function Toast({ message, onClose }: ToastProps) {
  useEffect(() => {
    const t = setTimeout(onClose, 3200);
    return () => clearTimeout(t);
  }, [message, onClose]);
  return (
    <div className="animate-fadeIn fixed bottom-4 right-4 z-50 max-w-md rounded-xl border border-border bg-panel px-4 py-3 text-sm text-fg shadow-xl">
      {message}
    </div>
  );
}
