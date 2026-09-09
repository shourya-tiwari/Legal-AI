"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * AI Assistant conversations.
 *
 * The backend `/ask` endpoint is single-turn and stateless — no conversation
 * persistence server-side. Conversations therefore live in localStorage; each
 * turn is an independent grounded call against the selected document.
 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  /** assistant only */
  faithful?: boolean;
  faithfulnessMethod?: string;
  unsupportedClaims?: string[];
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  documentId: number | null;
  documentName: string | null;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

interface ChatState {
  conversations: Conversation[];
  activeId: string | null;
  create: (documentId: number | null, documentName: string | null) => string;
  setActive: (id: string | null) => void;
  remove: (id: string) => void;
  rename: (id: string, title: string) => void;
  addMessage: (conversationId: string, message: ChatMessage) => void;
  updateMessage: (
    conversationId: string,
    messageId: string,
    patch: Partial<ChatMessage>,
  ) => void;
  setDocument: (
    conversationId: string,
    documentId: number | null,
    documentName: string | null,
  ) => void;
  clearAll: () => void;
}

const now = () => new Date().toISOString();
const rid = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

export const useChat = create<ChatState>()(
  persist(
    (set) => ({
      conversations: [],
      activeId: null,
      create: (documentId, documentName) => {
        const id = rid();
        const conv: Conversation = {
          id,
          title: "New conversation",
          documentId,
          documentName,
          messages: [],
          createdAt: now(),
          updatedAt: now(),
        };
        set((s) => ({
          conversations: [conv, ...s.conversations],
          activeId: id,
        }));
        return id;
      },
      setActive: (id) => set({ activeId: id }),
      remove: (id) =>
        set((s) => {
          const conversations = s.conversations.filter((c) => c.id !== id);
          return {
            conversations,
            activeId: s.activeId === id ? (conversations[0]?.id ?? null) : s.activeId,
          };
        }),
      rename: (id, title) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === id ? { ...c, title, updatedAt: now() } : c,
          ),
        })),
      addMessage: (conversationId, message) =>
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== conversationId) return c;
            const isFirstUser =
              message.role === "user" &&
              c.messages.filter((m) => m.role === "user").length === 0;
            return {
              ...c,
              messages: [...c.messages, message],
              title: isFirstUser
                ? message.content.slice(0, 60)
                : c.title,
              updatedAt: now(),
            };
          }),
        })),
      updateMessage: (conversationId, messageId, patch) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === messageId ? { ...m, ...patch } : m,
                  ),
                  updatedAt: now(),
                }
              : c,
          ),
        })),
      setDocument: (conversationId, documentId, documentName) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, documentId, documentName, updatedAt: now() }
              : c,
          ),
        })),
      clearAll: () => set({ conversations: [], activeId: null }),
    }),
    { name: "legalai.chat" },
  ),
);
