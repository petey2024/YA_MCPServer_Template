const { createApp, ref, computed } = Vue;

function escapeHtml(input) {
  return String(input)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function sanitizeUrl(url) {
  const raw = String(url || "").trim();
  if (!raw) return "#";
  if (/^(https?:\/\/|mailto:)/i.test(raw)) return raw;
  return "#";
}

function renderInlineMarkdown(text) {
  let s = String(text);
  s = s.replace(/`([^`\n]+)`/g, (_, code) => `<code>${code}</code>`);
  s = s.replace(/\*\*([^*\n]+)\*\*/g, (_, t) => `<strong>${t}</strong>`);
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, (_, p1, t) => `${p1}<em>${t}</em>`);
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
    const href = sanitizeUrl(url);
    return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
  });
  return s;
}

function basicMarkdownToHtml(markdownText) {
  const md = String(markdownText ?? "").replace(/\r\n/g, "\n");
  const lines = md.split("\n");

  let html = "";
  let inCodeBlock = false;
  let codeLang = "";
  let codeBuffer = [];
  let inUl = false;
  let inOl = false;
  let inBlockquote = false;

  const closeLists = () => {
    if (inUl) {
      html += "</ul>";
      inUl = false;
    }
    if (inOl) {
      html += "</ol>";
      inOl = false;
    }
  };

  const closeBlockquote = () => {
    if (inBlockquote) {
      html += "</blockquote>";
      inBlockquote = false;
    }
  };

  for (const rawLine of lines) {
    const fenceMatch = rawLine.match(/^```\s*([a-zA-Z0-9_-]+)?\s*$/);
    if (fenceMatch) {
      if (!inCodeBlock) {
        closeLists();
        closeBlockquote();
        inCodeBlock = true;
        codeLang = fenceMatch[1] || "";
        codeBuffer = [];
      } else {
        const code = escapeHtml(codeBuffer.join("\n"));
        const langClass = codeLang ? ` class="language-${escapeHtml(codeLang)}"` : "";
        html += `<pre><code${langClass}>${code}</code></pre>`;
        inCodeBlock = false;
        codeLang = "";
        codeBuffer = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(rawLine);
      continue;
    }

    if (!rawLine.trim()) {
      closeLists();
      closeBlockquote();
      continue;
    }

    const bqMatch = rawLine.match(/^>\s?(.*)$/);
    if (bqMatch) {
      closeLists();
      if (!inBlockquote) {
        html += "<blockquote>";
        inBlockquote = true;
      }
      const safe = renderInlineMarkdown(escapeHtml(bqMatch[1]));
      html += `<p>${safe}</p>`;
      continue;
    } else {
      closeBlockquote();
    }

    const heading = rawLine.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      closeLists();
      const level = heading[1].length;
      const safe = renderInlineMarkdown(escapeHtml(heading[2].trim()));
      html += `<h${level}>${safe}</h${level}>`;
      continue;
    }

    const ulItem = rawLine.match(/^\s*[-*]\s+(.*)$/);
    if (ulItem) {
      if (inOl) {
        html += "</ol>";
        inOl = false;
      }
      if (!inUl) {
        html += "<ul>";
        inUl = true;
      }
      const safe = renderInlineMarkdown(escapeHtml(ulItem[1].trim()));
      html += `<li>${safe}</li>`;
      continue;
    }

    const olItem = rawLine.match(/^\s*\d+\.\s+(.*)$/);
    if (olItem) {
      if (inUl) {
        html += "</ul>";
        inUl = false;
      }
      if (!inOl) {
        html += "<ol>";
        inOl = true;
      }
      const safe = renderInlineMarkdown(escapeHtml(olItem[1].trim()));
      html += `<li>${safe}</li>`;
      continue;
    }

    closeLists();
    const safe = renderInlineMarkdown(escapeHtml(rawLine.trim()));
    html += `<p>${safe}</p>`;
  }

  if (inCodeBlock) {
    const code = escapeHtml(codeBuffer.join("\n"));
    const langClass = codeLang ? ` class="language-${escapeHtml(codeLang)}"` : "";
    html += `<pre><code${langClass}>${code}</code></pre>`;
  }
  closeLists();
  closeBlockquote();

  return html;
}

