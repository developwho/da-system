import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Search, Eye, BarChart3, MessageSquare, Trash2, FileSpreadsheet, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useFiles, useUploadFile, useDeleteFile } from '@/hooks/use-data';
import { useApp } from '@/contexts/AppContext';
import { chatApi } from '@/services/chat-api';
import { config } from '@/lib/config';
import { formatBytes, formatNumber } from '@/lib/mock-data';
import { toast } from 'sonner';
import type { FileStatus } from '@/types';

export default function DataPage() {
  const { data: files = [], isLoading } = useFiles();
  const uploadMutation = useUploadFile();
  const deleteMutation = useDeleteFile();
  const [search, setSearch] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { setActiveSession } = useApp();

  const filteredFiles = files.filter((file) =>
    file.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    if (selected.length === 0) return;

    let filesToUpload = selected;
    if (selected.length > 5) {
      toast.error('최대 5개 파일까지 업로드할 수 있습니다. 처음 5개만 업로드합니다.');
      filesToUpload = selected.slice(0, 5);
    }

    setIsUploading(true);
    for (const file of filesToUpload) {
      try {
        await uploadMutation.mutateAsync(file);
        toast.success(`${file.name} 업로드 완료`);
      } catch (err) {
        const message = err instanceof Error ? err.message : '알 수 없는 오류';
        toast.error(`업로드 실패: ${message}`);
      }
    }
    setIsUploading(false);
    e.target.value = '';
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => toast.success('파일이 삭제되었습니다'),
      onError: (err) => toast.error(`삭제 실패: ${err.message}`),
    });
  };

  const handleUseInChat = async (fileId: string) => {
    try {
      if (config.useMock) {
        setActiveSession(`mock-${fileId}`);
      } else {
        const session = await chatApi.createSession(fileId);
        setActiveSession(session.session_id);
      }
      navigate('/');
    } catch (err) {
      const message = err instanceof Error ? err.message : '알 수 없는 오류';
      toast.error(`채팅 세션 생성 실패: ${message}`);
    }
  };

  const getStatusBadge = (status: FileStatus) => {
    const variants: Record<FileStatus, { variant: 'default' | 'secondary' | 'destructive'; label: string }> = {
      ready: { variant: 'default', label: 'Ready' },
      processing: { variant: 'secondary', label: 'Processing' },
      uploading: { variant: 'secondary', label: 'Uploading' },
      error: { variant: 'destructive', label: 'Error' },
    };
    const { variant, label } = variants[status];
    return <Badge variant={variant}>{label}</Badge>;
  };

  const getProblemTypeBadge = (type: string | null) => {
    if (!type) return <span className="text-muted-foreground">—</span>;
    const labels: Record<string, string> = {
      binary_classification: 'Binary',
      multiclass_classification: 'Multiclass',
      regression: 'Regression',
    };
    return (
      <Badge variant="outline" className="text-xs">
        {labels[type] || type}
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">데이터 파일</h1>
            <p className="text-sm text-muted-foreground">
              업로드된 데이터셋을 관리합니다
            </p>
          </div>
          <Button
            className="gap-2"
            onClick={handleUploadClick}
            disabled={uploadMutation.isPending || isUploading}
          >
            {uploadMutation.isPending || isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            파일 업로드
          </Button>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="파일 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Files table */}
        {filteredFiles.length > 0 ? (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Rows</TableHead>
                    <TableHead>Columns</TableHead>
                    <TableHead>Problem Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFiles.map((file) => (
                    <TableRow key={file.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{file.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatBytes(file.size)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatNumber(file.rows)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {file.columns != null ? file.columns : '—'}
                      </TableCell>
                      <TableCell>{getProblemTypeBadge(file.problemType)}</TableCell>
                      <TableCell>{getStatusBadge(file.status)}</TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              Actions
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Eye className="mr-2 h-4 w-4" />
                              Preview
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <BarChart3 className="mr-2 h-4 w-4" />
                              Profile
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleUseInChat(file.id)}>
                              <MessageSquare className="mr-2 h-4 w-4" />
                              Use in Chat
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => handleDelete(file.id)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ) : (
          <EmptyState hasSearch={!!search} onUpload={handleUploadClick} />
        )}
      </div>
    </div>
  );
}

function EmptyState({ hasSearch, onUpload }: { hasSearch: boolean; onUpload: () => void }) {
  return (
    <Card className="border-dashed">
      <CardHeader className="items-center pb-2">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <FileSpreadsheet className="h-8 w-8 text-muted-foreground" />
        </div>
        <CardTitle className="text-lg">
          {hasSearch ? '파일을 찾을 수 없습니다' : '데이터 파일이 없습니다'}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-center">
        <p className="mb-4 text-sm text-muted-foreground">
          {hasSearch
            ? '다른 검색어를 시도해보세요'
            : '분석을 시작하려면 데이터셋을 업로드하세요'}
        </p>
        {!hasSearch && (
          <Button className="gap-2" onClick={onUpload}>
            <Upload className="h-4 w-4" />
            파일 업로드
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
