import CustomerProfile from "./CustomerProfile";
import { useState, useRef, useEffect } from "react";
import {
  Leaf,
  Send,
  Loader2,
  ShieldCheck,
  PackageSearch,
  Brain,
  AlertTriangle,
  Sprout,
  UserRound,
  Bot,
  Activity,
  CheckCircle2,
  ImagePlus,
  ChevronRight,
  Users,
  ClipboardList,
  MessageSquare,
  X,
} from "lucide-react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000/chat";
const DIAGNOSE_URL = "http://127.0.0.1:8000/diagnose";
const HUMAN_ESCALATION_URL = "http://127.0.0.1:8000/human-escalation";
const ESCALATIONS_URL = "http://127.0.0.1:8000/escalations";

const examples = [
  "My tomato leaves have yellow spots. What should I use?",
  "Can I eat tomatoes one day after spraying pesticide?",
  "Can you recommend a product for tomato aphids?",
  "Where is my order?",
  "Where is my order 1001?",
  "I have a complaint. The product arrived damaged and I want a refund",
];

function formatLabel(value) {
  if (!value) return "Not available";
  return String(value).replaceAll("_", " ");
}

function safeText(value, fallback = "Not available") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  if (Array.isArray(value)) {
    return value.length
      ? value.map((item) => safeText(item, fallback)).join(", ")
      : fallback;
  }

  if (typeof value === "object") {
    if (value.crop) return safeText(value.crop, fallback);
    if (value.disease) return safeText(value.disease, fallback);
    if (value.disease_type) return safeText(value.disease_type, fallback);
    if (value.product_name) return safeText(value.product_name, fallback);
    if (value.product_name_en) return safeText(value.product_name_en, fallback);
    if (value.name) return safeText(value.name, fallback);

    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }

  return String(value);
}

function displayDiagnosisLabel(value) {
  const text = safeText(value, "Unknown");

  const labelMap = {
    玫瑰: "Rose",
    月季: "Rose",
    黑斑病: "Black spot disease",
    真菌病害: "Fungal disease",
    番茄: "Tomato",
    黄瓜: "Cucumber",
    辣椒: "Pepper",
    苹果: "Apple",
    葡萄: "Grape",
    水稻: "Rice",
    小麦: "Wheat",
    玉米: "Corn",
    根腐: "Root rot",
    叶斑病: "Leaf spot disease",
    白粉病: "Powdery mildew",
    炭疽病: "Anthracnose",
    锈病: "Rust disease",
  };

  return labelMap[text] || text;
}

function getImageDiagnosisObject(data) {
  if (data?.diagnosis_response && typeof data.diagnosis_response === "object") {
    return data.diagnosis_response;
  }

  if (data?.diagnosis && typeof data.diagnosis === "object") {
    return data.diagnosis;
  }

  if (data?.result && typeof data.result === "object") {
    return data.result;
  }

  return {};
}

// Typing dots component
function TypingDots() {
  return (
    <span className="typing-dots" aria-label="Typing">
      <span />
      <span />
      <span />
    </span>
  );
}

