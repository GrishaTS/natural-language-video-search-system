import { defineStore } from "pinia";

interface ChatState {
  selectedChatId: string | null;
}

export const useChatStore = defineStore("chat", {
  state: (): ChatState => ({
    selectedChatId: null,
  }),
  actions: {
    selectChat(id: string | null) {
      this.selectedChatId = id;
    },
  },
});
