import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const ChatViewLanggraph = () => import("../views/ChatViewLanggraph.vue");
const StatusView = () => import("../views/StatusView.vue");
const ProfileView = () => import("../views/ProfileView.vue");
const AuthView = () => import("../views/AuthView.vue");

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/chat" },
    { path: "/chat", name: "chat", component: ChatViewLanggraph },
    { path: "/chat/:id", name: "chat-detail", component: ChatViewLanggraph },
    { path: "/status", name: "status", component: StatusView },
    { path: "/profile", name: "profile", component: ProfileView },
    { path: "/auth", name: "auth", component: AuthView },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!auth.isAuthenticated && to.name !== "auth") {
    return { name: "auth", query: { redirect: to.fullPath } };
  }
  if (auth.isAuthenticated && to.name === "auth") {
    return { name: "chat" };
  }
  return true;
});

export default router;
