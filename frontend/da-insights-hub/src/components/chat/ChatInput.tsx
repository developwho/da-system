import { useState, useCallback, useRef } from 'react';
import { Send, Plus, Mic, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { dataApi } from '@/services/data-api';
import { config } from '@/lib/config';

interface ChatInputProps {
  onSend: (content: string, fileId?: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async () => {
    const content = input.trim();
    if (!content && attachedFiles.length === 0) return;

    let fileId: string | undefined;
    // 첫 번째 파일만 분석 (나머지는 업로드만)
    if (attachedFiles.length > 0) {
      setIsUploading(true);
      try {
        if (config.useMock) {
          fileId = `mock-file-${Date.now()}`;
        } else {
          // 모든 파일 업로드
          const uploadPromises = attachedFiles.map((file) => dataApi.uploadFile(file));
          const uploads = await Promise.all(uploadPromises);

          // 첫 번째 파일 ID를 분석용으로 사용
          fileId = uploads[0].file_id;

          if (uploads.length > 1) {
            console.log(`${uploads.length}개 파일 업로드됨. 첫 번째 파일 분석: ${attachedFiles[0].name}`);
          }
        }
      } catch (error) {
        alert('파일 업로드에 실패했습니다. 다시 시도해주세요.');
        setIsUploading(false);
        return;
      }
    }

    const fileNames = attachedFiles.map((f) => f.name).join(', ');
    onSend(content || `Analyze ${fileNames}`, fileId);
    setInput('');
    setAttachedFiles([]);
    setIsUploading(false);
  }, [input, attachedFiles, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length === 0) return;

      // 최대 5개 제한
      const currentCount = attachedFiles.length;
      const availableSlots = 5 - currentCount;

      if (availableSlots <= 0) {
        alert('최대 5개 파일까지 업로드할 수 있습니다.');
        if (fileInputRef.current) fileInputRef.current.value = '';
        return;
      }

      const validTypes = ['.csv', '.xlsx', '.xls'];
      const validFiles: File[] = [];
      const invalidFiles: string[] = [];

      files.slice(0, availableSlots).forEach((file) => {
        const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
        if (validTypes.includes(ext)) {
          validFiles.push(file);
        } else {
          invalidFiles.push(file.name);
        }
      });

      if (invalidFiles.length > 0) {
        alert(`다음 파일은 CSV/Excel 형식이 아닙니다:\n${invalidFiles.join('\n')}`);
      }

      if (validFiles.length > 0) {
        setAttachedFiles((prev) => [...prev, ...validFiles]);
      }

      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [attachedFiles.length]
  );

  const removeAttachment = useCallback((index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  return (
    <div className="space-y-2">
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
      <div className="flex items-center gap-2 rounded-full border border-border bg-card px-2 py-2">
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
          disabled={disabled || isUploading || attachedFiles.length >= 5}
        >
          <Plus className="h-5 w-5 text-muted-foreground" />
        </Button>

        {/* Text input */}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            attachedFiles.length >= 5
              ? '최대 5개 파일까지 첨부 가능'
              : '메시지를 입력하거나 파일을 첨부하세요...'
          }
          className={cn(
            'flex-1 bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted-foreground',
            'focus:outline-none'
          )}
          disabled={disabled || isUploading}
        />

        {/* Microphone button */}
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 shrink-0 rounded-full hover:bg-muted"
          disabled={disabled || isUploading}
        >
          <Mic className="h-5 w-5 text-muted-foreground" />
        </Button>

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
