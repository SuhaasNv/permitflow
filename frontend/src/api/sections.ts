import type { ApplicationView } from "./applications";
import { request } from "./client";

export function updateSection(
  id: string,
  key: string,
  data: Record<string, unknown>,
): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${id}/sections/${key}`, {
    method: "PATCH",
    body: data,
  });
}
