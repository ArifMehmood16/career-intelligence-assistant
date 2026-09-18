/**
 * Phase 13.1 — Fit / Gaps / Prepare / Letter tabs for a role.
 * Presentational: value and panels are owned by the container (deep-link).
 */
import type { ReactNode } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  isRoleDetailTabId,
  ROLE_DETAIL_TABS,
  type RoleDetailTabId,
} from "@/components/role/role-detail-tabs";

export interface RoleDetailTabsProps {
  value: RoleDetailTabId;
  onValueChange: (value: RoleDetailTabId) => void;
  fit: ReactNode;
  gaps: ReactNode;
  prepare: ReactNode;
  letter: ReactNode;
}

export function RoleDetailTabs({
  value,
  onValueChange,
  fit,
  gaps,
  prepare,
  letter,
}: RoleDetailTabsProps) {
  return (
    <Tabs
      value={value}
      onValueChange={(next) => {
        if (isRoleDetailTabId(next)) {
          onValueChange(next);
        }
      }}
    >
      <TabsList aria-label="Role detail sections">
        {ROLE_DETAIL_TABS.map((tab) => (
          <TabsTrigger key={tab.id} value={tab.id}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      <TabsContent value="fit">{fit}</TabsContent>
      <TabsContent value="gaps">{gaps}</TabsContent>
      <TabsContent value="prepare">{prepare}</TabsContent>
      <TabsContent value="letter">{letter}</TabsContent>
    </Tabs>
  );
}
