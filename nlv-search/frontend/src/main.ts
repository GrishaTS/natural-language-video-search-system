import { createApp } from "vue";
import { createPinia } from "pinia";
import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import App from "./App.vue";
import router from "./router";
import { register } from "vue-advanced-chat";
import "./assets/main.css";

register();

const app = createApp(App);
const pinia = createPinia();
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
    },
  },
});

app.use(pinia);
app.use(router);
app.use(VueQueryPlugin, { queryClient });

app.mount("#app");
