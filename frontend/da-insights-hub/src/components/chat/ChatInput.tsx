import { useState, useCallback, useRef } from 'react';
import { Send, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { dataApi } from '@/services/data-api';
import { config } from '@/lib/config';
import { toast } from 'sonner';

const VALID_EXTENSIONS = ['.csv', '.xlsx', '.xls'];
const MAX_FILES = 5;

/** Validates files and returns { valid, invalid } arrays */
export function validateFiles(files: File[]): { valid: File[]; invalid: string[] } {
  const valid: File[] = [];
  const invalid: string[] = [];
  for (const file of files) {
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
    if (VALID_EXTENSIONS.includes(ext)) {
      valid.push(file);
    } else {
      invalid.push(file.name);
    }
  }
  return { valid, invalid };
}

interface ChatInputProps {
  onSend: (content: string, fileId?: string) => void;
  disabled?: boolean;
  onFilesAdded?: (files: File[]) => void;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }, []);

  const handleSubmit = useCallback(async () => {
    const content = input.trim();
    if (!content && attachedFiles.length === 0) return;

    let fileId: string | undefined;
    if (attachedFiles.length > 0) {
      setIsUploading(true);
      try {
        if (config.useMock) {
          fileId = `mock-file-${Date.now()}`;
        } else {
          const uploadPromises = attachedFiles.map((file) => dataApi.uploadFile(file));
          const uploads = await Promise.all(uploadPromises);
          fileId = uploads[0].file_id;

          if (uploads.length > 1) {
            console.log(`${uploads.length}개 파일 업로드됨. 첫 번째 파일 분석: ${attachedFiles[0].name}`);
          }
        }
      } catch {
        toast.error('파일 업로드에 실패했습니다. 다시 시도해주세요.');
        setIsUploading(false);
        return;
      }
    }

    const fileNames = attachedFiles.map((f) => f.name).join(', ');
    onSend(content || `Analyze ${fileNames}`, fileId);
    setInput('');
    setAttachedFiles([]);
    setIsUploading(false);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input, attachedFiles, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const addValidatedFiles = useCallback((files: File[], availableSlots: number) => {
    const sliced = files.slice(0, availableSlots);
    const { valid, invalid } = validateFiles(sliced);

    if (invalid.length > 0) {
      toast.error(`지원하지 않는 형식: ${invalid.join(', ')}`);
    }
    if (valid.length > 0) {
      setAttachedFiles((prev) => [...prev, ...valid]);
    }
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length === 0) return;

      const availableSlots = MAX_FILES - attachedFiles.length;
      if (availableSlots <= 0) {
        toast.warning('최대 5개 파일까지 첨부 가능합니다.');
        if (fileInputRef.current) fileInputRef.current.value = '';
        return;
      }

      addValidatedFiles(files, availableSlots);

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [attachedFiles.length, addValidatedFiles]
  );

  const removeAttachment = useCallback((index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Expose a way to add files from drag-and-drop
  (ChatInput as any)._addFiles = (files: File[]) => {
    const availableSlots = MAX_FILES - attachedFiles.length;
    if (availableSlots <= 0) {
      toast.warning('최대 5개 파일까지 첨부 가능합니다.');
      return;
    }
    addValidatedFiles(files, availableSlots);
  };

  return (
    <div className="space-y-2">
      {/* Upload progress */}
      {isUploading && (
        <Progress className="h-1" />
      )}

      {/* Attached files preview */}
      {attachedFiles.length > 0 && (
        <div className="space-y-2">
          {attachedFiles.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2"
            >
              <Plus className="h-4 w-4 text-muted-foreground" />
              <span className="flex-1 truncate text-sm text-foreground">
                {file.name}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => removeAttachment(index)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          {attachedFiles.length > 1 && (
            <p className="text-xs text-muted-foreground px-2">
              {attachedFiles.length}개 파일 첨부됨. 첫 번째 파일이 분석됩니다.
            </p>
          )}
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-2 rounded-2xl border border-border bg-card px-2 py-2">
        {/* Add/attachment button */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 shrink-0 rounded-full hover:bg-muted"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isUploading || attachedFiles.length >= MAX_FILES}
        >
          <Plus className="h-5 w-5 text-muted-foreground" />
        </Button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          placeholder={
            attachedFiles.length >= MAX_FILES
              ? '최대 5개 파일까지 첨부 가능'
              : '메시지를 입력하세요... (Shift+Enter로 줄바꿈)'
          }
          className={cn(
            'flex-1 resize-none bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted-foreground',
            'focus:outline-none'
          )}
          style={{ maxHeight: '200px' }}
          disabled={disabled || isUploading}
        />

        {/* Send button */}
        <Button
          size="icon"
          className="h-10 w-10 shrink-0 rounded-full bg-foreground hover:bg-foreground/90"
          onClick={handleSubmit}
          disabled={disabled || isUploading || (!input.trim() && attachedFiles.length === 0)}
        >
          <Send className="h-4 w-4 text-background" />
        </Button>
      </div>
    </div>
  );
}
