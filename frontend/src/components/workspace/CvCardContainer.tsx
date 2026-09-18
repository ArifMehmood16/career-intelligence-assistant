import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteCv, getCv, uploadCv } from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import { CvCard, type CvCardState } from "@/components/workspace/CvCard";

export function CvCardContainer() {
  const queryClient = useQueryClient();
  const cvQuery = useQuery({ queryKey: ["cv"], queryFn: getCv });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["cv"] });
    void queryClient.invalidateQueries({ queryKey: ["roles"] });
  };

  const upload = useMutation({ mutationFn: uploadCv, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: deleteCv, onSuccess: invalidate });

  const failed = cvQuery.isError || upload.isError || remove.isError;
  const busy = cvQuery.isPending || upload.isPending || remove.isPending;
  const failure = upload.error ?? remove.error ?? cvQuery.error;

  const state: CvCardState = failed
    ? "error"
    : busy
      ? "parsing"
      : cvQuery.data
        ? "parsed"
        : "empty";

  return (
    <CvCard
      state={state}
      document={cvQuery.data ?? null}
      errorMessage={
        failed ? formatDescribedError(describeApiError(failure)) : null
      }
      onUpload={(file) => upload.mutate(file)}
      onReplace={(file) => upload.mutate(file)}
      onDelete={() => remove.mutate()}
      onRetry={() => {
        upload.reset();
        remove.reset();
        void cvQuery.refetch();
      }}
    />
  );
}
