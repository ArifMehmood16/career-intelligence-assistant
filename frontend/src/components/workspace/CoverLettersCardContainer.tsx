import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteCoverLetter,
  getCoverLetters,
  uploadCoverLetter,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import {
  CoverLettersCard,
  type CoverLettersCardState,
} from "@/components/workspace/CoverLettersCard";

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
  const failure = upload.error ?? remove.error ?? listQuery.error;
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
        failed ? formatDescribedError(describeApiError(failure)) : null
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
