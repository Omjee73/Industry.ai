import React, { useRef, useState } from 'react';
import { FileUp, Loader2 } from 'lucide-react';

interface UploadCardProps {
  title: string;
  subtitle?: string;
  onFile: (file: File) => void;
  busy?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  className?: string;
}

/** Drag-and-drop upload card used for the reference and test images. */
export default function UploadCard({
  title,
  subtitle,
  onFile,
  busy = false,
  disabled = false,
  icon,
  className = '',
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const pick = (file: File | undefined) => {
    if (file) onFile(file);
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => { e.preventDefault(); setDragOver(false); pick(e.dataTransfer.files[0]); }}
      className={`group cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors sm:p-8 ${
        dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-muted'
      } ${busy ? 'cursor-wait opacity-90' : ''} ${className}`}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = '';
        }}
      />
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-panel-elevated">
        {icon ?? <FileUp className="h-6 w-6 text-muted" />}
      </div>
      <p className="text-base font-semibold text-fg">{title}</p>
      {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      {busy && <Loader2 className="mx-auto mt-3 h-5 w-5 animate-spin text-muted" />}
    </div>
  );
}
