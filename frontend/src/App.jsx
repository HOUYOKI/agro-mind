import CustomerProfile from "./CustomerProfile";
import { useState } from "react";
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

function App() {
  const [customerId, setCustomerId] = useState("123");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [latestResult, setLatestResult] = useState(null);
  const [showProfiles, setShowProfiles] = useState(false);
  const [showReviewQueue, setShowReviewQueue] = useState(false);
  const [escalations, setEscalations] = useState([]);
  const [reviewNotes, setReviewNotes] = useState({});

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text:
        "Hello, I’m Agro-Mind. Describe your crop issue, upload a photo of your plant, or ask a support question.",
    },
  ]);

  async function sendMessage(customMessage = null) {
    const textToSend = customMessage || message;

    if (!textToSend.trim()) return;

    const userMessage = {
      role: "user",
      text: textToSend,
    };

    setMessages((prev) => [...prev, userMessage]);
    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          customer_id: customerId,
          message: textToSend,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.log("Backend error:", errorText);
        throw new Error("Backend returned an error");
      }

      const data = await response.json();
      setLatestResult(data);

      const assistantMessage = {
        role: "assistant",
        text: data.response || buildFriendlyResponse(data),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: "assistant",
        error: true,
        text:
          "I couldn’t connect to the Agro-Mind backend. Make sure FastAPI is running on http://127.0.0.1:8000.",
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    event.target.value = null;

    const userMessage = {
      role: "user",
      text: `[Uploaded Image: ${file.name}]`,
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

        console.error("Diagnose API Error:");
        console.error("Status:", response.status);
        console.error("Response:", errorText);

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

      if (recommendedProduct) {
        responseText += `\n\nSuggested product: ${recommendedProduct}`;
      }

      if (data.escalation_case_id) {
        responseText += `\n\nHuman review case: ${data.escalation_case_id}`;
      }

      const assistantMessage = {
        role: "assistant",
        text: responseText,
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
          {
            step: 1,
            task: "Upload crop image",
            status: "completed",
            result: file.name,
          },
          {
            step: 2,
            task: "Run image diagnosis tool",
            status: "completed",
            result: detectedDisease,
          },
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
    } catch (error) {
      console.error("Image Upload Error:", error);

      const errorMessage = {
        role: "assistant",
        error: true,
        text: `Image diagnosis failed: ${error.message}`,
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
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
        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          customer_id: customerId,
          name: customerId,
          phone: "",
          issue:
            latestResult?.detected_issue ||
            latestResult?.intent ||
            "User requested human escalation",
          ai_response:
            latestResult?.response ||
            latestResult?.customer_response ||
            latestResult?.safe_response ||
            latestResult?.product_reason ||
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
          role: "assistant",
          error: true,
          text: "Human escalation failed. Please make sure the backend is running.",
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          reviewer_note:
            reviewNotes[caseId] || "Reviewed from Agro-Mind UI",
        }),
      });

      setReviewNotes((prev) => ({
        ...prev,
        [caseId]: "",
      }));

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
        response += `Order ID: ${data.order.order_id}\n`;
        response += `Status: ${data.order.status}\n`;
        response += `ETA: ${data.order.eta}\n`;
        response += `Tracking number: ${data.order.tracking_number}\n\n`;
        response += `${data.order.reason}`;
      } else {
        response += "I could not find an order for this request.\n\n";
        response += data.order?.reason || "No order information was available.";
      }

      if (data.case_saved) {
        response += `\n\nCase saved: Yes #${data.case_id}`;
      }

      if (data.escalation_case_id) {
        response += `\nHuman review case: ${data.escalation_case_id}`;
      }

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

    if (data.case_saved) {
      response += `\nCase saved: Yes #${data.case_id}`;
    }

    if (data.escalation_case_id) {
      response += `\nHuman review case: ${data.escalation_case_id}`;
    }

    return response;
  }

  const riskLevel = latestResult?.risk_level || "none";
  const isOrderStatus = latestResult?.intent === "order_status";

  return (
    <div className="app-shell">
      <div className="glow glow-one"></div>
      <div className="glow glow-two"></div>

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Leaf size={22} />
          </div>
          <div>
            <h1>Agro-Mind</h1>
            <p>AI Agricultural Support Assistant</p>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <button
            onClick={() => {
              setShowReviewQueue(false);
              setShowProfiles((prev) => !prev);
            }}
            style={{
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "999px",
              padding: "8px 12px",
              cursor: "pointer",
              background: "rgba(255,255,255,0.08)",
              color: "inherit",
            }}
          >
            {showProfiles ? "Back to Chat" : "Customer Profiles"}
          </button>

          <button
            onClick={async () => {
              setShowProfiles(false);
              setShowReviewQueue((prev) => !prev);
              await loadEscalations();
            }}
            style={{
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "999px",
              padding: "8px 12px",
              cursor: "pointer",
              background: "rgba(255,255,255,0.08)",
              color: "inherit",
            }}
          >
            {showReviewQueue ? "Back to Chat" : "Human Review"}
          </button>

          <div className="system-status">
            <span></span>
            Live agent pipeline
          </div>
        </div>
      </header>

      {showProfiles ? (
        <CustomerProfile />
      ) : showReviewQueue ? (
        <main className="review-layout">
          <section className="review-panel">
            <div className="panel-header">
              <div>
                <p>Human-in-the-Loop</p>
                <h3>Human Review Queue</h3>
              </div>

              <button className="human-escalation-btn" onClick={loadEscalations}>
                Refresh Queue
              </button>
            </div>

            {escalations.length === 0 ? (
              <div className="empty-panel">
                <AlertTriangle size={42} />
                <h3>No pending cases</h3>
                <p>
                  Escalated pesticide, complaint, and low-confidence diagnosis
                  cases will appear here.
                </p>
              </div>
            ) : (
              escalations.map((item) => (
                <div key={item.case_id} className="review-card">
                  <div className="review-card-header">
                    <h3>{safeText(item.case_id)}</h3>
                    <span>{safeText(item.status)}</span>
                  </div>

                  <p>
                    <strong>Customer:</strong> {safeText(item.customer_id)}
                  </p>

                  <p>
                    <strong>User message:</strong>{" "}
                    {safeText(
                      item.user_message ||
                        item.payload?.received_message ||
                        item.payload?.message ||
                        item.payload?.issue ||
                        item.payload?.payload?.issue,
                      "Not saved."
                    )}
                  </p>

                  <p>
                    <strong>Type:</strong> {formatLabel(item.type)}
                  </p>

                  <p>
                    <strong>Source:</strong> {safeText(item.source)}
                  </p>

                  <p>
                    <strong>Reason:</strong> {safeText(item.reason)}
                  </p>

                  <p>
                    <strong>AI Response:</strong>{" "}
                    {safeText(item.ai_response, "No AI response saved.")}
                  </p>

                  <textarea
                    placeholder="Add human reviewer note..."
                    value={reviewNotes[item.case_id] || ""}
                    onChange={(e) =>
                      setReviewNotes((prev) => ({
                        ...prev,
                        [item.case_id]: e.target.value,
                      }))
                    }
                    style={{
                      marginTop: "10px",
                      minHeight: "80px",
                      resize: "vertical",
                    }}
                  />

                  <button
                    className="human-escalation-btn"
                    onClick={() => markReviewed(item.case_id)}
                  >
                    Mark Reviewed
                  </button>
                </div>
              ))
            )}
          </section>
        </main>
      ) : (
        <main className="main-layout">
          <section className="chat-card">
            <div className="chat-header">
              <div>
                <div className="eyebrow">
                  <Sprout size={15} />
                  Customer Chat
                </div>
                <h2>Ask Agro-Mind</h2>
                <p>
                  Chat with the support agent. The backend analyzes each message
                  using intent detection, safety checks, product matching, order
                  lookup, Qwen response generation, and case memory.
                </p>
              </div>
              <Bot size={34} />
            </div>

            <div className="customer-row">
              <label>Customer ID</label>
              <input
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="123"
              />
            </div>

            <div className="chat-window">
              {messages.map((item, index) => (
                <div
                  key={index}
                  className={`message-row ${
                    item.role === "user" ? "user-row" : "assistant-row"
                  }`}
                >
                  <div className="message-avatar">
                    {item.role === "user" ? (
                      <UserRound size={17} />
                    ) : (
                      <Leaf size={17} />
                    )}
                  </div>

                  <div
                    className={`message-bubble ${
                      item.role === "user" ? "user-bubble" : "assistant-bubble"
                    } ${item.error ? "error-bubble" : ""}`}
                  >
                    <pre
                      style={{
                        whiteSpace: "pre-wrap",
                        fontFamily: "inherit",
                        margin: 0,
                      }}
                    >
                      {safeText(item.text, "")}
                    </pre>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message-row assistant-row">
                  <div className="message-avatar">
                    <Leaf size={17} />
                  </div>
                  <div className="message-bubble assistant-bubble typing">
                    <Loader2 className="spin" size={16} />
                    Analyzing...
                  </div>
                </div>
              )}
            </div>

            <div className="examples">
              {examples.map((example) => (
                <button
                  key={example}
                  onClick={() => sendMessage(example)}
                  disabled={loading}
                >
                  {example}
                </button>
              ))}
            </div>

            <div
              className="composer"
              style={{ display: "flex", gap: "10px", alignItems: "center" }}
            >
              <label
                style={{
                  cursor: loading ? "not-allowed" : "pointer",
                  padding: "8px",
                  opacity: loading ? 0.5 : 1,
                }}
                title="Upload crop image"
              >
                <ImagePlus size={24} color="#666" />
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  disabled={loading}
                  style={{ display: "none" }}
                />
              </label>

              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type a customer message..."
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                style={{ flex: 1 }}
              />

              <button onClick={() => sendMessage()} disabled={loading}>
                {loading ? (
                  <Loader2 className="spin" size={19} />
                ) : (
                  <Send size={19} />
                )}
              </button>
            </div>
          </section>

          <aside className="agent-panel">
            <div className="panel-header">
              <div>
                <p>Agent Analysis</p>
                <h3>
                  {latestResult
                    ? formatLabel(latestResult.intent)
                    : "No case yet"}
                </h3>
              </div>
              <span className={`risk-badge ${riskLevel}`}>{riskLevel}</span>
            </div>

            {!latestResult && (
              <div className="empty-panel">
                <Brain size={42} />
                <h3>Waiting for a message</h3>
                <p>
                  Once a customer sends a message or uploads an image, the
                  agent’s decision path will appear here.
                </p>
              </div>
            )}

            {latestResult && (
              <>
                <div className="metric-grid">
                  <div className="metric-card">
                    <Brain size={21} />
                    <span>Intent</span>
                    <strong>{formatLabel(latestResult.intent)}</strong>
                  </div>

                  <div className="metric-card">
                    <ShieldCheck size={21} />
                    <span>Risk</span>
                    <strong>{safeText(latestResult.risk_level)}</strong>
                  </div>

                  {latestResult.intent !== "image_diagnosis" && (
                    <div className="metric-card">
                      <CheckCircle2 size={21} />
                      <span>Case saved</span>
                      <strong>
                        {latestResult.case_saved
                          ? `Yes #${latestResult.case_id}`
                          : "Not saved"}
                      </strong>
                    </div>
                  )}

                  {isOrderStatus ? (
                    <>
                      <div className="metric-card">
                        <PackageSearch size={21} />
                        <span>Order ID</span>
                        <strong>
                          {safeText(
                            latestResult.order?.order_id,
                            "Not found"
                          )}
                        </strong>
                      </div>

                      <div className="metric-card">
                        <Activity size={21} />
                        <span>Status</span>
                        <strong>
                          {safeText(
                            latestResult.order?.status,
                            "Not available"
                          )}
                        </strong>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="metric-card">
                        <PackageSearch size={21} />
                        <span>Product/Crop</span>
                        <strong>
                          {safeText(
                            latestResult.recommended_product ||
                              latestResult.detected_crop,
                            "None"
                          )}
                        </strong>
                      </div>

                      <div className="metric-card">
                        <Activity size={21} />
                        <span>Escalation</span>
                        <strong>
                          {latestResult.escalation_required ||
                          latestResult.needs_human_review ||
                          latestResult.human_review_required
                            ? "Required"
                            : "Not required"}
                        </strong>
                      </div>
                    </>
                  )}
                </div>

                {latestResult.updated_customer_profile && (
                  <div className="decision-card">
                    <div className="decision-title">
                      <UserRound size={18} />
                      Customer memory
                    </div>

                    <p>
                      <strong>Profile:</strong>{" "}
                      {safeText(
                        latestResult.updated_customer_profile.profile_summary,
                        "No summary available"
                      )}
                    </p>

                    <p>
                      <strong>Segment:</strong>{" "}
                      {safeText(
                        latestResult.updated_customer_profile.customer_segment,
                        "Regular"
                      )}
                    </p>

                    <p>
                      <strong>Crops:</strong>{" "}
                      {safeText(
                        latestResult.updated_customer_profile.crops,
                        "Not available"
                      )}
                    </p>
                  </div>
                )}

                <div className="decision-card">
                  <div className="decision-title">
                    <CheckCircle2 size={18} />
                    Current decision
                  </div>

                  {isOrderStatus ? (
                    <>
                      <p>
                        <strong>Order found:</strong>{" "}
                        {latestResult.order?.order_found ? "Yes" : "No"}
                      </p>
                      <p>
                        <strong>ETA:</strong>{" "}
                        {safeText(latestResult.order?.eta)}
                      </p>
                      <p>
                        <strong>Tracking number:</strong>{" "}
                        {safeText(latestResult.order?.tracking_number)}
                      </p>
                      <p>
                        <strong>Reason:</strong>{" "}
                        {safeText(
                          latestResult.order?.reason,
                          "No lookup reason available"
                        )}
                      </p>
                    </>
                  ) : (
                    <>
                      <p>
                        <strong>Detected crop:</strong>{" "}
                        {safeText(latestResult.detected_crop, "Not detected")}
                      </p>
                      <p>
                        <strong>Detected issue:</strong>{" "}
                        {safeText(latestResult.detected_issue, "Not detected")}
                      </p>
                      <p>
                        <strong>Reason:</strong>{" "}
                        {safeText(
                          latestResult.product_reason,
                          "No product reason available"
                        )}
                      </p>
                      {latestResult.escalation_case_id && (
                        <p>
                          <strong>Human review case:</strong>{" "}
                          {safeText(latestResult.escalation_case_id)}
                        </p>
                      )}
                    </>
                  )}
                </div>

                {latestResult.execution_trace &&
                  latestResult.execution_trace.length > 0 && (
                    <div className="decision-card">
                      <div className="decision-title">
                        <Activity size={18} />
                        Agent execution trace
                      </div>

                      {latestResult.execution_trace.map((step) => (
                        <p key={step.step}>
                          <strong>
                            {safeText(step.step)}. {safeText(step.task)}:
                          </strong>{" "}
                          {safeText(step.status, "unknown")} —{" "}
                          {safeText(step.result, "No result")}
                        </p>
                      ))}
                    </div>
                  )}

                {latestResult.risk_level === "high" && (
                  <div className="warning-card">
                    <AlertTriangle size={20} />
                    <div>
                      <strong>High-risk case</strong>
                      <p>
                        Human Review Required — this case has been flagged for
                        agronomist or safety review.
                      </p>
                    </div>
                  </div>
                )}

                {(latestResult.escalation_required ||
                  latestResult.needs_human_review ||
                  latestResult.human_review_required) &&
                  latestResult.risk_level !== "high" && (
                    <div className="warning-card">
                      <AlertTriangle size={20} />
                      <div>
                        <strong>Human review recommended</strong>
                        <p>
                          Human Review Required — this case has been flagged for
                          agronomist review.
                        </p>
                      </div>
                    </div>
                  )}

                {(latestResult.escalation_required ||
                  latestResult.needs_human_review ||
                  latestResult.human_review_required) && (
                  <button
                    className="human-escalation-btn"
                    onClick={goToHumanEscalation}
                  >
                    👨‍🌾 Contact Human Expert
                  </button>
                )}

                <details className="json-card">
                  <summary>Raw backend JSON</summary>
                  <pre>{JSON.stringify(latestResult, null, 2)}</pre>
                </details>
              </>
            )}
          </aside>
        </main>
      )}
    </div>
  );
}

export default App;