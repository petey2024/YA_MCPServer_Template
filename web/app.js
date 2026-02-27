const { createApp, ref, computed } = Vue;

function safeJsonParse(line) {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

function buildUrl(path, params) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    url.searchParams.set(k, String(v));
  });
  return url;
}

createApp({
  setup() {
    const query = ref("");
    const serverUrl = ref("http://127.0.0.1:19420");
    const maxSteps = ref(8);
    const verbose = ref(false);

    const isRunning = ref(false);
    const status = ref("idle");
    const meta = ref(null);
    const toolsCount = ref(null);

    const events = ref([]);
    const finalText = ref("");
    const errorText = ref("");

    /** @type {import('vue').Ref<EventSource|null>} */
    const esRef = ref(null);

    const logsText = computed(() => {
      return events.value
        .map((e) => {
          const t = e.type || "event";
          if (t === "deepseek_request") return `[deepseek_request] step=${e.step}`;
          if (t === "deepseek_response") return `[deepseek_response] step=${e.step}`;
          if (t === "tool_call") {
            return `[tool_call] ${e.name} ${e.arguments ? JSON.stringify(e.arguments) : ""}`;
          }
          if (t === "tool_result") {
            let preview = "";
            if (e.result !== undefined) preview = typeof e.result === "string" ? e.result : JSON.stringify(e.result);
            else if (e.error) preview = e.error;
            if (preview.length > 800) preview = preview.slice(0, 800) + "…";
            return `[tool_result] ${e.name} ${preview}`;
          }
          if (t === "status") {
            return `[status] ${e.message || ""}`;
          }
          if (t === "tools") {
            return `[tools] ${e.count ?? "?"}`;
          }
          if (t === "final") {
            return `[final]`; // final content shown separately
          }
          if (t === "error") {
            return `[error] ${e.message || ""}`;
          }
          return `[${t}] ${JSON.stringify(e)}`;
        })
        .join("\n");
    });

    function reset() {
      events.value = [];
      finalText.value = "";
      errorText.value = "";
      status.value = "idle";
      meta.value = null;
      toolsCount.value = null;
    }

    function stop() {
      if (esRef.value) {
        esRef.value.close();
        esRef.value = null;
      }
      isRunning.value = false;
      if (status.value !== "done" && status.value !== "error") {
        status.value = "stopped";
      }
    }

    function pushEvent(ev) {
      events.value.push(ev);

      if (ev.type === "meta") meta.value = ev;
      if (ev.type === "tools") toolsCount.value = ev.count;
      if (ev.type === "status") status.value = ev.message || "running";

      if (ev.type === "final") {
        finalText.value = ev.content || "";
        status.value = "done";
        isRunning.value = false;
        stop();
      }

      if (ev.type === "error") {
        errorText.value = ev.message || "Unknown error";
        status.value = "error";
        isRunning.value = false;
        stop();
      }
    }

    function start() {
      reset();
      errorText.value = "";

      if (!query.value.trim()) {
        errorText.value = "请输入问题 (query)。";
        return;
      }

      isRunning.value = true;
      status.value = "connecting";

      const url = buildUrl("/api/chat", {
        query: query.value,
        server_url: serverUrl.value,
        max_steps: maxSteps.value,
        verbose: verbose.value ? 1 : 0,
      });

      const es = new EventSource(url.toString());
      esRef.value = es;

      es.onmessage = (msg) => {
        const data = safeJsonParse(msg.data);
        if (!data) return;
        pushEvent(data);
      };

      es.onerror = () => {
        // Server may have closed the stream after final/error.
        // If we're still running, surface a generic error.
        if (isRunning.value) {
          pushEvent({ type: "error", message: "SSE 连接中断（请检查 bridge_server 与 mcp server 是否在运行）" });
        }
      };
    }

    return {
      query,
      serverUrl,
      maxSteps,
      verbose,
      isRunning,
      status,
      meta,
      toolsCount,
      events,
      logsText,
      finalText,
      errorText,
      start,
      stop,
      reset,
    };
  },
  template: `
    <div class="container">
      <div class="h1">DeepSeek ↔ MCP 闭环演示（Web）</div>

      <div class="row">
        <div class="card grow">
          <div class="label">问题（query）</div>
          <textarea class="textarea" v-model="query" placeholder="例如：给我分析一下 AAPL 的风险，并给出建议"></textarea>

          <div style="height:10px"></div>

          <div class="kv">
            <div>
              <div class="label">MCP Server URL（SSE）</div>
              <input class="input" v-model="serverUrl" />
              <div class="small">默认：http://127.0.0.1:19420</div>
            </div>
            <div>
              <div class="label">max_steps</div>
              <input class="input" type="number" min="1" max="30" v-model.number="maxSteps" />
              <div class="small">工具调用循环最多步数</div>
            </div>
            <div>
              <div class="label">verbose</div>
              <div class="small" style="margin-bottom:8px">输出更多事件</div>
              <button class="btn secondary" @click="verbose = !verbose" :disabled="isRunning">
                {{ verbose ? 'ON' : 'OFF' }}
              </button>
            </div>
          </div>

          <hr />

          <div class="row" style="align-items:center">
            <button class="btn" @click="start" :disabled="isRunning">开始</button>
            <button class="btn secondary" @click="stop" :disabled="!isRunning">停止</button>
            <span class="badge">状态：{{ status }}</span>
            <span class="badge" v-if="toolsCount !== null">tools：{{ toolsCount }}</span>
          </div>

          <div class="small" style="margin-top:10px" v-if="meta">
            MCP：{{ meta.mcp_server_url }} ｜ DeepSeek：{{ meta.deepseek_model }} ｜ max_steps：{{ meta.max_steps }}
          </div>

          <div class="small" style="margin-top:10px; color:#ffb4b4" v-if="errorText">
            {{ errorText }}
          </div>
        </div>

        <div class="card grow">
          <div class="label">过程日志（SSE events）</div>
          <div class="logs" style="min-height:360px">{{ logsText || '（暂无）' }}</div>
        </div>
      </div>

      <div style="height:12px"></div>

      <div class="card">
        <div class="label">最终输出（final）</div>
        <div class="logs">{{ finalText || '（暂无）' }}</div>
      </div>

      <div class="small" style="margin-top:10px">
        提示：先启动 MCP Server（SSE）再启动 Bridge。密钥只在服务端读取。
      </div>
    </div>
  `,
}).mount("#app");