function App() {
  const [customerId, setCustomerId] = useState("123");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [latestResult, setLatestResult] = useState(null);
  const [showProfiles, setShowProfiles] = useState(false);
  const [showReviewQueue, setShowReviewQueue] = useState(false);
  const [escalations, setEscalations] = useState([]);
  const [reviewNotes, setReviewNotes] = useState({});
  const [isTyping, setIsTyping] = useState(false);
  const [typingMessageId, setTypingMessageId] = useState(null);

  const chatEndRef = useRef(null);
  const typingIntervalRef = useRef(null);

  const [messages, setMessages] = useState([
    {
      id: "init",
      role: "assistant",
      text: "Hello, I'm Agro-Mind. Describe your crop issue, upload a photo of your plant, or ask a support question.",
      done: true,
    },
  ]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Fake typing effect — streams the full response char by char
  function startTyping(fullText, messageId) {
    setIsTyping(true);
    setTypingMessageId(messageId);

    let index = 0;
    const CHUNK = 4; // chars per tick — tune for speed
    const INTERVAL = 18; // ms per tick

    if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);

    typingIntervalRef.current = setInterval(() => {
      index += CHUNK;
      const partial = fullText.slice(0, index);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? { ...m, text: partial } : m
        )
      );

      if (index >= fullText.length) {
        clearInterval(typingIntervalRef.current);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId ? { ...m, text: fullText, done: true } : m
          )
        );
        setIsTyping(false);
        setTypingMessageId(null);
      }
    }, INTERVAL);
  }

  async function sendMessage(customMessage = null) {
    const textToSend = customMessage || message;
    if (!textToSend.trim()) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: textToSend,
      done: true,
    };

    setMessages((prev) => [...prev, userMessage]);
    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, message: textToSend }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.log("Backend error:", errorText);
        throw new Error("Backend returned an error");
      }

      const data = await response.json();
      // Update side panel immediately — don't wait for typing to finish
      setLatestResult(data);

      const fullText = data.response || buildFriendlyResponse(data);
      const msgId = `assistant-${Date.now()}`;

      // Insert placeholder message — typing will fill it in
      const assistantMessage = {
        id: msgId,
        role: "assistant",
        text: "",
        done: false,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setLoading(false);
      startTyping(fullText, msgId);
    } catch (error) {
      const errorMessage = {
        id: `err-${Date.now()}`,
        role: "assistant",
        error: true,
        text: "I couldn't connect to the Agro-Mind backend. Make sure FastAPI is running on http://127.0.0.1:8000.",
        done: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
      setLoading(false);
    }
  }

  async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    event.target.value = null;

    const userMessage = {
      id: `user-img-${Date.now()}`,
      role: "user",
      text: `📷 ${file.name}`,
      done: true,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("customer_id", customerId);

    try {
      const response = await fetch(DIAGNOSE_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Diagnose API Error:", response.status, errorText);
        throw new Error(`Backend returned ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log("Diagnosis response:", data);

      const diagnosisObject = getImageDiagnosisObject(data);

      const detectedCrop = displayDiagnosisLabel(
        data.crop || data.detected_crop || diagnosisObject.crop
      );
      const detectedDisease = displayDiagnosisLabel(
        data.disease ||
          data.condition ||
          data.detected_issue ||
          diagnosisObject.disease ||
          data.diagnosis
      );
      const detectedDiseaseType = displayDiagnosisLabel(
        data.disease_type || diagnosisObject.disease_type || "Not available"
      );

      const confidenceRaw =
        typeof data.confidence === "number"
          ? data.confidence
          : Number(data.confidence || diagnosisObject.confidence || 0);
      const confidence =
        confidenceRaw > 1
          ? Math.round(confidenceRaw)
          : Math.round(confidenceRaw * 100);

      const symptoms = safeText(
        data.symptoms || data.explanation || data.description,
        "Not available"
      );
      const customerFacingResponse = safeText(
        data.response ||
          data.customer_response ||
          data.safe_response ||
          data.recommendation ||
          data.recommendation_hint,
        "No direct product recommendation was shown. Human review may be required."
      );

      let recommendedProduct = null;
      if (data.best_product) {
        recommendedProduct =
          data.best_product.product_name ||
          data.best_product.product_name_en ||
          data.best_product.name ||
          null;
      }
      if (!recommendedProduct && Array.isArray(data.recommended_products)) {
        recommendedProduct =
          data.recommended_products[0]?.product_name ||
          data.recommended_products[0]?.product_name_en ||
          data.recommended_products[0]?.name ||
          null;
      }
      recommendedProduct = safeText(recommendedProduct, "");

      let responseText = `📷 Image Diagnosis Complete:\n\n`;
      responseText += `Crop: ${detectedCrop}\n\n`;
      responseText += `Disease: ${detectedDisease}\n\n`;
      responseText += `Disease type: ${detectedDiseaseType}\n\n`;
      responseText += `Confidence: ${confidence}%\n\n`;
      responseText += `Severity: ${safeText(data.severity, "Not available")}\n\n`;
      responseText += `Symptoms: ${symptoms}\n\n`;
      responseText += `Recommendation: ${customerFacingResponse}`;
      if (recommendedProduct) responseText += `\n\nSuggested product: ${recommendedProduct}`;
      if (data.escalation_case_id) responseText += `\n\nHuman review case: ${data.escalation_case_id}`;

      const msgId = `assistant-diag-${Date.now()}`;
      const assistantMessage = {
        id: msgId,
        role: "assistant",
        text: "",
        done: false,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      setLatestResult({
        ...data,
        intent: "image_diagnosis",
        risk_level:
          data.risk_level ||
          (data.needs_human_review || data.human_review_required
            ? "medium"
            : "low"),
        detected_crop: detectedCrop,
        detected_issue: detectedDisease,
        recommended_product: recommendedProduct || null,
        product_reason: customerFacingResponse || "Image diagnosis completed.",
        escalation_required: Boolean(
          data.escalation_required ||
            data.needs_human_review ||
            data.human_review_required
        ),
        execution_trace: data.execution_trace || [
          { step: 1, task: "Upload crop image", status: "completed", result: file.name },
          { step: 2, task: "Run image diagnosis tool", status: "completed", result: detectedDisease },
          {
            step: 3,
            task: "Check confidence and escalation",
            status: "completed",
            result:
              data.needs_human_review || data.human_review_required
                ? "Human review required"
                : "No immediate escalation",
          },
        ],
      });

      setLoading(false);
      startTyping(responseText, msgId);
    } catch (error) {
      console.error("Image Upload Error:", error);
      const errorMessage = {
        id: `err-${Date.now()}`,
        role: "assistant",
        error: true,
        text: `Image diagnosis failed: ${error.message}`,
        done: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
      setLoading(false);
    }
  }

  async function goToHumanEscalation() {
    try {
      if (latestResult?.escalation_case_id) {
        window.location.href = "/human_escalation.html";
        return;
      }

      const response = await fetch(HUMAN_ESCALATION_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_id: customerId,
          name: customerId,
          phone: "",
          issue:
            safeText(latestResult?.detected_issue, "") ||
            safeText(latestResult?.intent, "") ||
            "User requested human escalation",
          ai_response:
            safeText(latestResult?.response, "") ||
            safeText(latestResult?.customer_response, "") ||
            safeText(latestResult?.safe_response, "") ||
            safeText(latestResult?.product_reason, "") ||
            "",
          source: latestResult?.intent || "manual",
        }),
      });

      const data = await response.json();

      setLatestResult((prev) => ({
        ...(prev || {}),
        human_review_required: true,
        escalation_required: true,
        escalation_case_id: data.escalation_case_id,
        updated_customer_profile:
          data.updated_customer_profile || prev?.updated_customer_profile,
      }));

      window.location.href = "/human_escalation.html";
    } catch (error) {
      console.error("Human escalation failed:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          error: true,
          text: "Human escalation failed. Please make sure the backend is running.",
          done: true,
        },
      ]);
    }
  }

  async function loadEscalations() {
    try {
      const response = await fetch(`${ESCALATIONS_URL}?status=pending`);
      const data = await response.json();
      setEscalations(data.items || []);
    } catch (error) {
      console.error("Failed to load escalations:", error);
    }
  }

  async function markReviewed(caseId) {
    try {
      await fetch(`http://127.0.0.1:8000/escalations/${caseId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewer_note: reviewNotes[caseId] || "Reviewed from Agro-Mind UI",
        }),
      });
      setReviewNotes((prev) => ({ ...prev, [caseId]: "" }));
      await loadEscalations();
    } catch (error) {
      console.error("Failed to mark escalation reviewed:", error);
    }
  }

  function buildFriendlyResponse(data) {
    let response = "";

    if (data.intent === "order_status") {
      if (data.order?.order_found) {
        response += `I found the order details.\n\n`;
        response += `Order ID: ${safeText(data.order.order_id)}\n`;
        response += `Status: ${safeText(data.order.status)}\n`;
        response += `ETA: ${safeText(data.order.eta)}\n`;
        response += `Tracking number: ${safeText(data.order.tracking_number)}\n\n`;
        response += `${safeText(data.order.reason)}`;
      } else {
        response += "I could not find an order for this request.\n\n";
        response += safeText(
          data.order?.reason,
          "No order information was available."
        );
      }
      if (data.case_saved) response += `\n\nCase saved: Yes #${safeText(data.case_id)}`;
      if (data.escalation_case_id) response += `\nHuman review case: ${safeText(data.escalation_case_id)}`;
      return response;
    }

    if (
      data.intent === "pesticide_safety" ||
      data.risk_level === "high" ||
      data.escalation_required
    ) {
      response +=
        "This looks like a safety-sensitive or uncertain case. A human expert should review it before further action.\n\n";
    }

    if (data.detected_crop || data.detected_issue) {
      response += `Possible crop: ${safeText(data.detected_crop, "Not detected")}\n`;
      response += `Possible issue: ${safeText(data.detected_issue, "Not confirmed")}\n\n`;
    }

    if (data.recommended_product) {
      response += `Suggested product: ${safeText(data.recommended_product)}\n`;
      response +=
        "Please confirm the diagnosis before applying any pesticide or treatment.\n\n";
    } else {
      response += "No product recommendation was made for this message.\n\n";
    }

    response += `Risk level: ${safeText(data.risk_level)}\n`;
    response += data.escalation_required
      ? "Escalation: Human expert review is recommended."
      : "Escalation: No human escalation needed right now.";

    if (data.case_saved) response += `\nCase saved: Yes #${safeText(data.case_id)}`;
    if (data.escalation_case_id) response += `\nHuman review case: ${safeText(data.escalation_case_id)}`;

    return response;
  }

  const riskLevel = latestResult?.risk_level || "none";
  const isOrderStatus = latestResult?.intent === "order_status";
  const needsEscalation =
    latestResult?.escalation_required ||
    latestResult?.needs_human_review ||
    latestResult?.human_review_required;

  const activeView = showProfiles
    ? "profiles"
    : showReviewQueue
    ? "review"
    : "chat";

  return (
    <div className="app-shell">
      {/* Ambient background glows */}
      <div className="glow glow-one" />
      <div className="glow glow-two" />
      <div className="glow glow-three" />

      {/* ── Top bar ── */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Leaf size={20} />
          </div>
          <div>
            <h1>Agro-Mind</h1>
            <p>AI Agricultural Support</p>
          </div>
        </div>

        <nav className="topbar-nav">
          <button
            className={`nav-pill ${activeView === "chat" ? "nav-pill--active" : ""}`}
            onClick={() => { setShowProfiles(false); setShowReviewQueue(false); }}
          >
            <MessageSquare size={14} />
            Chat
          </button>

          <button
            className={`nav-pill ${activeView === "profiles" ? "nav-pill--active" : ""}`}
            onClick={() => { setShowReviewQueue(false); setShowProfiles((p) => !p); }}
          >
            <Users size={14} />
            Profiles
          </button>

          <button
            className={`nav-pill ${activeView === "review" ? "nav-pill--active" : ""}`}
            onClick={async () => {
              setShowProfiles(false);
              setShowReviewQueue((p) => !p);
              await loadEscalations();
            }}
          >
            <ClipboardList size={14} />
            Review Queue
          </button>

          <div className="system-status">
            <span className="status-dot" />
            Live
          </div>
        </nav>
      </header>

      {/* ── Customer Profiles ── */}
      {activeView === "profiles" && <CustomerProfile />}

      {/* ── Human Review Queue ── */}
      {activeView === "review" && (
        <main className="review-layout">
          <section className="review-panel">
            <div className="panel-header">
              <div>
                <p className="panel-eyebrow">Human-in-the-Loop</p>
                <h3>Review Queue</h3>
              </div>
              <button className="btn-secondary" onClick={loadEscalations}>
                Refresh
              </button>
            </div>

            {escalations.length === 0 ? (
              <div className="empty-panel">
                <div className="empty-icon">
                  <ClipboardList size={26} />
                </div>
                <h3>Queue is clear</h3>
                <p>
                  Escalated pesticide, complaint, and low-confidence diagnosis
                  cases will appear here.
                </p>
              </div>
            ) : (
              <div className="review-cards-list">
                {escalations.map((item) => (
                  <div key={item.case_id} className="review-card">
                    <div className="review-card-header">
                      <div className="review-card-id">
                        <AlertTriangle size={14} />
                        {safeText(item.case_id)}
                      </div>
                      <span className="status-badge status-badge--pending">
                        {safeText(item.status)}
                      </span>
                    </div>

                    <div className="review-fields">
                      <div className="review-field">
                        <span>Customer</span>
                        <strong>{safeText(item.customer_id)}</strong>
                      </div>
                      <div className="review-field">
                        <span>Type</span>
                        <strong>{formatLabel(item.type)}</strong>
                      </div>
                      <div className="review-field">
                        <span>Source</span>
                        <strong>{safeText(item.source)}</strong>
                      </div>
                    </div>

                    <div className="review-field review-field--full">
                      <span>User message</span>
                      <strong>
                        {safeText(
                          item.user_message ||
                            item.payload?.received_message ||
                            item.payload?.message ||
                            item.payload?.issue ||
                            item.payload?.payload?.issue,
                          "Not saved."
                        )}
                      </strong>
                    </div>

                    <div className="review-field review-field--full">
                      <span>Reason</span>
                      <strong>{safeText(item.reason)}</strong>
                    </div>

                    <div className="review-field review-field--full">
                      <span>AI Response</span>
                      <strong>{safeText(item.ai_response, "No AI response saved.")}</strong>
                    </div>

                    <textarea
                      className="review-note"
                      placeholder="Add a reviewer note…"
                      value={reviewNotes[item.case_id] || ""}
                      onChange={(e) =>
                        setReviewNotes((prev) => ({
                          ...prev,
                          [item.case_id]: e.target.value,
                        }))
                      }
                    />

                    <button
                      className="btn-primary btn-full"
                      onClick={() => markReviewed(item.case_id)}
                    >
                      <CheckCircle2 size={15} />
                      Mark Reviewed
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>
      )}

      {/* ── Main Chat Layout ── */}
      {activeView === "chat" && (
        <main className="main-layout">
          {/* Left: Chat */}
          <section className="chat-card">
            <div className="chat-header">
              <div className="chat-header-text">
                <div className="eyebrow">
                  <Sprout size={13} />
                  Customer Chat
                </div>
                <h2>Ask Agro-Mind</h2>
                <p>
                  Describe a crop issue, upload a plant photo, or ask a support question.
                  The agent runs intent detection, safety checks, product matching,
                  and order lookup on every message.
                </p>
              </div>
              <div className="chat-header-bot">
                <Bot size={28} />
              </div>
            </div>

            {/* Customer ID */}
            <div className="customer-row">
              <label htmlFor="cid">Customer ID</label>
              <input
                id="cid"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="123"
              />
            </div>

            {/* Messages */}
            <div className="chat-window">
              {messages.map((item) => (
                <div
                  key={item.id}
                  className={`message-row ${item.role === "user" ? "user-row" : "assistant-row"} msg-fade-in`}
                >
                  <div className={`message-avatar ${item.role === "user" ? "avatar--user" : "avatar--bot"}`}>
                    {item.role === "user" ? (
                      <UserRound size={15} />
                    ) : (
                      <Leaf size={15} />
                    )}
                  </div>

                  <div
                    className={`message-bubble ${
                      item.role === "user" ? "user-bubble" : "assistant-bubble"
                    } ${item.error ? "error-bubble" : ""}`}
                  >
                    <pre>{safeText(item.text, "")}</pre>
                    {/* Cursor blink while this specific message is still typing */}
                    {!item.done && item.role === "assistant" && (
                      <span className="type-cursor" />
                    )}
                  </div>
                </div>
              ))}

              {/* Spinner while waiting for backend response */}
              {loading && (
                <div className="message-row assistant-row msg-fade-in">
                  <div className="message-avatar avatar--bot">
                    <Leaf size={15} />
                  </div>
                  <div className="message-bubble assistant-bubble typing-bubble">
                    <TypingDots />
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Example prompts */}
            <div className="examples">
              {examples.map((ex) => (
                <button
                  key={ex}
                  className="example-pill"
                  onClick={() => sendMessage(ex)}
                  disabled={loading || isTyping}
                >
                  {ex}
                  <ChevronRight size={12} />
                </button>
              ))}
            </div>

            {/* Composer */}
            <div className="composer">
              <label
                className={`upload-btn ${loading || isTyping ? "upload-btn--disabled" : ""}`}
                title="Upload crop image for diagnosis"
              >
                <ImagePlus size={20} />
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  disabled={loading || isTyping}
                  style={{ display: "none" }}
                />
              </label>

              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type a customer message…"
                rows={1}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
              />

              <button
                className="send-btn"
                onClick={() => sendMessage()}
                disabled={loading || isTyping}
                aria-label="Send"
              >
                {loading ? (
                  <Loader2 className="spin" size={17} />
                ) : (
                  <Send size={17} />
                )}
              </button>
            </div>
          </section>

          {/* Right: Agent Panel */}
          <aside className="agent-panel">
            <div className="panel-header">
              <div>
                <p className="panel-eyebrow">Agent Analysis</p>
                <h3>
                  {latestResult ? formatLabel(latestResult.intent) : "Awaiting input"}
                </h3>
              </div>
              <span className={`risk-badge risk-badge--${riskLevel}`}>
                {riskLevel}
              </span>
            </div>

            {!latestResult && (
              <div className="empty-panel">
                <div className="empty-icon">
                  <Brain size={26} />
                </div>
                <h3>No case yet</h3>
                <p>
                  Send a message or upload a plant photo — the agent's decision
                  path will appear here in real time.
                </p>
              </div>
            )}

            {latestResult && (
              <div className="panel-body">
                {/* Metric grid */}
                <div className="metric-grid">
                  <div className="metric-card">
                    <Brain size={18} />
                    <span>Intent</span>
                    <strong>{formatLabel(latestResult.intent)}</strong>
                  </div>

                  <div className="metric-card">
                    <ShieldCheck size={18} />
                    <span>Risk</span>
                    <strong className={`risk-text risk-text--${safeText(latestResult.risk_level, "none")}`}>
                      {safeText(latestResult.risk_level)}
                    </strong>
                  </div>

                  {latestResult.intent !== "image_diagnosis" && (
                    <div className="metric-card">
                      <CheckCircle2 size={18} />
                      <span>Case</span>
                      <strong>
                        {latestResult.case_saved
                          ? `#${safeText(latestResult.case_id)}`
                          : "Not saved"}
                      </strong>
                    </div>
                  )}

                  {isOrderStatus ? (
                    <>
                      <div className="metric-card">
                        <PackageSearch size={18} />
                        <span>Order ID</span>
                        <strong>{safeText(latestResult.order?.order_id, "Not found")}</strong>
                      </div>
                      <div className="metric-card">
                        <Activity size={18} />
                        <span>Status</span>
                        <strong>{safeText(latestResult.order?.status, "—")}</strong>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="metric-card">
                        <PackageSearch size={18} />
                        <span>Product / Crop</span>
                        <strong>
                          {safeText(
                            latestResult.recommended_product || latestResult.detected_crop,
                            "None"
                          )}
                        </strong>
                      </div>
                      <div className="metric-card">
                        <Activity size={18} />
                        <span>Escalation</span>
                        <strong className={needsEscalation ? "risk-text risk-text--high" : ""}>
                          {needsEscalation ? "Required" : "Not required"}
                        </strong>
                      </div>
                    </>
                  )}
                </div>

                {/* Customer memory */}
                {latestResult.updated_customer_profile && (
                  <div className="decision-card">
                    <div className="decision-title">
                      <UserRound size={16} />
                      Customer memory
                    </div>
                    <div className="decision-fields">
                      <div className="decision-field">
                        <span>Profile</span>
                        <strong>
                          {safeText(
                            latestResult.updated_customer_profile.profile_summary,
                            "No summary available"
                          )}
                        </strong>
                      </div>
                      <div className="decision-field">
                        <span>Segment</span>
                        <strong>
                          {safeText(
                            latestResult.updated_customer_profile.customer_segment,
                            "Regular"
                          )}
                        </strong>
                      </div>
                      <div className="decision-field">
                        <span>Crops</span>
                        <strong>
                          {safeText(
                            latestResult.updated_customer_profile.crops,
                            "Not available"
                          )}
                        </strong>
                      </div>
                    </div>
                  </div>
                )}

                {/* Current decision */}
                <div className="decision-card">
                  <div className="decision-title">
                    <CheckCircle2 size={16} />
                    Current decision
                  </div>
                  <div className="decision-fields">
                    {isOrderStatus ? (
                      <>
                        <div className="decision-field">
                          <span>Order found</span>
                          <strong>{latestResult.order?.order_found ? "Yes" : "No"}</strong>
                        </div>
                        <div className="decision-field">
                          <span>ETA</span>
                          <strong>{safeText(latestResult.order?.eta)}</strong>
                        </div>
                        <div className="decision-field">
                          <span>Tracking</span>
                          <strong>{safeText(latestResult.order?.tracking_number)}</strong>
                        </div>
                        <div className="decision-field decision-field--full">
                          <span>Reason</span>
                          <strong>
                            {safeText(latestResult.order?.reason, "No lookup reason available")}
                          </strong>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="decision-field">
                          <span>Detected crop</span>
                          <strong>{safeText(latestResult.detected_crop, "Not detected")}</strong>
                        </div>
                        <div className="decision-field">
                          <span>Detected issue</span>
                          <strong>{safeText(latestResult.detected_issue, "Not detected")}</strong>
                        </div>
                        <div className="decision-field decision-field--full">
                          <span>Reason</span>
                          <strong>
                            {safeText(latestResult.product_reason, "No product reason available")}
                          </strong>
                        </div>
                        {latestResult.escalation_case_id && (
                          <div className="decision-field">
                            <span>Review case</span>
                            <strong>{safeText(latestResult.escalation_case_id)}</strong>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Execution trace */}
                {latestResult.execution_trace?.length > 0 && (
                  <div className="decision-card">
                    <div className="decision-title">
                      <Activity size={16} />
                      Execution trace
                    </div>
                    <ol className="trace-list">
                      {latestResult.execution_trace.map((step) => (
                        <li key={safeText(step.step)} className="trace-step">
                          <div className="trace-dot">
                            <CheckCircle2 size={12} />
                          </div>
                          <div className="trace-content">
                            <div className="trace-task">{safeText(step.task)}</div>
                            <div className="trace-result">
                              <span className={`trace-status trace-status--${safeText(step.status, "unknown")}`}>
                                {safeText(step.status, "unknown")}
                              </span>
                              {safeText(step.result, "No result")}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* High-risk warning */}
                {latestResult.risk_level === "high" && (
                  <div className="warning-card warning-card--high">
                    <AlertTriangle size={18} />
                    <div>
                      <strong>High-risk case</strong>
                      <p>
                        This case has been flagged for agronomist or safety review before any action is taken.
                      </p>
                    </div>
                  </div>
                )}

                {/* Escalation warning (medium) */}
                {needsEscalation && latestResult.risk_level !== "high" && (
                  <div className="warning-card warning-card--medium">
                    <AlertTriangle size={18} />
                    <div>
                      <strong>Human review recommended</strong>
                      <p>
                        This case has been flagged for agronomist review.
                      </p>
                    </div>
                  </div>
                )}

                {/* Escalation CTA */}
                {needsEscalation && (
                  <button className="btn-escalate" onClick={goToHumanEscalation}>
                    <UserRound size={16} />
                    Contact Human Expert
                  </button>
                )}

                {/* Raw JSON */}
                <details className="json-card">
                  <summary>Raw backend JSON</summary>
                  <pre>{JSON.stringify(latestResult, null, 2)}</pre>
                </details>
              </div>
            )}
          </aside>
        </main>
      )}
    </div>
  );
}

export default App;
