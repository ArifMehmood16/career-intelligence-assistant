import {
  breakdownFixture,
  cvFixture,
  messagesFixture,
  providerChoiceFixture,
  providersFixture,
  requirementsFixture,
  rolesFixture,
} from "./fixtures";
import type {
  BreakdownRow,
  ChatMessage,
  CvDocument,
  Provider,
  ProviderChoice,
  Requirement,
  Role,
} from "@/types";

const LATENCY_MS = 400;

const delay = <T>(value: T): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS));

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

let cv: CvDocument | null = clone(cvFixture);
let roles: Role[] = clone(rolesFixture);
const requirements: Requirement[] = clone(requirementsFixture);
let messages: ChatMessage[] = clone(messagesFixture);
let providerChoice: ProviderChoice = clone(providerChoiceFixture);

export function getCv(): Promise<CvDocument | null> {
  return delay(cv ? clone(cv) : null);
}

export function uploadCv(filename: string): Promise<CvDocument> {
  cv = {
    id: `cv-${Date.now()}`,
    filename,
    pageCount: cvFixture.pageCount,
    parsedAt: new Date().toISOString(),
  };
  return delay(clone(cv));
}

export function deleteCv(): Promise<void> {
  cv = null;
  return delay(undefined);
}

export function getRoles(): Promise<Role[]> {
  return delay(clone(roles));
}

export function getRole(id: string): Promise<Role | null> {
  return delay(clone(roles.find((role) => role.id === id) ?? null));
}

export function getRequirements(roleId: string): Promise<Requirement[]> {
  return delay(clone(requirements.filter((req) => req.roleId === roleId)));
}

export function getFitBreakdown(roleId: string): Promise<BreakdownRow[]> {
  return delay(clone(breakdownFixture[roleId] ?? []));
}

export function addRole(input: {
  title: string;
  company: string;
  description: string;
}): Promise<Role> {
  const role: Role = {
    id: `role-${Date.now()}`,
    title: input.title,
    company: input.company,
    fitScore: 0,
    bandLabel: "Not scored yet",
    counts: { met: 0, partial: 0, missing: 0 },
  };
  roles = [...roles, role];
  return delay(clone(role));
}

export function getMessages(): Promise<ChatMessage[]> {
  return delay(clone(messages));
}

export function sendMessage(content: string): Promise<ChatMessage[]> {
  const userMessage: ChatMessage = {
    id: `msg-${Date.now()}`,
    author: "user",
    content,
    kind: "answer",
    citations: [],
    model: null,
    provider: null,
  };
  const reply: ChatMessage = {
    id: `msg-${Date.now() + 1}`,
    author: "assistant",
    content: "The CV does not contain enough information to answer that.",
    kind: "insufficient",
    citations: [],
    model: providerChoice.answerModel,
    provider: providerChoice.answerProviderId,
  };
  messages = [...messages, userMessage, reply];
  return delay(clone(messages));
}

export function getProviders(): Promise<Provider[]> {
  return delay(clone(providersFixture));
}

export function getProviderChoice(): Promise<ProviderChoice> {
  return delay(clone(providerChoice));
}

export function setProviderChoice(choice: ProviderChoice): Promise<ProviderChoice> {
  providerChoice = clone(choice);
  return delay(clone(providerChoice));
}
