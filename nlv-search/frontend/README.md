# Natural Language Video Search — Frontend

https://github.com/user-attachments/assets/b5dc470c-63cb-47c8-8a52-841497049730

https://github.com/user-attachments/assets/c9687dce-3197-49f9-9bba-93927bdfb997

https://github.com/user-attachments/assets/619f2063-edeb-49c9-a9dd-593062388a43

___
## About
*Natural Language Video Search — Frontend is the user interface of the system, built as a Vue 3 + TypeScript SPA. It provides a chat-based interface for issuing natural language queries, attaching photos, resolving entity disambiguation prompts, and viewing streaming search results with VMS deep-links and event previews.*

Key features:
- Multi-page layout: Chat, Auth, Profile, and Services Status pages
- Real-time SSE streaming of agent stages, LLM tokens, and search result previews
- Inline options cards for entity disambiguation (interrupt/resume flow)
- Photo attachment for face-based search
- Markdown rendering of LLM narrative responses
- Pinia-based auth and chat state management

___
## Project Structure

<details>
  <summary>📂 frontend/</summary>
  <ul>
    <li>📄 <code>.dockerignore</code> — Files and folders excluded from Docker build context</li>
    <li>📄 <code>Dockerfile</code> — Instructions for building the frontend Docker image</li>
    <li>📄 <code>package.json</code> — Node.js dependencies and scripts</li>
    <li>📄 <code>vite.config.ts</code> — Vite build configuration</li>
    <li>📄 <code>tsconfig.json</code> — TypeScript configuration</li>
    <li>📄 <code>index.html</code> — HTML entry point</li>
    <details>
      <summary>📂 src/</summary>
      <ul>
        <li>📄 <code>main.ts</code> — Application entry point</li>
        <li>📄 <code>App.vue</code> — Root component</li>
        <details>
          <summary>📂 api/</summary>
          <ul>
            <li>📄 <code>auth.ts</code> — Auth API calls (login, register, refresh)</li>
            <li>📄 <code>conversationalSearch.ts</code> — Chat and SSE streaming API calls</li>
            <li>📄 <code>health.ts</code> — Services health API calls</li>
            <li>📄 <code>http.ts</code> — Axios instance with interceptors</li>
            <li>📄 <code>errors.ts</code> — API error types</li>
          </ul>
        </details>
        <details>
          <summary>📂 components/</summary>
          <ul>
            <li>📄 <code>AppAlert.vue</code> — Global alert component</li>
            <li>📄 <code>AppHero.vue</code> — Landing hero section</li>
            <li>📄 <code>PromptExamples.vue</code> — Sample query suggestions</li>
            <details>
              <summary>📂 chat/</summary>
              <ul>
                <li>📄 <code>ChatMessages.vue</code> — Message list renderer</li>
                <li>📄 <code>SearchResultMessageCard.vue</code> — Result card with previews and VMS links</li>
                <li>📄 <code>InlineOptionsMessageCard.vue</code> — Entity disambiguation selection card</li>
                <li>📄 <code>vmsLinks.ts</code> — VMS deep-link formatting utilities</li>
              </ul>
            </details>
            <details>
              <summary>📂 status/</summary>
              <ul>
                <li>📄 <code>ServicesStatusGrid.vue</code> — External services health status grid</li>
              </ul>
            </details>
          </ul>
        </details>
        <details>
          <summary>📂 composables/</summary>
          <ul>
            <li>📄 <code>useAuthGuard.ts</code> — Route authentication guard</li>
            <li>📄 <code>useMarkdownRenderer.ts</code> — Markdown-to-HTML rendering</li>
            <li>📄 <code>useSamplePrompts.ts</code> — Sample prompt rotation logic</li>
          </ul>
        </details>
        <details>
          <summary>📂 stores/</summary>
          <ul>
            <li>📄 <code>auth.ts</code> — Auth state (user, tokens, login/logout)</li>
            <li>📄 <code>chat.ts</code> — Chat and message state with SSE handling</li>
          </ul>
        </details>
        <details>
          <summary>📂 types/</summary>
          <ul>
            <li>📄 <code>auth.ts</code> — Auth request/response types</li>
            <li>📄 <code>chat.ts</code> — Chat, message, and SSE event types</li>
            <li>📄 <code>health.ts</code> — Health status types</li>
            <li>📄 <code>common.ts</code> — Shared utility types</li>
          </ul>
        </details>
        <details>
          <summary>📂 views/</summary>
          <ul>
            <li>📄 <code>AuthView.vue</code> — Login and registration page</li>
            <li>📄 <code>ChatViewLanggraph.vue</code> — Main conversational search page</li>
            <li>📄 <code>ProfileView.vue</code> — User profile page</li>
            <li>📄 <code>StatusView.vue</code> — External services status page</li>
          </ul>
        </details>
        <li>📄 <code>router/index.ts</code> — Vue Router route definitions</li>
        <li>📄 <code>config/index.ts</code> — Application configuration constants</li>
      </ul>
    </details>
  </ul>
</details>

___
## Technologies Used
![Vue 3](https://img.shields.io/badge/UI-Vue_3-4FC08D?logo=vue.js) ![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?logo=typescript) ![Vite](https://img.shields.io/badge/Build-Vite-646CFF?logo=vite) ![Pinia](https://img.shields.io/badge/State-Pinia-FFD859) ![Axios](https://img.shields.io/badge/HTTP-Axios-5A29E4) ![Vue Router](https://img.shields.io/badge/Routing-Vue_Router-4FC08D?logo=vue.js)