function renderMarkdownToSafeHtml(markdownText) {
  const md = String(markdownText ?? "");

  const marked = window.marked;
  if (marked && typeof marked.parse === "function") {
    try {
      const html = marked.parse(md, { headerIds: false, mangle: false });
      const DOMPurify = window.DOMPurify;
      if (DOMPurify && typeof DOMPurify.sanitize === "function") {
        return DOMPurify.sanitize(html);
      }
    } catch {
      // ignore and fall back
    }
  }

  return basicMarkdownToHtml(md);
}

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

    const finalHtml = computed(() => renderMarkdownToSafeHtml(finalText.value));

    const connectionTone = computed(() => {
      if (status.value === "error") return "bad";
      if (isRunning.value || status.value === "connecting" || status.value === "running") return "warn";
      if (status.value === "done") return "ok";
      if (status.value === "stopped") return "warn";
      return "warn";
    });

    const connectionText = computed(() => {
      if (status.value === "error") return "连接异常";
      if (status.value === "connecting") return "正在连接…";
      if (status.value === "running") return "正在运行";
      if (status.value === "done") return "已完成";
      if (status.value === "stopped") return "已停止";
      return "未开始";
    });

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
      finalHtml,
      errorText,
      connectionTone,
      connectionText,
      start,
      stop,
      reset,
    };
  },
  template: `
    <div class="appLayout">
      <aside class="sidebar">
        <div class="sidebarHeader">
          <div class="sidebarTitle">MCP 控制台</div>
          <div class="sidebarSub">Bridge (SSE) · Tools / Events / Final</div>
        </div>


        <div class="sidebarSection">
          <div class="sectionTitle">连接配置</div>
          <div class="panel">
            <div class="label">MCP Server URL（SSE）</div>
            <input class="input" v-model="serverUrl" />

            <div class="divider"></div>

            <div class="row">
              <div style="flex:1;min-width:140px">
                <div class="label">max_steps</div>
                <input class="input" type="number" min="1" max="30" v-model.number="maxSteps" />
              </div>
              <div style="flex:1;min-width:140px">
                <div class="label">verbose</div>
                <button class="btn secondary" @click="verbose = !verbose" :disabled="isRunning">
                  {{ verbose ? 'ON' : 'OFF' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="sidebarSection">
          <div class="sectionTitle">连接状态</div>
          <div class="panel">
            <div class="connRow">
              <span :class="['statusDot', connectionTone]"></span>
              <div class="small">Bridge：{{ connectionText }}</div>
            </div>
            <div class="small" style="margin-top:10px" v-if="toolsCount !== null">tools：{{ toolsCount }}</div>
            <div class="small" style="margin-top:6px" v-if="meta">
              模型：{{ meta.deepseek_model }}
            </div>
          </div>
        </div>

        <div class="sidebarSection">
          <div class="sectionTitle">运行说明</div>
          <div class="panel">
            <div class="codeBlock">cd YA_MCPServer_Template\nuv run server.py\nuv run bridge_server.py</div>
            <div class="small" style="margin-top:10px">提示：密钥只在服务端读取</div>
          </div>
        </div>
      </aside>

      <main class="main">
        <div class="hero">
          <div class="heroKicker">MCP Server 的 SSE 端点地址（默认由 config.yaml 的 transport 决定）</div>
          <div class="heroTitle">金融智能体演示</div>
          <div class="heroDesc">
            输入问题 → DeepSeek tool-calling → MCP Tools → 回填结果 → 输出 final。\n
            你可以尝试：<strong>“分析 AAPL 风险并给建议”</strong> / <strong>“预测 TSLA 未来 7 天价格趋势”</strong>
          </div>
        </div>

        <div class="content">
          <div class="card">
            <div class="label">最终输出（final）</div>
            <div class="chatBubble" v-if="finalText">
              <div class="md" v-html="finalHtml"></div>
            </div>
            <div class="chatBubble ghost" v-else>（暂无输出，发送问题开始）</div>
          </div>

          <div class="card">
            <div class="label">过程日志（SSE events）</div>
            <div class="logs tall">{{ logsText || '（暂无）' }}</div>
          </div>

          <div class="inputBar">
            <div class="row rowCenter">
              <input
                class="input chatInput"
                v-model="query"
                :disabled="isRunning"
                placeholder="输入消息，例如：识别一下 / 查询价格 / 预测趋势…"
                @keydown.enter.prevent="start"
              />
              <button class="btn" @click="start" :disabled="isRunning">发送</button>
              <button class="btn secondary" @click="stop" :disabled="!isRunning">停止</button>
              <span class="badge">状态：{{ status }}</span>
            </div>
            <div class="small error" v-if="errorText">{{ errorText }}</div>
          </div>
        </div>
      </main>
    </div>
  `,
}).mount("#app");
