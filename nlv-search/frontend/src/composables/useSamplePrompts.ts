import { computed } from "vue";

const DEFAULT_PROMPTS = [
  "Найди Германа Петрова за последние полтора года",
  "авто с номером 2977TK7",
  "найди девушку на платонова 20б за 2025 год",
  "найди германана петрова за 2025 год",
];

export function useSamplePrompts() {
  const prompts = computed(() => DEFAULT_PROMPTS);
  return { prompts };
}
