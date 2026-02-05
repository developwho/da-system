import { useEffect } from 'react';
import { toast } from 'sonner';
import { ApiError } from '@/services/api-client';

/**
 * Show a toast when a React Query error is an ApiError.
 * Usage: useApiError(query.error)
 */
export function useApiError(error: Error | null) {
  useEffect(() => {
    if (!error) return;
    if (error instanceof ApiError) {
      if (error.status === 401) {
        toast.error('인증에 실패했습니다. API 키를 확인하세요.');
      } else if (error.status === 404) {
        toast.error('리소스를 찾을 수 없습니다.');
      } else {
        toast.error(error.detail || 'API 오류가 발생했습니다.');
      }
    } else {
      toast.error(error.message || '예기치 않은 오류가 발생했습니다.');
    }
  }, [error]);
}
