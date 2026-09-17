import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteCv, getCv, uploadCv } from "@/api/client";
import { CvCard, type CvCardState } from "@/components/workspace/CvCard";

export function CvCardContainer() {
  const queryClient = useQueryClient();
  const cvQuery = useQuery({ queryKey: ["cv"], queryFn: getCv });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["cv"] });
  };

  const upload = useMutation({ mutationFn: uploadCv, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: deleteCv, onSuccess: invalidate });

  const failed = cvQuery.isError || upload.isError || remove.isError;
  const busy = cvQuery.isPending || upload.isPending || remove.isPending;

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
      errorMessage={failed ? "That CV could not be parsed. Try uploading it again." : null}
      onUpload={(filename) => upload.mutate(filename)}
      onReplace={(filename) => upload.mutate(filename)}
      onDelete={() => remove.mutate()}
      onRetry={() => {
        upload.reset();
        remove.reset();
        void cvQuery.refetch();
      }}
    />
  );
}
