import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  deleteCoverLetter,
  getCoverLetters,
  uploadCoverLetter,
} from "@/api/client";
import {
  CoverLettersCard,
  type CoverLettersCardState,
} from "@/components/workspace/CoverLettersCard";

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function CoverLettersCardContainer() {
  const queryClient = useQueryClient();
  const listQuery = useQuery({
    queryKey: ["cover-letters"],
    queryFn: getCoverLetters,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["cover-letters"] });
  };

  const upload = useMutation({
    mutationFn: uploadCoverLetter,
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: deleteCoverLetter,
    onSuccess: invalidate,
  });

  const failed = listQuery.isError || upload.isError || remove.isError;
  const state: CoverLettersCardState = failed
    ? "error"
    : listQuery.isPending
      ? "loading"
      : "ready";

  return (
    <CoverLettersCard
      state={state}
      documents={listQuery.data ?? []}
      errorMessage={
        failed
          ? errorMessage(
              upload.error ?? remove.error ?? listQuery.error,
              "Cover letters could not be loaded.",
            )
          : null
      }
      uploading={upload.isPending}
      onUpload={(file) => upload.mutate(file)}
      onDelete={(id) => remove.mutate(id)}
      onRetry={() => {
        upload.reset();
        remove.reset();
        void listQuery.refetch();
      }}
    />
  );
}
